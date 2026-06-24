# """
# Simplifier: Converts legal analysis into plain-language explanations.
# Takes assessed risk clauses and adds simple_explanation for each.
# """

# import json
# import re
# import time
# import copy
# from utils.llm import get_llm
# from utils.logger import get_logger

# logger = get_logger("simplifier")

# # ── Persona by document type ─────────────────────────────────
# _PERSONA_MAP = {
#     "OFFER_LETTER":         "a 22-year-old fresh graduate in India who just got their first job offer",
#     "EMPLOYMENT_CONTRACT":  "a working professional in India signing an employment contract",
#     "RENT_AGREEMENT":       "a young tenant in India renting their first apartment",
#     "INTERNSHIP_CONTRACT":  "a college student in India starting their first internship",
#     "SERVICE_AGREEMENT":    "a freelancer or small business owner in India signing a service contract",
#     "NDA":                  "a professional in India being asked to sign a non-disclosure agreement",
#     "OTHER":                "an ordinary person in India reviewing a legal document",
# }


# def simplify_risks(risks: list, doc_type: str) -> list:
#     """
#     Batch simplify all clauses in ONE API call.
#     Uses deep copy — never mutates the original list from pipeline state.
#     """
#     if not risks:
#         return []

#     risks_copy = copy.deepcopy(risks)
#     doc_label = doc_type.replace("_", " ").title()
#     audience = _PERSONA_MAP.get(doc_type, _PERSONA_MAP["OTHER"])

#     clauses_text = ""
#     for i, r in enumerate(risks_copy):
#         clauses_text += f"""
# Clause {i + 1}:
#   Type: {r.get('clause_type')}
#   Risk Level: {r.get('risk_level')}
#   Original Text: {r.get('original_text', '')[:300]}
#   Reason: {r.get('reason')}
#   Negotiation Tip: {r.get('negotiation_tip', '')}
# ---"""

#     prompt = f"""You are a legal expert explaining a {doc_label} to {audience}.

# Your goal is to make each clause crystal clear to someone with NO legal background. They should understand exactly what they're agreeing to and what could happen to them.

# For EACH clause below, write a clear explanation in EXACTLY 2-3 sentences:
# 1. FIRST SENTENCE: What this clause actually means — translate the legal language into everyday words. Start with "This clause means..." or "This means..."
# 2. SECOND SENTENCE: The specific real-world consequence — how it can hurt or protect them. Be concrete (mention money amounts, time periods, career impact if applicable).
# 3. THIRD SENTENCE (for risky clauses): One concrete action to take. For SAFE clauses: confirm it's fair and say no action is needed.

# Return a JSON array with EXACTLY {len(risks_copy)} objects:
# [
#   {{
#     "index": 0,
#     "simple_explanation": "your 2-3 sentence explanation here"
#   }}
# ]

# RULES:
# - Return ONLY the JSON array — no markdown fences, no commentary
# - index is 0-based (Clause 1 = index 0, Clause 2 = index 1, etc.)
# - Write as if talking to a friend over coffee, not writing a legal memo
# - Be specific to the Indian context (mention Indian laws, typical Indian salary ranges, etc. where relevant)
# - For SAFE clauses: explain WHY it's fair — don't just say "this is standard"
# - Each explanation must be unique and specific to that clause — no generic copy-paste
# - Use specific numbers and timeframes from the document when available

# Clauses:
# {clauses_text}
# """

#     llm = get_llm(max_tokens=4000, temperature=0.2)

#     for attempt in range(3):
#         try:
#             response = llm.invoke(prompt)
#             content = response.content.strip()

#             json_match = re.search(r'\[.*\]', content, re.DOTALL)
#             if json_match:
#                 explanations = json.loads(json_match.group())

#                 for exp in explanations:
#                     idx = exp.get("index", -1)
#                     if 0 <= idx < len(risks_copy):
#                         risks_copy[idx]["simple_explanation"] = exp.get(
#                             "simple_explanation",
#                             "No explanation available."
#                         )

#                 # Fill any gaps — use reason as fallback
#                 for r in risks_copy:
#                     if "simple_explanation" not in r:
#                         r["simple_explanation"] = r.get(
#                             "reason", "Review this clause carefully."
#                         )

#                 logger.info(f"Simplified {len(risks_copy)} clauses | attempt={attempt + 1}")
#                 return risks_copy

#             logger.warning(f"No valid JSON on attempt {attempt + 1}")
#             if attempt < 2:
#                 time.sleep(2 ** attempt)

#         except (json.JSONDecodeError, ValueError) as e:
#             logger.warning(f"JSON parse error on attempt {attempt + 1}: {e}")
#             if attempt < 2:
#                 time.sleep(2 ** attempt)
#         except Exception as e:
#             logger.warning(f"Unexpected error on attempt {attempt + 1}: {e}")
#             if attempt < 2:
#                 time.sleep(2 ** attempt)

#     # Fallback — use reason as explanation
#     logger.error("All simplification attempts failed — using fallback")
#     for r in risks_copy:
#         if "simple_explanation" not in r:
#             r["simple_explanation"] = r.get("reason", "Review this clause carefully.")

#     return risks_copy
"""
Simplifier: Converts legal analysis into plain-language explanations.
Takes assessed risk clauses and adds simple_explanation for each.

FIX HISTORY:
1) (original) Batched concurrent simplification with staggered start and
   reason-text fallback for timed-out clauses.
2) (2026-06-22, fix #1) [CURRENT]
   - SIMPLIFY_BATCH_SIZE reduced 10 → 7: 10 clauses × 3 sentences each was
     pushing max_tokens=2000 to its limit (200 tokens/clause), causing
     mid-JSON truncation → parse error → retry loop. 7 clauses gives ~285
     tokens/clause — enough for clean 2-3 sentence output.
   - max_tokens raised 2000 → 2500: gives headroom so output is never
     truncated even if the model writes slightly longer explanations.
   - SIMPLIFY_OVERALL_DEADLINE raised 40s → 60s:
     Math: 6 batches (36 clauses ÷ 7) × 1.0s stagger = batch6 starts at 5s
     + 24s × 3 attempts + 1.0s × 2 backoff = 57s worst case. 40s was
     impossible for a 36-clause doc.
   - PER_ATTEMPT_LLM_TIMEOUT raised 20s → 24s: matches other agents.
   - MAX_ATTEMPTS raised 2 → 3: consistent with risk_analyzer/extractor.
   - BATCH_STAGGER raised 0.5s → 1.0s: reduces Groq key contention.
   - Clause type alignment check relaxed: was doing exact string match which
     rejected valid explanations on trivial casing/whitespace differences.
     Now uses normalized comparison (lowercase + stripped).
   - RETRY_BACKOFF raised 0.75s → 1.0s for consistency across agents.
"""

import asyncio
import json
import re
import time
import copy
from utils.llm import get_fast_llm as get_llm
from utils.logger import get_logger
import nest_asyncio
nest_asyncio.apply()

logger = get_logger("simplifier")

_PERSONA_MAP = {
    "OFFER_LETTER":         "a 22-year-old fresh graduate who just got their first job offer",
    "EMPLOYMENT_CONTRACT":  "a working professional signing an employment contract",
    "RENT_AGREEMENT":       "a young tenant renting their first apartment",
    "INTERNSHIP_CONTRACT":  "a college student starting their first internship",
    "SERVICE_AGREEMENT":    "a freelancer or small business owner signing a service contract",
    "NDA":                  "a professional being asked to sign a non-disclosure agreement",
    "OTHER":                "an ordinary person reviewing a legal document",
}

# ── Batching ──────────────────────────────────────────────────────────────────
SIMPLIFY_BATCH_SIZE = 7      # ↓ from 10: prevents output truncation mid-JSON

# ── Timing knobs ──────────────────────────────────────────────────────────────
BATCH_STAGGER_SECONDS               = 1.0    # ↑ from 0.5
PER_ATTEMPT_LLM_TIMEOUT_SECONDS     = 24.0   # ↑ from 20
MAX_ATTEMPTS_PER_BATCH              = 3      # ↑ from 2
RETRY_BACKOFF_SECONDS               = 1.0    # ↑ from 0.75
# Math: 36 clauses ÷ 7 = 6 batches; batch6 starts at 5s
#       + 24s × 3 attempts + 1.0s × 2 backoff = 57s worst case
SIMPLIFY_OVERALL_DEADLINE_SECONDS   = 60.0   # ↑ from 40


def _locale_instruction(locale_hint: str | None) -> str:
    return (
        f"This document is governed by the laws of {locale_hint}. "
        f"Only reference {locale_hint}-specific laws, currency, or norms — "
        f"never assume any other country's laws or currency."
        if locale_hint else
        "The document's jurisdiction/currency is not confirmed. "
        "Do NOT assume any specific country's laws or currency (no ₹, no IT Act, "
        "no jurisdiction-specific claims) unless the clause text itself states it. "
        "Keep guidance general and currency-neutral, or use the currency/figures "
        "actually present in the clause text."
    )


def _normalize_type(s: str) -> str:
    """Lowercase, strip, collapse whitespace — for loose type matching."""
    return re.sub(r'\s+', ' ', (s or "").lower().strip())


def _build_simplify_prompt(
    batch_risks: list[dict],
    doc_type: str,
    locale_hint: str | None,
) -> str:
    doc_label = doc_type.replace("_", " ").title()
    audience  = _PERSONA_MAP.get(doc_type, _PERSONA_MAP["OTHER"])

    clauses_text = ""
    for i, r in enumerate(batch_risks):
        clauses_text += f"""
Clause {i + 1}:
  Type: {r.get('clause_type')}
  Risk Level: {r.get('risk_level')}
  Original Text: {r.get('original_text', '')[:300]}
  Reason: {r.get('reason')}
  Negotiation Tip: {r.get('negotiation_tip', '')}
---"""

    return f"""You are a legal expert explaining a {doc_label} to {audience}.

{_locale_instruction(locale_hint)}

Your goal is to make each clause crystal clear to someone with NO legal background. They should understand exactly what they're agreeing to and what could happen to them.

For EACH clause below, write a clear explanation in EXACTLY 2-3 sentences:
1. FIRST SENTENCE: What this clause actually means in everyday words. Start with "This clause means..." or "This means..."
2. SECOND SENTENCE: The specific real-world consequence — how it can hurt or protect them. Be concrete. Mention amounts or time periods ONLY if they appear in the clause's Original Text above — never invent numbers.
3. THIRD SENTENCE (for HIGH or MEDIUM risk): One concrete action to take. For SAFE or LOW clauses: confirm it's fair and say no action is needed.

Return a JSON array with EXACTLY {len(batch_risks)} objects:
[
  {{
    "index": 0,
    "clause_type": "<copy the exact Type value shown for that clause above>",
    "simple_explanation": "your 2-3 sentence explanation here"
  }}
]

RULES:
- Return ONLY the JSON array — no markdown fences, no commentary
- index is 0-based and LOCAL to this list (Clause 1 = index 0, Clause 2 = index 1, etc.)
- Write as if talking to a friend, not writing a legal memo
- NEVER invent numbers, amounts, or timeframes not present in the Original Text
- Each explanation must be specific to that clause — no generic copy-paste
- For SAFE clauses: explain WHY it's fair, not just "this is standard"

Clauses:
{clauses_text}
"""


async def _simplify_batch_async(
    batch_risks: list[dict],
    doc_type: str,
    locale_hint: str | None,
    batch_num: int,
) -> None:
    """
    Mutates batch_risks IN PLACE, setting simple_explanation on each dict.
    Gaps (rejected or timed-out entries) are filled by the caller's fallback loop.
    """
    logger.info(f"Simplify batch {batch_num}: {len(batch_risks)} clause(s)")
    prompt = _build_simplify_prompt(batch_risks, doc_type, locale_hint)
    llm    = get_llm(max_tokens=2500, temperature=0.2)  # ↑ from 2000

    for attempt in range(MAX_ATTEMPTS_PER_BATCH):
        try:
            response = await asyncio.wait_for(
                llm.ainvoke(prompt), timeout=PER_ATTEMPT_LLM_TIMEOUT_SECONDS
            )
            content = response.content.strip()

            json_match = re.search(r'\[.*\]', content, re.DOTALL)
            if not json_match:
                logger.warning(
                    f"Simplify batch {batch_num}: no JSON array on attempt {attempt + 1}"
                )
                if attempt < MAX_ATTEMPTS_PER_BATCH - 1:
                    await asyncio.sleep(RETRY_BACKOFF_SECONDS)
                continue

            explanations = json.loads(json_match.group())

            accepted = 0
            rejected = 0
            for exp in explanations:
                idx = exp.get("index", -1)
                if not (isinstance(idx, int) and 0 <= idx < len(batch_risks)):
                    rejected += 1
                    continue

                # Relaxed type check: normalized comparison instead of exact match
                # Prevents rejecting valid explanations on trivial casing differences
                expected_type = _normalize_type(batch_risks[idx].get("clause_type", ""))
                returned_type = _normalize_type(exp.get("clause_type", ""))

                if expected_type and returned_type and expected_type != returned_type:
                    # Allow partial match — if one contains the other it's likely fine
                    if expected_type not in returned_type and returned_type not in expected_type:
                        logger.warning(
                            f"Simplify batch {batch_num}: type mismatch at index {idx}: "
                            f"expected '{expected_type}', got '{returned_type}' — rejecting"
                        )
                        rejected += 1
                        continue

                batch_risks[idx]["simple_explanation"] = exp.get(
                    "simple_explanation", "Review this clause carefully."
                )
                accepted += 1

            logger.info(
                f"Simplify batch {batch_num}: accepted={accepted} rejected={rejected} "
                f"on attempt {attempt + 1}"
            )

            # Retry if too many misaligned — but only on first attempt
            if rejected >= max(1, len(batch_risks) // 3) and attempt < MAX_ATTEMPTS_PER_BATCH - 1:
                await asyncio.sleep(RETRY_BACKOFF_SECONDS)
                continue

            return  # gaps filled by caller's fallback loop

        except asyncio.TimeoutError:
            logger.warning(
                f"Simplify batch {batch_num}: LLM call exceeded "
                f"{PER_ATTEMPT_LLM_TIMEOUT_SECONDS}s on attempt {attempt + 1}"
            )
            if attempt < MAX_ATTEMPTS_PER_BATCH - 1:
                await asyncio.sleep(RETRY_BACKOFF_SECONDS)

        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(
                f"Simplify batch {batch_num}: JSON parse error on attempt {attempt + 1}: {e}"
            )
            if attempt < MAX_ATTEMPTS_PER_BATCH - 1:
                await asyncio.sleep(RETRY_BACKOFF_SECONDS)

        except Exception as e:
            logger.warning(
                f"Simplify batch {batch_num}: error on attempt {attempt + 1}: {e}"
            )
            if attempt < MAX_ATTEMPTS_PER_BATCH - 1:
                await asyncio.sleep(RETRY_BACKOFF_SECONDS)

    logger.error(
        f"Simplify batch {batch_num}: all {MAX_ATTEMPTS_PER_BATCH} attempts failed "
        f"— falling back to `reason` text for {len(batch_risks)} clause(s)"
    )


async def _simplify_all_batches_with_deadline(
    batches: list[list[dict]],
    doc_type: str,
    locale_hint: str | None,
) -> None:
    async def _delayed(batch, batch_num, delay):
        if delay > 0:
            await asyncio.sleep(delay)
        await _simplify_batch_async(batch, doc_type, locale_hint, batch_num)

    tasks = [
        asyncio.ensure_future(_delayed(batch, i + 1, delay=i * BATCH_STAGGER_SECONDS))
        for i, batch in enumerate(batches)
    ]

    done, pending = await asyncio.wait(tasks, timeout=SIMPLIFY_OVERALL_DEADLINE_SECONDS)

    if pending:
        for t in pending:
            t.cancel()
        await asyncio.gather(*pending, return_exceptions=True)
        for batch_num, task in enumerate(tasks, start=1):
            if task in pending:
                logger.error(
                    f"Simplify batch {batch_num}: did not finish within "
                    f"{SIMPLIFY_OVERALL_DEADLINE_SECONDS}s deadline — "
                    f"falling back to `reason` text"
                )


def simplify_risks(
    risks: list,
    doc_type: str,
    locale_hint: str = None,
) -> list:
    """
    Batch-simplify all clauses concurrently within a hard time budget.
    Uses deep copy — never mutates the caller's original list.

    locale_hint: e.g. "Maharashtra, India" / "California, USA" — detected
    upstream from the document's governing-law clause. If None, the prompt
    stays jurisdiction-neutral.
    """
    if not risks:
        return []

    risks_copy = copy.deepcopy(risks)
    batches = [
        risks_copy[i:i + SIMPLIFY_BATCH_SIZE]
        for i in range(0, len(risks_copy), SIMPLIFY_BATCH_SIZE)
    ]

    start = time.monotonic()
    asyncio.run(_simplify_all_batches_with_deadline(batches, doc_type, locale_hint))
    elapsed = time.monotonic() - start

    # Fill any gaps — never leave a clause with no explanation
    filled_from_reason = 0
    for r in risks_copy:
        if "simple_explanation" not in r:
            r["simple_explanation"] = r.get("reason", "Review this clause carefully.")
            filled_from_reason += 1

    logger.info(
        f"Simplified {len(risks_copy)} clause(s) across {len(batches)} batch(es) "
        f"in {elapsed:.1f}s (deadline={SIMPLIFY_OVERALL_DEADLINE_SECONDS}s) | "
        f"fell_back_to_reason={filled_from_reason}"
    )

    return risks_copy