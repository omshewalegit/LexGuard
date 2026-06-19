"""
Simplifier: Converts legal analysis into plain-language explanations.
Takes assessed risk clauses and adds simple_explanation for each.
"""

import json
import re
import time
import copy
from utils.llm import get_llm
from utils.logger import get_logger

logger = get_logger("simplifier")

# ── Persona by document type ─────────────────────────────────
_PERSONA_MAP = {
    "OFFER_LETTER":         "a 22-year-old fresh graduate in India who just got their first job offer",
    "EMPLOYMENT_CONTRACT":  "a working professional in India signing an employment contract",
    "RENT_AGREEMENT":       "a young tenant in India renting their first apartment",
    "INTERNSHIP_CONTRACT":  "a college student in India starting their first internship",
    "SERVICE_AGREEMENT":    "a freelancer or small business owner in India signing a service contract",
    "NDA":                  "a professional in India being asked to sign a non-disclosure agreement",
    "OTHER":                "an ordinary person in India reviewing a legal document",
}


def simplify_risks(risks: list, doc_type: str) -> list:
    """
    Batch simplify all clauses in ONE API call.
    Uses deep copy — never mutates the original list from pipeline state.
    """
    if not risks:
        return []

    risks_copy = copy.deepcopy(risks)
    doc_label = doc_type.replace("_", " ").title()
    audience = _PERSONA_MAP.get(doc_type, _PERSONA_MAP["OTHER"])

    clauses_text = ""
    for i, r in enumerate(risks_copy):
        clauses_text += f"""
Clause {i + 1}:
  Type: {r.get('clause_type')}
  Risk Level: {r.get('risk_level')}
  Original Text: {r.get('original_text', '')[:300]}
  Reason: {r.get('reason')}
  Negotiation Tip: {r.get('negotiation_tip', '')}
---"""

    prompt = f"""You are a legal expert explaining a {doc_label} to {audience}.

Your goal is to make each clause crystal clear to someone with NO legal background. They should understand exactly what they're agreeing to and what could happen to them.

For EACH clause below, write a clear explanation in EXACTLY 2-3 sentences:
1. FIRST SENTENCE: What this clause actually means — translate the legal language into everyday words. Start with "This clause means..." or "This means..."
2. SECOND SENTENCE: The specific real-world consequence — how it can hurt or protect them. Be concrete (mention money amounts, time periods, career impact if applicable).
3. THIRD SENTENCE (for risky clauses): One concrete action to take. For SAFE clauses: confirm it's fair and say no action is needed.

Return a JSON array with EXACTLY {len(risks_copy)} objects:
[
  {{
    "index": 0,
    "simple_explanation": "your 2-3 sentence explanation here"
  }}
]

RULES:
- Return ONLY the JSON array — no markdown fences, no commentary
- index is 0-based (Clause 1 = index 0, Clause 2 = index 1, etc.)
- Write as if talking to a friend over coffee, not writing a legal memo
- Be specific to the Indian context (mention Indian laws, typical Indian salary ranges, etc. where relevant)
- For SAFE clauses: explain WHY it's fair — don't just say "this is standard"
- Each explanation must be unique and specific to that clause — no generic copy-paste
- Use specific numbers and timeframes from the document when available

Clauses:
{clauses_text}
"""

    llm = get_llm(max_tokens=4000, temperature=0.2)

    for attempt in range(3):
        try:
            response = llm.invoke(prompt)
            content = response.content.strip()

            json_match = re.search(r'\[.*\]', content, re.DOTALL)
            if json_match:
                explanations = json.loads(json_match.group())

                for exp in explanations:
                    idx = exp.get("index", -1)
                    if 0 <= idx < len(risks_copy):
                        risks_copy[idx]["simple_explanation"] = exp.get(
                            "simple_explanation",
                            "No explanation available."
                        )

                # Fill any gaps — use reason as fallback
                for r in risks_copy:
                    if "simple_explanation" not in r:
                        r["simple_explanation"] = r.get(
                            "reason", "Review this clause carefully."
                        )

                logger.info(f"Simplified {len(risks_copy)} clauses | attempt={attempt + 1}")
                return risks_copy

            logger.warning(f"No valid JSON on attempt {attempt + 1}")
            if attempt < 2:
                time.sleep(2 ** attempt)

        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"JSON parse error on attempt {attempt + 1}: {e}")
            if attempt < 2:
                time.sleep(2 ** attempt)
        except Exception as e:
            logger.warning(f"Unexpected error on attempt {attempt + 1}: {e}")
            if attempt < 2:
                time.sleep(2 ** attempt)

    # Fallback — use reason as explanation
    logger.error("All simplification attempts failed — using fallback")
    for r in risks_copy:
        if "simple_explanation" not in r:
            r["simple_explanation"] = r.get("reason", "Review this clause carefully.")

    return risks_copy
