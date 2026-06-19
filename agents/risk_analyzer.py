"""
Pass 2: Risk Assessment.
Takes extracted clauses (from Pass 1) and assesses each for risk level,
provides reasoning, and generates negotiation tips.
Uses the full document context + few-shot examples for high-quality output.
"""

import json
import re
import time
from utils.llm import get_llm
from utils.logger import get_logger

logger = get_logger("risk_analyzer")

# ── Doc-type aware analyst persona ────────────────────────────
PERSONA_MAP = {
    "OFFER_LETTER":         "employment lawyer specializing in Indian labor law and fresh-graduate offers",
    "EMPLOYMENT_CONTRACT":  "employment lawyer specializing in Indian labor law and employment agreements",
    "RENT_AGREEMENT":       "property lawyer specializing in Indian rental and tenancy laws",
    "INTERNSHIP_CONTRACT":  "employment lawyer advising fresh graduates and interns in India",
    "SERVICE_AGREEMENT":    "commercial contracts lawyer specializing in Indian business law",
    "NDA":                  "IP and confidentiality law specialist in India",
    "OTHER":                "senior legal analyst with expertise in Indian contract law",
}

# ── Few-shot examples for quality anchoring ───────────────────
FEW_SHOT_EXAMPLES = """
EXAMPLE OUTPUT (showing the quality and detail expected):
[
  {
    "clause_type": "Non-Compete Restriction",
    "original_text": "Employee shall not engage in any business competing with the Company for a period of 2 years after termination of employment",
    "risk_level": "HIGH",
    "confidence": 92,
    "reason": "2-year non-compete is excessively long. Indian courts have generally held post-employment non-compete clauses as unenforceable under Section 27 of the Indian Contract Act, 1872, but the clause could still create practical barriers and intimidation during job transitions.",
    "negotiation_tip": "Request reduction to 6 months maximum, limit scope to direct competitors only, and restrict geographic area to the city of employment. Cite Section 27 of the Indian Contract Act if challenged."
  },
  {
    "clause_type": "IP and Invention Assignment",
    "original_text": "any creation, innovation or intellectual property developed during the term of employment shall be the exclusive property of the Company",
    "risk_level": "MEDIUM",
    "confidence": 85,
    "reason": "The clause assigns all IP to the employer without distinguishing between work created during office hours using company resources vs personal projects. This is common but overly broad — it could claim ownership of a side project or open-source contribution you build on weekends.",
    "negotiation_tip": "Add an exception clause: 'IP created outside of working hours, without using Company resources, and unrelated to Company business, shall remain the Employee's property.' Get this in writing."
  },
  {
    "clause_type": "Probation Period",
    "original_text": "The probationary period will be of Six (6) Months from the date of joining",
    "risk_level": "SAFE",
    "confidence": 90,
    "reason": "6-month probation is standard practice in India across most industries. The period is reasonable and gives both parties time to evaluate the fit.",
    "negotiation_tip": "No action needed — this is a standard and fair clause. Confirm that performance review criteria during probation are clearly defined."
  }
]"""

# ── Risk checks by document type (what to look for) ───────────
RISK_FOCUS = {
    "OFFER_LETTER": [
        "Is the notice period reasonable (30-90 days)?",
        "Does the IP clause cover personal projects or only work-related IP?",
        "Is there a bond/training cost recovery clause? How much and how long?",
        "Is the non-compete scope and duration reasonable?",
        "Are salary revision terms at employer's sole discretion?",
        "Is the relocation clause open-ended?",
        "Does it restrict moonlighting or side projects?",
        "Is the variable pay subject to arbitrary deductions?",
    ],
    "EMPLOYMENT_CONTRACT": [
        "Is the notice period and buyout amount reasonable?",
        "Does IP assignment cover personal/off-hours projects?",
        "Is 'gross misconduct' defined narrowly or left vague?",
        "Is the non-compete enforceable under Indian law (Section 27)?",
        "Is indemnity unlimited or capped?",
        "Is there a garden leave provision?",
        "Is jurisdiction clause fair (local vs distant court)?",
        "Is the probation period and confirmation process clear?",
        "Is there a bond period or training cost recovery?",
        "Are salary revision terms discretionary or structured?",
    ],
    "RENT_AGREEMENT": [
        "Is the security deposit amount reasonable (1-3 months)?",
        "Are refund conditions for deposit clearly stated?",
        "Is rent escalation capped (5-10% per year is standard)?",
        "Who bears maintenance and major repair costs?",
        "Is subletting explicitly restricted?",
        "Is there a lock-in period with penalties?",
        "Does the landlord have unrestricted inspection rights?",
        "Is the notice period for vacating reasonable?",
        "Can the landlord terminate without cause?",
    ],
    "INTERNSHIP_CONTRACT": [
        "Is IP ownership of intern's work clearly defined?",
        "Is there a conversion-to-full-time clause?",
        "Is the stipend payment timeline clear?",
        "Are working hours and overtime expectations defined?",
        "Is the confidentiality duration reasonable?",
        "Is there a non-compete for interns (unusual and concerning)?",
    ],
    "SERVICE_AGREEMENT": [
        "Are payment terms and timelines clear?",
        "Is scope creep handled (change request process)?",
        "Who owns the deliverables/IP?",
        "Is there a termination-for-convenience clause (risky for service provider)?",
        "Is the liability cap reasonable?",
        "Is there auto-renewal with difficult exit?",
        "Is the indemnity clause balanced?",
    ],
    "NDA": [
        "Is 'confidential information' defined too broadly?",
        "Is the confidentiality duration excessive (over 3-5 years)?",
        "Is there a residuals clause (knowledge retained in memory)?",
        "Are standard exceptions included (public knowledge, independent development)?",
        "Is it mutual or one-sided?",
        "Is the injunctive relief clause proportionate?",
        "Are return/destruction obligations clear?",
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


def _prepare_text_sample(text: str, max_chars: int = 20000) -> str:
    """
    Send as much document text as possible for context.
    For docs under max_chars, sends the full text.
    For longer docs, uses beginning + middle + end sampling.
    """
    if len(text) <= max_chars:
        return text

    chunk = max_chars // 3
    beginning = text[:chunk]
    mid_start = len(text) // 2 - chunk // 2
    middle = text[mid_start: mid_start + chunk]
    end = text[-chunk:]
    return (
        f"{beginning}\n\n"
        f"[... document continues — middle section ...]\n\n"
        f"{middle}\n\n"
        f"[... document continues — final section ...]\n\n"
        f"{end}"
    )


def _build_assessment_prompt(
    extracted_clauses: list[dict],
    doc_type: str,
    full_text: str,
) -> str:
    """Build the risk assessment prompt with extracted clauses + full context."""
    persona = PERSONA_MAP.get(doc_type, PERSONA_MAP["OTHER"])
    doc_label = doc_type.replace("_", " ").title()
    focus = RISK_FOCUS.get(doc_type, DEFAULT_FOCUS)
    focus_text = "\n".join(f"  - {f}" for f in focus)
    text_sample = _prepare_text_sample(full_text)

    # Format extracted clauses for the LLM
    clauses_text = ""
    for i, c in enumerate(extracted_clauses):
        clauses_text += f"""
Clause {i + 1}: {c.get('clause_type', 'Unknown')}
  Category: {c.get('category', 'Other')}
  Original Text: {c.get('original_text', '')[:300]}
  Section: {c.get('section_ref', 'Unknown')}
---"""

    return f"""You are a {persona} conducting a thorough risk assessment of a {doc_label}.

CONTEXT: The clauses below have already been extracted from the document. Your job is to ASSESS the risk level of each clause and provide expert analysis.

RISK LEVEL CRITERIA — apply these precisely:
- HIGH: Clauses causing significant financial loss (>1 lakh), career restriction (>1 year), unlimited personal liability, or legal exposure. The person signing would be materially harmed.
  Examples: non-compete over 1 year, unlimited indemnity, IP assignment covering personal projects, bond period over 1 year, termination without notice.
- MEDIUM: Clauses that are unfavorable but negotiable. Common in Indian contracts but should be reviewed. Moderate financial or career impact.
  Examples: vague termination criteria, broad confidentiality without time limit, salary revision at sole discretion, 3-month notice period, relocation clause.
- LOW: Minor concerns. Slightly one-sided but industry standard. Minimal practical impact on the signer.
  Examples: standard probation, reasonable working hours clause, minor penalty for late payment, standard data protection terms.
- SAFE: Fair, balanced, legally standard clauses that protect both parties. No action needed.
  Examples: mutual 30-day notice, clear salary structure, standard leave policy, reasonable jurisdiction clause.

FOCUS AREAS for {doc_label}:
{focus_text}

{FEW_SHOT_EXAMPLES}

NOW ASSESS THESE EXTRACTED CLAUSES:
{clauses_text}

FULL DOCUMENT (for reference — use this to understand context around each clause):
{text_sample}

Return a JSON array with EXACTLY {len(extracted_clauses)} objects (one per clause above), each with:
{{
  "clause_type": "descriptive name (do NOT include risk level in the name)",
  "original_text": "exact text from the document (same as provided above)",
  "risk_level": "HIGH or MEDIUM or LOW or SAFE",
  "confidence": integer 60-99,
  "reason": "2-3 sentences: (1) what this means in practice, (2) why this risk level, (3) reference to Indian law if applicable",
  "negotiation_tip": "specific actionable advice — what exactly to say or request. For SAFE clauses: 'No action needed — this is a standard and fair clause.'"
}}

RULES:
- Return ONLY a valid JSON array — no markdown fences, no commentary
- Assess EVERY clause listed above — do not skip any
- Use original_text exactly as provided
- Be specific to Indian legal context
- Confidence should reflect how certain you are about the risk level
- Do NOT add new clauses — only assess the ones provided
"""


def assess_risks(
    extracted_clauses: list[dict],
    doc_type: str,
    full_text: str,
) -> list[dict]:
    """
    Pass 2: Assess risk for each extracted clause.
    Takes pre-extracted clauses and adds risk_level, confidence,
    reason, and negotiation_tip.
    """
    if not extracted_clauses:
        logger.warning("No clauses to assess")
        return _fallback_response()

    logger.info(f"Assessing {len(extracted_clauses)} clauses | doc_type={doc_type}")

    prompt = _build_assessment_prompt(extracted_clauses, doc_type, full_text)
    llm = get_llm(max_tokens=5000, temperature=0.1)

    for attempt in range(3):
        try:
            response = llm.invoke(prompt)
            content = response.content.strip()

            # Extract JSON array
            json_match = re.search(r'\[.*\]', content, re.DOTALL)
            if not json_match:
                logger.warning(f"No JSON array on attempt {attempt + 1}")
                if attempt < 2:
                    time.sleep(2 ** attempt)
                continue

            assessed = json.loads(json_match.group())

            # Validate each assessed clause
            validated = []
            for r in assessed:
                if not isinstance(r, dict):
                    continue
                if not all(k in r for k in ["clause_type", "risk_level", "confidence"]):
                    continue

                # Sanitize
                r["clause_type"] = _sanitize_clause_type(
                    r.get("clause_type", "Unknown Clause")
                )
                r.setdefault("original_text", "")
                r.setdefault("reason", "")
                r.setdefault(
                    "negotiation_tip",
                    "Request clarification or amendment on this clause."
                )

                # Clamp confidence
                r["confidence"] = max(60, min(99, int(r.get("confidence", 70))))

                # Normalize risk level
                r["risk_level"] = r["risk_level"].upper().strip()
                if r["risk_level"] not in ("HIGH", "MEDIUM", "LOW", "SAFE"):
                    r["risk_level"] = "MEDIUM"

                # Filter out phantom clauses (last safety net)
                original = r.get("original_text", "").strip().lower()
                if original in ("not applicable", "n/a", "none", "na", "-", ""):
                    logger.debug(f"Filtered phantom: {r.get('clause_type')}")
                    continue

                validated.append(r)

            if validated:
                logger.info(
                    f"Assessment complete: {len(validated)} clauses | "
                    f"HIGH={sum(1 for r in validated if r['risk_level'] == 'HIGH')} | "
                    f"MEDIUM={sum(1 for r in validated if r['risk_level'] == 'MEDIUM')} | "
                    f"LOW={sum(1 for r in validated if r['risk_level'] == 'LOW')} | "
                    f"SAFE={sum(1 for r in validated if r['risk_level'] == 'SAFE')} | "
                    f"attempt={attempt + 1}"
                )
                return validated

            logger.warning(f"No valid assessments on attempt {attempt + 1}")
            if attempt < 2:
                time.sleep(2 ** attempt)

        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse error on attempt {attempt + 1}: {e}")
            if attempt < 2:
                time.sleep(2 ** attempt)
        except Exception as e:
            logger.warning(f"Assessment error on attempt {attempt + 1}: {e}")
            if attempt < 2:
                time.sleep(2 ** attempt)

    logger.error("All assessment attempts failed. Returning fallback.")
    return _fallback_response()


def _fallback_response() -> list:
    """Last resort when all LLM attempts fail."""
    return [{
        "clause_type":     "Analysis Failed",
        "original_text":   "",
        "risk_level":      "UNKNOWN",
        "confidence":      0,
        "reason":          "Could not analyze document. Please try again.",
        "negotiation_tip": ""
    }]
