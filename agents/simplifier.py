# # from langchain_groq import ChatGroq
# # from dotenv import load_dotenv
# # import os
# # import json
# # import re
# # import time
# # import copy

# # load_dotenv()

# # GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# # llm = ChatGroq(
# #     api_key=GROQ_API_KEY,
# #     model_name="llama-3.3-70b-versatile",
# #     temperature=0.2,
# #     max_tokens=3000,
# #     timeout=60
# # )


# # def simplify_risks(risks: list, doc_type: str) -> list:
# #     """
# #     Batch simplify all clauses in ONE API call.
# #     Uses deep copy — never mutates original list.
# #     """
# #     if not risks:
# #         return []

# #     # Deep copy — never mutate original state
# #     risks_copy = copy.deepcopy(risks)

# #     clauses_text = ""
# #     for i, r in enumerate(risks_copy):
# #         clauses_text += f"""
# # Clause {i+1}:
# # Type: {r.get('clause_type')}
# # Risk Level: {r.get('risk_level')}
# # Original: {r.get('original_text', '')[:200]}
# # Reason: {r.get('reason')}
# # ---"""

# #     prompt = f"""You are a legal expert explaining contract clauses to a fresh graduate in India.

# # For each clause below, write a plain English explanation (2-3 sentences):
# # 1. What it actually means in simple words
# # 2. How it can specifically affect the person
# # 3. What they should do about it

# # Return a JSON array with exactly {len(risks_copy)} objects:
# # [
# #   {{
# #     "index": 0,
# #     "simple_explanation": "your explanation here"
# #   }}
# # ]

# # Rules:
# # - Return ONLY valid JSON array
# # - index must match clause number minus 1
# # - Be specific to Indian job/rental market
# # - For SAFE clauses: "This is a standard clause that protects both parties fairly."
# # - No markdown, no text outside array

# # Clauses:
# # {clauses_text}
# # """

# #     for attempt in range(3):
# #         try:
# #             response = llm.invoke(prompt)
# #             content = response.content.strip()

# #             json_match = re.search(r'\[.*\]', content, re.DOTALL)
# #             if json_match:
# #                 explanations = json.loads(json_match.group())

# #                 for exp in explanations:
# #                     idx = exp.get("index", -1)
# #                     if 0 <= idx < len(risks_copy):
# #                         risks_copy[idx]["simple_explanation"] = exp.get(
# #                             "simple_explanation",
# #                             "No explanation available."
# #                         )

# #                 # Fill any missing
# #                 for r in risks_copy:
# #                     if "simple_explanation" not in r:
# #                         r["simple_explanation"] = r.get("reason", "Review this clause carefully.")

# #                 return risks_copy

# #         except (json.JSONDecodeError, ValueError):
# #             if attempt == 2:
# #                 break
# #             time.sleep(2 ** attempt)
# #         except Exception:
# #             if attempt == 2:
# #                 break
# #             time.sleep(2 ** attempt)

# #     # Fallback
# #     for r in risks_copy:
# #         if "simple_explanation" not in r:
# #             r["simple_explanation"] = r.get("reason", "Review this clause carefully.")

# #     return risks_copy

# from langchain_groq import ChatGroq
# from dotenv import load_dotenv
# import os
# import json
# import re
# import time
# import copy
# from utils.logger import get_logger

# logger = get_logger("simplifier")

# load_dotenv()

# GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# # ── Lazy init ─────────────────────────────────────────────────
# _llm = None

# def _get_llm():
#     global _llm
#     if _llm is None:
#         _llm = ChatGroq(
#             api_key=GROQ_API_KEY,
#             model_name="llama-3.3-70b-versatile",
#             temperature=0.2,
#             max_tokens=3000,
#             timeout=60
#         )
#     return _llm


# def simplify_risks(risks: list, doc_type: str) -> list:
#     """
#     Batch simplify all clauses in ONE API call.
#     Uses deep copy — never mutates original list.
#     """
#     if not risks:
#         return []

#     risks_copy = copy.deepcopy(risks)

#     clauses_text = ""
#     for i, r in enumerate(risks_copy):
#         clauses_text += f"""
# Clause {i+1}:
# Type: {r.get('clause_type')}
# Risk Level: {r.get('risk_level')}
# Original: {r.get('original_text', '')[:200]}
# Reason: {r.get('reason')}
# Negotiation Tip: {r.get('negotiation_tip', '')}
# ---"""

#     prompt = f"""You are a legal expert explaining {doc_type.replace('_', ' ').title()} clauses to a non-lawyer.

# For each clause below, write a plain English explanation (2-3 sentences max):
# 1. What it actually means in simple words
# 2. How it can specifically affect the person signing
# 3. What they should do about it

# Return a JSON array with exactly {len(risks_copy)} objects:
# [
#   {{
#     "index": 0,
#     "simple_explanation": "your explanation here"
#   }}
# ]

# Rules:
# - Return ONLY valid JSON array
# - index must match clause number minus 1 (0-based)
# - Keep language simple — no legal jargon
# - For SAFE clauses: confirm why it is fair and standard
# - No markdown, no text outside the array

# Clauses:
# {clauses_text}
# """

#     for attempt in range(3):
#         try:
#             response = _get_llm().invoke(prompt)
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

#                 # Fill any missing explanations
#                 for r in risks_copy:
#                     if "simple_explanation" not in r:
#                         r["simple_explanation"] = r.get("reason", "Review this clause carefully.")

#                 logger.info(f"Simplified {len(risks_copy)} clauses")
#                 return risks_copy

#         except (json.JSONDecodeError, ValueError) as e:
#             logger.warning(f"JSON parse error on attempt {attempt + 1}: {e}")
#             if attempt == 2:
#                 break
#             time.sleep(2 ** attempt)
#         except Exception as e:
#             logger.warning(f"Unexpected error on attempt {attempt + 1}: {e}")
#             if attempt == 2:
#                 break
#             time.sleep(2 ** attempt)

#     # Fallback — use reason as explanation
#     logger.error("All simplification attempts failed — using fallback")
#     for r in risks_copy:
#         if "simple_explanation" not in r:
#             r["simple_explanation"] = r.get("reason", "Review this clause carefully.")

#     return risks_copy
from langchain_groq import ChatGroq
from dotenv import load_dotenv
import os
import json
import re
import time
import copy
from utils.logger import get_logger

logger = get_logger("simplifier")

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# ── Lazy init ─────────────────────────────────────────────────
_llm = None

def _get_llm():
    global _llm
    if _llm is None:
        _llm = ChatGroq(
            api_key=GROQ_API_KEY,
            model_name="llama-3.3-70b-versatile",
            temperature=0.2,
            max_tokens=3000,
            timeout=60
        )
    return _llm


def simplify_risks(risks: list, doc_type: str) -> list:
    """
    Batch simplify all clauses in ONE API call.
    Uses deep copy — never mutates original list.
    """
    if not risks:
        return []

    risks_copy = copy.deepcopy(risks)

    clauses_text = ""
    for i, r in enumerate(risks_copy):
        clauses_text += f"""
Clause {i+1}:
Type: {r.get('clause_type')}
Risk Level: {r.get('risk_level')}
Original: {r.get('original_text', '')[:200]}
Reason: {r.get('reason')}
Negotiation Tip: {r.get('negotiation_tip', '')}
---"""

    prompt = f"""You are a legal expert explaining {doc_type.replace('_', ' ').title()} clauses to a non-lawyer.

For each clause below, write a plain English explanation (2-3 sentences max):
1. What it actually means in simple words
2. How it can specifically affect the person signing
3. What they should do about it

Return a JSON array with exactly {len(risks_copy)} objects:
[
  {{
    "index": 0,
    "simple_explanation": "your explanation here"
  }}
]

Rules:
- Return ONLY valid JSON array
- index must match clause number minus 1 (0-based)
- Keep language simple — no legal jargon
- For SAFE clauses: confirm why it is fair and standard
- No markdown, no text outside the array

Clauses:
{clauses_text}
"""

    for attempt in range(3):
        try:
            response = _get_llm().invoke(prompt)
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

                # Fill any missing explanations
                for r in risks_copy:
                    if "simple_explanation" not in r:
                        r["simple_explanation"] = r.get("reason", "Review this clause carefully.")

                logger.info(f"Simplified {len(risks_copy)} clauses")
                return risks_copy

        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"JSON parse error on attempt {attempt + 1}: {e}")
            if attempt == 2:
                break
            time.sleep(2 ** attempt)
        except Exception as e:
            logger.warning(f"Unexpected error on attempt {attempt + 1}: {e}")
            if attempt == 2:
                break
            time.sleep(2 ** attempt)

    # Fallback — use reason as explanation
    logger.error("All simplification attempts failed — using fallback")
    for r in risks_copy:
        if "simple_explanation" not in r:
            r["simple_explanation"] = r.get("reason", "Review this clause carefully.")

    return risks_copy