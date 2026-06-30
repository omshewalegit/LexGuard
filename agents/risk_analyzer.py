"""
Pass 2: Risk Assessment.

Takes extracted clauses (from Pass 1) and assesses each for risk level,
provides reasoning, generates negotiation tips, estimates financial impact,
and suggests replacement language.

Architecture:
  - Clauses are deduplicated BEFORE batching (identical original_text collapsed)
  - Batches run CONCURRENTLY with staggered start, bounded by OVERALL_DEADLINE
  - Failed batches get a BATCHED rescue pass (not single-clause — see fix below)
  - Duplicates are re-expanded after assessment
  - Uses the 70B SMART model — this is the most critical reasoning step

FIX HISTORY (2026-07-01):
  - CRITICAL BUG FIXED: rescue pass fired one asyncio task PER unknown clause
    with no concurrency cap (asyncio.gather on up to 24 tasks at once), all
    hammering only 3 API keys simultaneously. This caused mass rate-limiting
    and timeouts, pushing total pipeline time past 4 minutes.
    FIX 1: Added a global asyncio.Semaphore bounding concurrent LLM calls to
    MAX_CONCURRENT_LLM_CALLS (= number of API keys). Applies to BOTH the main
    batch pass and the rescue pass, since they share _assess_batch_async().
    FIX 2: Rescue pass no longer creates one task per clause. Unknown clauses
    are re-batched into groups of RESCUE_BATCH_SIZE and run through the same
    batched assessment path as the main pass — cutting 24 single-clause calls
    down to ~4 batched calls.
"""

import asyncio
import json
import re
import time
from utils.llm import get_llm
from utils.logger import get_logger
import nest_asyncio
nest_asyncio.apply()

logger = get_logger("risk_analyzer")

PERSONA_MAP = {
    "OFFER_LETTER":            "employment lawyer specializing in fresh-graduate job offers",
    "EMPLOYMENT_CONTRACT":     "employment lawyer specializing in employment agreements",
    "RENT_AGREEMENT":          "property lawyer specializing in rental and tenancy agreements",
    "INTERNSHIP_CONTRACT":     "employment lawyer advising fresh graduates and interns",
    "SERVICE_AGREEMENT":       "commercial contracts lawyer",
    "NDA":                     "IP and confidentiality law specialist",
    "LOAN_AGREEMENT":          "banking and finance lawyer specializing in loan documentation",
    "TERMS_AND_CONDITIONS":    "consumer protection and digital rights specialist",
    "PRIVACY_POLICY":          "data privacy and compliance lawyer",
    "PARTNERSHIP_AGREEMENT":   "corporate lawyer specializing in partnership structures",
    "CONSULTING_AGREEMENT":    "commercial lawyer specializing in consulting engagements",
    "FREELANCER_AGREEMENT":    "freelance and gig-economy contracts specialist",
    "SAAS_CONTRACT":           "technology contracts lawyer specializing in SaaS agreements",
    "VENDOR_CONTRACT":         "procurement and vendor management lawyer",
    "OTHER":                   "senior legal analyst specializing in contract law",
}

LEGAL_PROTOCOL = """
CRITICAL LEGAL ANALYSIS PROTOCOL

You are not a summarizer.

You are a contract risk auditor whose primary objective is to identify every legal obligation,
restriction, liability, financial exposure, employment limitation, dispute risk, ownership
transfer, and negotiation opportunity that affects the signer.

Your goal is MAXIMUM RECALL with MINIMUM HALLUCINATION.

=================================================
STEP 1 — ASSESSMENT ACCURACY
============================
Assess ONLY clauses that are explicitly provided to you below.
Never invent a clause. Never infer a clause that is not written.
Base every assessment strictly on the original_text provided.

=================================================
STEP 2 — CLAUSE LABEL DISCIPLINE
==================================
Never relabel clauses. Use the clause meaning that actually exists.

Examples of FORBIDDEN relabeling:
  Moonlighting Restriction ≠ Non-Compete
  Confidentiality ≠ Non-Solicitation
  Exclusivity Clause ≠ Non-Compete
  Transfer Rights ≠ Relocation Bond
  Variable Compensation ≠ Salary Reduction
  Audit Rights ≠ Liability Clause

If uncertain, preserve the original meaning instead of assigning a stronger legal label.
False positives are worse than missed clauses.

=================================================
STEP 3 — RISK ASSESSMENT DISCIPLINE
=====================================
Risk must be assigned based on actual signer impact — not assumed severity.

HIGH RISK: Unlimited liability, unlimited indemnity, immediate termination without notice,
large financial penalties, long non-competes (>1 year), deposit forfeiture, broad IP transfer,
one-sided termination rights, severe employment restrictions.

MEDIUM RISK: Salary discretion, transfer rights, broad confidentiality, exclusive jurisdiction,
variable pay changes, ambiguous obligations, moonlighting restrictions.

LOW RISK: Minor restrictions, administrative obligations, standard reporting requirements.

SAFE: Standard industry clauses, balanced obligations, statutory requirements,
ordinary compensation structures.

=================================================
STEP 4 — FINANCIAL IMPACT
==========================
Whenever numbers exist in the clause text — estimate actual exposure. Do not write generic statements.

Good: "Potential exposure = 15 days salary as notice buyout"
Bad:  "This may have financial consequences"

If exact calculation is impossible, explain why clearly.
Do NOT invent numbers that are not in the clause text.

=================================================
STEP 5 — NEGOTIATION QUALITY
==============================
Never generate generic advice.

Bad:  "Request clarification."
Good: "Request a cap limiting indemnity to direct losses and one year of compensation."

Bad:  "Review this clause carefully."
Good: "Request written relocation reimbursement and a minimum 30-day transfer notice."

=================================================
STEP 6 — LAWYER REVIEW TEST
=============================
Before assigning HIGH risk, ask:
  Would an experienced contract lawyer likely classify this as HIGH risk?

If the answer is uncertain — downgrade to MEDIUM and reduce confidence.
HIGH risk should be rare and reserved for clauses that create substantial
financial, employment, legal, or ownership exposure.

=================================================
STEP 7 — HALLUCINATION SAFETY CHECK
=====================================
Before finalizing each clause assessment, ask:
  1. Did I invent a fact not present in the clause text?
  2. Did I relabel this clause incorrectly?
  3. Did I overstate the legal risk?
  4. Did I cite a law or statute not mentioned in the clause?
  5. Would a lawyer agree with this classification?

If any answer is uncertain — lower confidence.
Accuracy is more important than sounding intelligent.

=================================================
FINAL RULE
==========
The objective is not to find the most risks.
The objective is to find the CORRECT risks.
A missed clause is acceptable. A hallucinated clause is unacceptable.
"""

LABELING_RULES = """
CLAUSE LABELING RULES — follow these strictly:

1. NON-COMPETE vs MOONLIGHTING:
   - Non-Compete = restricts work AFTER leaving the company → HIGH risk
   - Moonlighting Restriction = no side jobs DURING employment → MEDIUM risk
   - NEVER label a during-employment restriction as Non-Compete

2. CONFIDENTIALITY vs NON-SOLICITATION:
   - Confidentiality = don't share company secrets → use "Confidentiality / NDA"
   - Non-Solicitation = don't poach clients/employees → use "Non-Solicitation"
   - NEVER use these interchangeably

3. GENERAL RULE:
   - Use the clause's ACTUAL meaning, not its closest-sounding legal term
   - If unsure between two labels, pick the WEAKER/NARROWER one
   - A false positive (overstating risk) is WORSE than a missed clause
"""

CONFIDENCE_RULES = """
CONFIDENCE SCORING RULES — apply precisely:

  95-99: Clause explicitly states the obligation with no ambiguity whatsoever.
  85-94: Meaning is clear but minor interpretation exists.
  70-84: Some ambiguity exists in the clause language.
  50-69: Significant uncertainty — meaning depends heavily on context or assumptions.

Never use 95+ if legal interpretation depends on any assumptions.
When in doubt, score lower.
"""

FEW_SHOT_EXAMPLES = """
EXAMPLE OUTPUT (showing the quality, depth, and format expected):
[
  {
    "index": 0,
    "clause_type": "Non-Compete Restriction",
    "risk_level": "HIGH",
    "confidence": 92,
    "reason": "A 2-year non-compete is unusually long and could meaningfully restrict the person's ability to work in their field after leaving. Many jurisdictions limit or refuse to enforce broad post-employment non-competes, but the clause could still create practical barriers during job transitions.",
    "financial_impact": "Potential loss of 2 years of income in your field. If current CTC is stated as ₹14 LPA in the document, exposure is approximately ₹28 lakhs in career opportunity cost.",
    "real_world_consequences": "You may be forced to switch industries or remain unemployed for 24 months. Even if legally unenforceable, the company may send legal notices that create stress and legal costs.",
    "negotiation_tip": "Request reduction to 6 months maximum, limit scope to direct competitors only, and restrict the geographic area to where you actually work.",
    "suggested_replacement": "Employee agrees not to join a Direct Competitor in the same city of employment for a period of 6 months following separation. 'Direct Competitor' shall be defined as a company whose primary business directly competes with the Company's core product line."
  },
  {
    "index": 1,
    "clause_type": "Moonlighting Restriction",
    "risk_level": "MEDIUM",
    "confidence": 88,
    "reason": "This clause prevents any part-time work or business during employment. It is broader than typical exclusivity clauses as it may restrict passive income sources.",
    "financial_impact": "Potential loss of supplementary income during employment. No specific amount stated in clause.",
    "real_world_consequences": "You cannot freelance, consult, or run a side business while employed here.",
    "negotiation_tip": "Request narrowing to direct competitors only, with a carve-out for passive investments and non-competing freelance work.",
    "suggested_replacement": "Employee shall not engage in part-time employment or business that directly competes with the Company's core services during the term of employment."
  }
]"""

RISK_FOCUS = {
    "OFFER_LETTER": [
        "Is the notice period reasonable (30-90 days)?",
        "If an IP assignment clause exists, does it cover personal projects or only work-related IP?",
        "If a bond or training cost recovery clause exists, evaluate how much and how long.",
        "If a non-compete clause exists, evaluate its scope and duration — otherwise ignore.",
        "Are salary revision terms at employer's sole discretion?",
        "If a relocation clause exists, is it open-ended or does it include safeguards?",
        "If a moonlighting restriction exists, how broad is it?",
        "If variable pay exists, is it subject to arbitrary changes or clearly defined?",
    ],
    "EMPLOYMENT_CONTRACT": [
        "Is the notice period and buyout amount reasonable?",
        "If an IP assignment clause exists, does it cover personal/off-hours projects?",
        "Is 'gross misconduct' defined narrowly or left vague?",
        "If a non-compete exists, is its duration and scope reasonable and likely enforceable?",
        "Is indemnity unlimited or capped?",
        "If a garden leave provision exists, evaluate its terms.",
        "Is jurisdiction clause fair (local vs distant court)?",
        "Is the probation period and confirmation process clear?",
        "If a bond period or training cost recovery exists, evaluate it.",
        "Are salary revision terms discretionary or structured?",
    ],
    "RENT_AGREEMENT": [
        "Is the security deposit amount reasonable (1-3 months is standard)?",
        "Are conditions for deposit deduction clearly defined, or left to landlord's sole discretion?",
        "If a rent escalation clause exists, is it capped (5-10% per year is typical)?",
        "Who bears maintenance and major repair costs?",
        "If a lock-in period exists, is the penalty proportionate?",
        "Can the landlord terminate WITHOUT notice?",
        "Is the notice period for vacating reasonable (48 hours is extremely short)?",
        "If inspection rights exist, are they unrestricted or bounded?",
        "Is deposit forfeiture triggered too easily?",
    ],
    "INTERNSHIP_CONTRACT": [
        "Is IP ownership of intern's work clearly defined?",
        "If a conversion-to-full-time clause exists, evaluate its conditions.",
        "Is the stipend payment timeline clear?",
        "Are working hours and overtime expectations defined?",
        "Is the confidentiality duration reasonable?",
        "If a non-compete exists for interns, flag it as unusual and concerning.",
    ],
    "SERVICE_AGREEMENT": [
        "Are payment terms and timelines clear?",
        "If a scope of work exists, is scope creep handled (change request process)?",
        "Who owns the deliverables/IP?",
        "If a termination-for-convenience clause exists, evaluate risk to service provider.",
        "Is the liability cap reasonable?",
        "If auto-renewal exists, is exit difficult?",
        "Is the indemnity clause balanced?",
        "Are billing dispute resolution procedures fair?",
    ],
    "NDA": [
        "Is 'confidential information' defined too broadly?",
        "Is the confidentiality duration excessive (over 3-5 years)?",
        "If a residuals clause exists, evaluate it.",
        "Are standard exceptions included (public knowledge, independent development)?",
        "Is it mutual or one-sided?",
        "Is the injunctive relief clause proportionate?",
        "Are return/destruction obligations clear?",
    ],
    "LOAN_AGREEMENT": [
        "Is the interest rate fixed or variable? If variable, is the cap defined?",
        "If prepayment penalties exist, are they excessive?",
        "Is the default clause triggered too easily?",
        "Are late payment penalties proportionate?",
        "Is collateral requirement clearly defined?",
        "If an acceleration clause exists, is it fair?",
        "Are dispute resolution and jurisdiction reasonable?",
    ],
    "TERMS_AND_CONDITIONS": [
        "Is the limitation of liability reasonable?",
        "Can the company change terms unilaterally without notice?",
        "If an arbitration clause exists, is it fair or does it waive important rights?",
        "Is the data usage scope overly broad?",
        "Is the termination/account deletion process clear?",
        "Are refund/cancellation terms fair?",
    ],
    "PRIVACY_POLICY": [
        "What data is collected and is it proportionate to the service?",
        "Is data shared with third parties? Under what conditions?",
        "Is there a data deletion/export mechanism?",
        "Is consent for data processing freely given or buried in terms?",
        "Is the retention period defined and reasonable?",
        "Is there compliance with applicable data protection laws?",
    ],
    "PARTNERSHIP_AGREEMENT": [
        "Is profit/loss sharing proportionate to investment/effort?",
        "Are exit and dissolution terms clearly defined?",
        "Is decision-making authority balanced?",
        "Is liability limited or joint and several?",
        "Are capital contribution obligations clear?",
        "If a non-compete exists, is it reasonable during and after partnership?",
    ],
    "CONSULTING_AGREEMENT": [
        "Are payment terms and milestones clearly defined?",
        "If an IP assignment clause exists, does it cover pre-existing consultant IP?",
        "Is the scope of work clearly bounded?",
        "Is the termination notice period reasonable?",
        "If a non-solicitation clause exists, is it proportionate?",
        "Is the indemnity clause balanced?",
    ],
    "FREELANCER_AGREEMENT": [
        "Are payment terms and timelines clearly defined?",
        "If an IP transfer clause exists, does it happen only upon full payment?",
        "Is the revision/rework scope limited?",
        "Is the termination clause fair to the freelancer?",
        "If a non-compete exists, is it enforceable for a freelancer?",
        "Is liability capped at the contract value?",
    ],
    "SAAS_CONTRACT": [
        "If an SLA exists, is the uptime guarantee clearly defined with remedies?",
        "Are data portability and export rights guaranteed?",
        "If auto-renewal exists, is the opt-out process clear?",
        "If price escalation exists, is it capped?",
        "Are data security obligations specified?",
        "Is the termination and data deletion timeline clear?",
    ],
    "VENDOR_CONTRACT": [
        "Are delivery timelines and penalties clearly defined?",
        "Is the acceptance criteria for deliverables objective?",
        "Are payment terms fair (net-30/60/90)?",
        "Is the warranty period and scope reasonable?",
        "Is the indemnity proportionate to contract value?",
        "If a termination for convenience clause exists, is it balanced?",
    ],
}

DEFAULT_FOCUS = [
    "Are termination conditions fair and clearly defined?",
    "Is the notice period reasonable?",
    "Are IP and confidentiality clauses balanced?",
    "Is liability capped or unlimited?",
    "Is dispute resolution jurisdiction fair?",
    "Are payment/compensation terms clear?",
]

# ── Timing knobs ───────────────────────────────────────────────
BATCH_SIZE                      = 6
BATCH_STAGGER_SECONDS           = 1.5
PER_ATTEMPT_LLM_TIMEOUT_SECONDS = 30.0
MAX_ATTEMPTS_PER_BATCH          = 3
RETRY_BACKOFF_SECONDS           = 2.0
RATE_LIMIT_WAIT_CAP_SECONDS     = 12.0
OVERALL_DEADLINE_SECONDS        = 90.0

# ── Concurrency knobs (FIX) ──────────────────────────────────────
# Bounds how many LLM calls can be in-flight at once, across BOTH the main
# batch pass and the rescue pass (they share the same semaphore since they
# both ultimately call _assess_batch_async). Set to the number of available
# API keys — no point allowing more concurrent calls than keys, since extra
# calls just queue up rate-limit errors on a key that's already busy.
try:
    from utils.llm import GROQ_KEYS as _GROQ_KEYS
    MAX_CONCURRENT_LLM_CALLS = max(1, len(_GROQ_KEYS))
except Exception:
    MAX_CONCURRENT_LLM_CALLS = 3  # safe fallback if import shape changes

_llm_semaphore: "asyncio.Semaphore | None" = None


def _get_semaphore() -> asyncio.Semaphore:
    """
    Lazily create the semaphore bound to the currently-running event loop.
    (asyncio.Semaphore() must be created while a loop is running/known —
    creating it at module import time can bind it to the wrong loop when
    asyncio.run() is called multiple times, e.g. once per document.)
    """
    global _llm_semaphore
    if _llm_semaphore is None:
        _llm_semaphore = asyncio.Semaphore(MAX_CONCURRENT_LLM_CALLS)
    return _llm_semaphore


# Rescue pass batching (FIX) — unknown clauses are re-grouped into batches
# instead of firing one task per clause.
RESCUE_BATCH_SIZE = 6


def _parse_retry_after_seconds(error_message: str) -> float:
    match = re.search(
        r"try again in (?:(\d+)h)?(?:(\d+)m)?([\d.]+)s",
        error_message,
    )
    if not match:
        return 2.0
    hours   = float(match.group(1)) if match.group(1) else 0.0
    minutes = float(match.group(2)) if match.group(2) else 0.0
    seconds = float(match.group(3)) if match.group(3) else 0.0
    return hours * 3600 + minutes * 60 + seconds + 0.5


def _is_rate_limit_error(error_message: str) -> bool:
    msg = error_message.lower()
    return "rate_limit_exceeded" in msg or "rate limit reached" in msg


def _sanitize_clause_type(clause_type: str) -> str:
    """Strip risk-level prefixes the LLM sometimes leaks into clause_type."""
    prefixes = [
        "HIGH - ", "MEDIUM - ", "LOW - ", "SAFE - ",
        "HIGH: ", "MEDIUM: ", "LOW: ", "SAFE: ",
        "HIGH — ", "MEDIUM — ", "LOW — ", "SAFE — ",
    ]
    for prefix in prefixes:
        if clause_type.upper().startswith(prefix.upper()):
            clause_type = clause_type[len(prefix):].strip()
            break
    return clause_type


def _clause_type_matches(expected: str, returned: str) -> bool:
    """Fuzzy match clause types by checking keyword overlap."""
    if not expected or not returned:
        return True

    def normalize(s: str) -> set[str]:
        s = re.sub(r"[^a-z0-9\s]", " ", s.lower())
        stopwords = {
            "and", "or", "the", "a", "an", "of", "to", "for", "clause",
            "section", "provision", "term", "terms", "other", "general",
        }
        return {w for w in s.split() if w and w not in stopwords}

    exp_words = normalize(expected)
    ret_words = normalize(returned)
    if not exp_words or not ret_words:
        return True
    return bool(exp_words & ret_words)


# ── Deduplication ──────────────────────────────────────────────

def _deduplicate_clauses(clauses: list[dict]) -> tuple[list[dict], dict[int, int]]:
    seen: dict[str, int] = {}
    unique_clauses: list[dict] = []
    duplicate_map: dict[int, int] = {}

    for i, clause in enumerate(clauses):
        key = clause.get("original_text", "").strip().lower()
        if len(key) < 20:
            key = f"{key}|{clause.get('clause_type', '').strip().lower()}"

        if key in seen:
            duplicate_map[i] = seen[key]
            logger.debug(
                f"Duplicate clause at index {i} → maps to index {seen[key]}: "
                f"'{clause.get('clause_type', 'Unknown')}'"
            )
        else:
            unique_index = len(unique_clauses)
            seen[key] = unique_index
            duplicate_map[i] = unique_index
            unique_clauses.append(clause)

    removed = len(clauses) - len(unique_clauses)
    if removed > 0:
        logger.info(
            f"Deduplication: removed {removed} duplicate clause(s) "
            f"({len(clauses)} → {len(unique_clauses)} unique)"
        )
    return unique_clauses, duplicate_map


def _expand_duplicates(
    assessed_unique: list[dict],
    original_clauses: list[dict],
    duplicate_map: dict[int, int],
) -> list[dict]:
    result = []
    for i, original_clause in enumerate(original_clauses):
        unique_idx = duplicate_map[i]
        if unique_idx < len(assessed_unique):
            assessed = assessed_unique[unique_idx].copy()
            assessed["original_text"] = original_clause.get("original_text", "")
            assessed["clause_type"]   = original_clause.get("clause_type", assessed["clause_type"])
            assessed["section_ref"]   = original_clause.get("section_ref", assessed.get("section_ref", ""))
            result.append(assessed)
        else:
            result.append(_unanalyzed_entry(original_clause))
    return result


# ── Prompt Construction ────────────────────────────────────────

def _build_assessment_prompt(
    extracted_clauses: list[dict],
    doc_type: str,
    locale_hint: str = None,
) -> str:
    persona    = PERSONA_MAP.get(doc_type, PERSONA_MAP["OTHER"])
    doc_label  = doc_type.replace("_", " ").title()
    focus      = RISK_FOCUS.get(doc_type, DEFAULT_FOCUS)
    focus_text = "\n".join(f"  - {f}" for f in focus)

    locale_instruction = (
        f"This document is governed by the laws of {locale_hint}. When citing law, "
        f"only reference {locale_hint}-specific statutes or legal principles — never "
        f"assume any other country's laws."
        if locale_hint else
        "The document's governing jurisdiction is not confirmed. Do NOT cite a specific "
        "country's statutes unless the clause text itself names that jurisdiction. "
        "Keep legal reasoning general/principle-based when jurisdiction is unknown."
    )

    # Build clause list with index for coverage validation
    clause_indices = []
    clauses_text = ""
    for i, c in enumerate(extracted_clauses):
        clause_indices.append(f"  - Index {i}: {c.get('clause_type', 'Unknown')}")
        clauses_text += f"""
Clause index {i}: {c.get('clause_type', 'Unknown')}
  Category: {c.get('category', 'Other')}
  Original Text: {c.get('original_text', '')[:500]}
  Section: {c.get('section_ref', 'Unknown')}
---"""

    coverage_list = "\n".join(clause_indices)

    return f"""You are a {persona} conducting a thorough risk assessment of a {doc_label}.

{locale_instruction}

{LEGAL_PROTOCOL}

{LABELING_RULES}

{CONFIDENCE_RULES}

CONTEXT: Clauses below are already extracted. ASSESS the risk level of each one based on its text. Do NOT re-copy original_text in your response.

RISK LEVEL CRITERIA — apply these precisely:
- HIGH: Significant financial loss, career restriction >1 year, unlimited personal liability, legal exposure, or clauses that could leave the signer homeless/jobless with little notice. Includes: deposit forfeiture, bond >1 year, non-compete >1 year, immediate termination without notice, unlimited indemnity.
- MEDIUM: Unfavorable but negotiable. Common in many contracts but worth reviewing. Moderate financial or practical impact. Includes: vague termination criteria, broad confidentiality, salary at sole discretion, moonlighting restriction.
- LOW: Minor concerns. Slightly one-sided but industry standard. Minimal practical impact.
- SAFE: Fair, balanced, legally standard clauses. No action needed.

IMPORTANT — Do NOT default everything to MEDIUM. Distinguish carefully:
- A clause allowing immediate termination without notice is HIGH, not MEDIUM.
- A standard governing law clause is SAFE, not LOW.
- A 6-month probation period is SAFE.
- A moonlighting restriction is MEDIUM, NOT a Non-Compete.

FOCUS AREAS for {doc_label}:
{focus_text}

{FEW_SHOT_EXAMPLES}

COVERAGE VALIDATION — Before finalizing your response, verify you have assessed ALL of these:
{coverage_list}

If any index is missing from your response, add it before returning.

NOW ASSESS THESE EXTRACTED CLAUSES:
{clauses_text}

Return a JSON array with EXACTLY {len(extracted_clauses)} objects — ONE PER CLAUSE INDEX, in the SAME ORDER:
{{
  "index": <clause index number>,
  "clause_type": "<exact clause_type label from above — do NOT relabel>",
  "risk_level": "HIGH or MEDIUM or LOW or SAFE",
  "confidence": integer 50-99,
  "reason": "2-3 sentences explaining the real-world impact on the person signing",
  "financial_impact": "Quantify using actual numbers from the clause text. If no numbers exist, describe the category of risk only — do not invent figures.",
  "real_world_consequences": "1-2 sentences: what could actually happen to the signer in practice",
  "negotiation_tip": "specific, actionable advice tailored to THIS clause — not generic",
  "suggested_replacement": "If risk_level is HIGH or MEDIUM, provide exact ready-to-use replacement language. If SAFE or LOW, leave empty string."
}}

RULES:
- Return ONLY a valid JSON array — no markdown fences, no commentary
- Assess EVERY clause index — do not skip any
- Use the EXACT clause_type label provided — do NOT relabel or rename
- confidence must follow CONFIDENCE SCORING RULES above — never inflate
- negotiation_tip must be specific to this clause, not a boilerplate suggestion
- financial_impact must reference actual numbers from the clause text when available
- suggested_replacement must be ready-to-use contract language, not a description of what to change
- Do NOT include original_text in your response
- Do NOT invent facts, numbers, or laws that are not present in the clause text
- If no number exists in the clause, estimate based only on stated salary/deposit/penalty figures
"""


# ── Core Assessment Logic ──────────────────────────────────────

def assess_risks(
    extracted_clauses: list[dict],
    doc_type: str,
    full_text: str = None,
    locale_hint: str = None,
) -> list[dict]:
    if not extracted_clauses:
        logger.warning("No clauses to assess")
        return _fallback_response()

    logger.info(f"Assessing {len(extracted_clauses)} clauses | doc_type={doc_type}")

    unique_clauses, duplicate_map = _deduplicate_clauses(extracted_clauses)

    batches = [
        unique_clauses[i:i + BATCH_SIZE]
        for i in range(0, len(unique_clauses), BATCH_SIZE)
    ]

    # Reset semaphore for this run (in case assess_risks is called multiple
    # times across different asyncio.run() event loops in the same process).
    global _llm_semaphore
    _llm_semaphore = None

    start_time = time.monotonic()
    assessed_unique, skipped_batches = asyncio.run(
        _assess_all_batches_with_deadline(batches, doc_type, locale_hint)
    )
    elapsed = time.monotonic() - start_time
    logger.info(
        f"All {len(batches)} batches resolved in {elapsed:.1f}s "
        f"(deadline={OVERALL_DEADLINE_SECONDS}s, skipped_batches={skipped_batches})"
    )

    if skipped_batches > 0:
        unknown_indices = [
            i for i, c in enumerate(assessed_unique)
            if c.get("risk_level") == "UNKNOWN"
        ]
        if unknown_indices:
            logger.info(f"Rescue pass: retrying {len(unknown_indices)} UNKNOWN clause(s)")
            rescued = asyncio.run(
                _rescue_unknown_clauses(
                    assessed_unique, unique_clauses, unknown_indices, doc_type, locale_hint
                )
            )
            for idx, result in rescued.items():
                assessed_unique[idx] = result

    all_validated = _expand_duplicates(assessed_unique, extracted_clauses, duplicate_map)

    if not all_validated:
        logger.error("All assessment attempts failed. Returning fallback.")
        return _fallback_response()

    _assign_priority_rankings(all_validated)

    logger.info(
        f"Assessment complete: {len(all_validated)} clauses | "
        f"HIGH={sum(1 for r in all_validated if r['risk_level'] == 'HIGH')} | "
        f"MEDIUM={sum(1 for r in all_validated if r['risk_level'] == 'MEDIUM')} | "
        f"LOW={sum(1 for r in all_validated if r['risk_level'] == 'LOW')} | "
        f"SAFE={sum(1 for r in all_validated if r['risk_level'] == 'SAFE')} | "
        f"NEEDS_MANUAL_REVIEW={sum(1 for r in all_validated if r['risk_level'] == 'UNKNOWN')}"
    )
    return all_validated


def _assign_priority_rankings(clauses: list[dict]) -> None:
    SEVERITY_WEIGHT = {"HIGH": 100, "MEDIUM": 50, "LOW": 10, "SAFE": 0, "UNKNOWN": 30}

    negotiable = [
        c for c in clauses
        if c.get("risk_level") in ("HIGH", "MEDIUM")
    ]

    negotiable.sort(
        key=lambda c: (
            SEVERITY_WEIGHT.get(c.get("risk_level", "UNKNOWN"), 0)
            * c.get("confidence", 50)
        ),
        reverse=True,
    )

    for rank, clause in enumerate(negotiable, start=1):
        clause["priority_rank"] = rank


# ── Async Batch Processing ─────────────────────────────────────

async def _rescue_unknown_clauses(
    assessed: list[dict],
    source_clauses: list[dict],
    unknown_indices: list[int],
    doc_type: str,
    locale_hint: str,
) -> dict[int, dict]:
    """
    FIX: previously created ONE asyncio task per unknown clause and gathered
    them all with no concurrency limit — e.g. 24 single-clause LLM calls
    fired simultaneously against only 3 API keys, causing mass rate-limiting.

    Now: unknown clauses are re-grouped into batches of RESCUE_BATCH_SIZE and
    run through the SAME batched path as the main pass (_assess_batch_async),
    which is itself bounded by the global semaphore. This turns e.g. 24
    single-clause calls into ~4 batched calls, with at most
    MAX_CONCURRENT_LLM_CALLS in flight at once.
    """
    chunks = [
        unknown_indices[i:i + RESCUE_BATCH_SIZE]
        for i in range(0, len(unknown_indices), RESCUE_BATCH_SIZE)
    ]

    async def _rescue_chunk(chunk_num: int, idx_chunk: list[int]) -> dict[int, dict]:
        chunk_clauses = [source_clauses[idx] for idx in idx_chunk]
        try:
            results = await _assess_batch_async(
                chunk_clauses, doc_type, locale_hint, batch_num=f"rescue-{chunk_num}"
            )
        except Exception as e:
            logger.warning(f"Rescue chunk {chunk_num} raised: {e}")
            return {}

        recovered: dict[int, dict] = {}
        # _assess_batch_async preserves order/length on success; on total
        # failure it returns _unanalyzed_entry() per input clause (still
        # UNKNOWN), so only copy over genuinely-recovered entries.
        for pos, idx in enumerate(idx_chunk):
            if pos < len(results) and results[pos].get("risk_level") != "UNKNOWN":
                recovered[idx] = results[pos]
                logger.info(
                    f"Rescue pass: recovered clause {idx} "
                    f"({source_clauses[idx].get('clause_type', '?')})"
                )
        return recovered

    tasks = [_rescue_chunk(i + 1, chunk) for i, chunk in enumerate(chunks)]
    chunk_results = await asyncio.gather(*tasks, return_exceptions=True)

    merged: dict[int, dict] = {}
    for r in chunk_results:
        if isinstance(r, dict):
            merged.update(r)
        elif isinstance(r, Exception):
            logger.warning(f"Rescue chunk raised exception: {r}")
    return merged


async def _assess_all_batches_with_deadline(
    batches: list[list[dict]],
    doc_type: str,
    locale_hint: str = None,
) -> tuple[list[dict], int]:
    async def _delayed(batch, batch_num, delay):
        if delay > 0:
            await asyncio.sleep(delay)
        return await _assess_batch_async(batch, doc_type, locale_hint, batch_num)

    tasks = [
        asyncio.ensure_future(
            _delayed(batch, i + 1, delay=i * BATCH_STAGGER_SECONDS)
        )
        for i, batch in enumerate(batches)
    ]

    done, pending = await asyncio.wait(tasks, timeout=OVERALL_DEADLINE_SECONDS)

    if pending:
        for t in pending:
            t.cancel()
        await asyncio.gather(*pending, return_exceptions=True)

    all_validated = []
    skipped_batches = 0

    for batch_num, (task, batch) in enumerate(zip(tasks, batches), start=1):
        if task in pending:
            logger.error(
                f"Batch {batch_num}: did not finish within the "
                f"{OVERALL_DEADLINE_SECONDS}s deadline — flagging for manual review"
            )
            all_validated.extend(_unanalyzed_entry(c) for c in batch)
            skipped_batches += 1
            continue
        try:
            all_validated.extend(task.result())
        except Exception as e:
            logger.error(f"Batch {batch_num}: raised after completion: {e}")
            all_validated.extend(_unanalyzed_entry(c) for c in batch)
            skipped_batches += 1

    return all_validated, skipped_batches


async def _assess_batch_async(
    batch_clauses: list[dict],
    doc_type: str,
    locale_hint: str,
    batch_num,
) -> list[dict]:
    logger.info(f"Assessing batch {batch_num} ({len(batch_clauses)} clauses)")
    prompt = _build_assessment_prompt(batch_clauses, doc_type, locale_hint)
    llm = get_llm(max_tokens=4000, temperature=0.1)
    semaphore = _get_semaphore()

    for attempt in range(MAX_ATTEMPTS_PER_BATCH):
        try:
            # FIX: actual network call is now gated by the global semaphore,
            # so at most MAX_CONCURRENT_LLM_CALLS requests are ever in-flight
            # at once — regardless of how many batches/rescue-chunks were
            # scheduled concurrently.
            async with semaphore:
                response = await asyncio.wait_for(
                    llm.ainvoke(prompt), timeout=PER_ATTEMPT_LLM_TIMEOUT_SECONDS
                )
            content = response.content.strip()

            json_match = re.search(r'\[.*\]', content, re.DOTALL)
            if not json_match:
                logger.warning(f"Batch {batch_num}: no JSON array on attempt {attempt + 1}")
                if attempt < MAX_ATTEMPTS_PER_BATCH - 1:
                    await asyncio.sleep(RETRY_BACKOFF_SECONDS)
                continue

            assessed = json.loads(json_match.group())
            validated, rejected = _validate_assessed_clauses(assessed, batch_clauses)

            if validated and rejected < max(1, len(batch_clauses) // 3):
                return validated

            logger.warning(
                f"Batch {batch_num}: unreliable on attempt {attempt + 1} "
                f"(validated={len(validated)}, rejected={rejected})"
            )
            if attempt < MAX_ATTEMPTS_PER_BATCH - 1:
                await asyncio.sleep(RETRY_BACKOFF_SECONDS)

        except asyncio.TimeoutError:
            logger.warning(
                f"Batch {batch_num}: LLM call exceeded "
                f"{PER_ATTEMPT_LLM_TIMEOUT_SECONDS}s on attempt {attempt + 1}"
            )
            if attempt < MAX_ATTEMPTS_PER_BATCH - 1:
                await asyncio.sleep(RETRY_BACKOFF_SECONDS)

        except json.JSONDecodeError as e:
            logger.warning(f"Batch {batch_num}: JSON parse error on attempt {attempt + 1}: {e}")
            if attempt < MAX_ATTEMPTS_PER_BATCH - 1:
                await asyncio.sleep(RETRY_BACKOFF_SECONDS)

        except Exception as e:
            error_str = str(e)
            if _is_rate_limit_error(error_str):
                wait_s = min(
                    _parse_retry_after_seconds(error_str),
                    RATE_LIMIT_WAIT_CAP_SECONDS,
                )
                logger.warning(
                    f"Batch {batch_num}: rate limit on attempt {attempt + 1} "
                    f"— waiting {wait_s:.1f}s"
                )
                if attempt < MAX_ATTEMPTS_PER_BATCH - 1:
                    await asyncio.sleep(wait_s)
            else:
                logger.warning(f"Batch {batch_num}: error on attempt {attempt + 1}: {e}")
                if attempt < MAX_ATTEMPTS_PER_BATCH - 1:
                    await asyncio.sleep(RETRY_BACKOFF_SECONDS)

    logger.error(
        f"Batch {batch_num}: all {MAX_ATTEMPTS_PER_BATCH} attempts failed "
        f"({len(batch_clauses)} clauses) — flagging for manual review"
    )
    return [_unanalyzed_entry(c) for c in batch_clauses]


# ── Validation ─────────────────────────────────────────────────

def _validate_assessed_clauses(
    assessed: list,
    batch_clauses: list[dict],
) -> tuple[list[dict], int]:
    validated = []
    rejected  = 0
    seen_indices: set[int] = set()

    for r in assessed:
        if not isinstance(r, dict):
            rejected += 1
            continue
        if not all(k in r for k in ["index", "clause_type", "risk_level", "confidence"]):
            rejected += 1
            continue

        idx = r.get("index", -1)
        if not (isinstance(idx, int) and 0 <= idx < len(batch_clauses)):
            rejected += 1
            continue
        if idx in seen_indices:
            logger.warning(f"Duplicate index {idx} in LLM response — rejecting")
            rejected += 1
            continue
        seen_indices.add(idx)

        source_clause  = batch_clauses[idx]
        returned_type  = _sanitize_clause_type(r.get("clause_type", "")).strip()
        expected_type  = (source_clause.get("clause_type") or "").strip()

        # Reject wrong labels instead of silently accepting
        if not _clause_type_matches(expected_type, returned_type):
            logger.warning(
                f"Rejected relabeled clause at index {idx}: "
                f"'{expected_type}' → '{returned_type}'"
            )
            rejected += 1
            continue

        out = {
            "clause_type":             source_clause.get("clause_type", "Unknown Clause"),
            "category":                source_clause.get("category", "Other"),
            "original_text":           source_clause.get("original_text", ""),
            "section_ref":             source_clause.get("section_ref", "Unknown"),
            "reason":                  r.get("reason", ""),
            "financial_impact":        r.get("financial_impact", ""),
            "real_world_consequences": r.get("real_world_consequences", ""),
            "negotiation_tip":         r.get(
                "negotiation_tip",
                "Request clarification or amendment on this clause."
            ),
            "suggested_replacement":   r.get("suggested_replacement", ""),
        }

        raw_conf = r.get("confidence", 70)
        try:
            out["confidence"] = max(50, min(99, int(raw_conf)))
        except (ValueError, TypeError):
            out["confidence"] = 70

        risk_level = str(r.get("risk_level", "MEDIUM")).upper().strip()
        out["risk_level"] = risk_level if risk_level in ("HIGH", "MEDIUM", "LOW", "SAFE") else "MEDIUM"

        original = out["original_text"].strip().lower()
        if original in ("not applicable", "n/a", "none", "na", "-", ""):
            logger.debug(f"Filtered phantom: {out['clause_type']}")
            continue

        validated.append(out)

    return validated, rejected


# ── Fallback ───────────────────────────────────────────────────

def _unanalyzed_entry(source_clause: dict) -> dict:
    return {
        "clause_type":             source_clause.get("clause_type", "Unknown Clause"),
        "category":                source_clause.get("category", "Other"),
        "original_text":           source_clause.get("original_text", ""),
        "section_ref":             source_clause.get("section_ref", "Unknown"),
        "risk_level":              "UNKNOWN",
        "confidence":              None,
        "reason":                  "This clause could not be analyzed within the time budget. Please review it manually.",
        "financial_impact":        "",
        "real_world_consequences": "",
        "negotiation_tip":         "",
        "suggested_replacement":   "",
    }


def _fallback_response() -> list:
    return [{
        "clause_type":             "Analysis Failed",
        "original_text":           "",
        "risk_level":              "UNKNOWN",
        "confidence":              None,
        "reason":                  "Could not analyze document. Please try again.",
        "financial_impact":        "",
        "real_world_consequences": "",
        "negotiation_tip":         "",
        "suggested_replacement":   "",
    }]