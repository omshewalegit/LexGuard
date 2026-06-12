# # from langchain_groq import ChatGroq
# # from dotenv import load_dotenv
# # import os
# # import json
# # import re
# # import time
# # from utils.logger import get_logger

# # logger = get_logger("risk_analyzer")

# # load_dotenv()

# # GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# # llm = ChatGroq(
# #     api_key=GROQ_API_KEY,
# #     model_name="llama-3.3-70b-versatile",
# #     temperature=0.1,
# #     max_tokens=3000,
# #     timeout=60
# # )

# # RISK_CHECKS = {
# #     "OFFER_LETTER": [
# #         "Notice period duration and penalties",
# #         "Intellectual property ownership including personal projects",
# #         "Salary revision terms and discretion",
# #         "Non-compete restrictions post employment",
# #         "Termination conditions and severance",
# #         "Relocation clauses",
# #         "Moonlighting or side project restrictions",
# #         "Bond period or training cost recovery",
# #         "Anti-disparagement clauses",
# #         "Variable pay conditions"
# #     ],
# #     "EMPLOYMENT_CONTRACT": [
# #         "Notice period and buyout terms",
# #         "IP and invention assignment",
# #         "Salary revision discretion",
# #         "Non-compete and non-solicitation",
# #         "Termination for cause definitions",
# #         "Garden leave provisions",
# #         "Indemnity clauses",
# #         "Jurisdiction for disputes",
# #         "Anti-disparagement",
# #         "Medical fitness termination"
# #     ],
# #     "RENT_AGREEMENT": [
# #         "Security deposit amount and refund conditions",
# #         "Notice period for vacating",
# #         "Rent escalation clause",
# #         "Maintenance responsibility",
# #         "Subletting restrictions",
# #         "Lock-in period penalties",
# #         "Utility payment terms",
# #         "Inspection rights"
# #     ],
# #     "INTERNSHIP_CONTRACT": [
# #         "IP ownership of work done",
# #         "Confidentiality scope",
# #         "Conversion to full-time terms",
# #         "Stipend payment conditions",
# #         "Notice period",
# #         "Non-disclosure duration"
# #     ]
# # }

# # DEFAULT_CHECKS = [
# #     "Termination conditions",
# #     "Notice period",
# #     "IP clause",
# #     "Non-compete",
# #     "Salary or payment terms",
# #     "Confidentiality scope"
# # ]


# # def analyze_risks(text: str, doc_type: str) -> list:
# #     """
# #     Analyze document for risky clauses.
# #     Returns list of risk objects with structured data.
# #     """
# #     logger.info(f"Analyzing risks | doc_type={doc_type} | chars={len(text)}")

# #     checks = RISK_CHECKS.get(doc_type, DEFAULT_CHECKS)
# #     checks_text = "\n".join(f"- {c}" for c in checks)

# #     prompt = f"""You are a senior legal analyst in India specializing in {doc_type} documents.

# # Analyze this document and identify ALL clauses that are risky or unfavorable for the employee/candidate/tenant.

# # Specifically check for:
# # {checks_text}

# # Return a JSON array. Each object must have EXACTLY these fields:
# # {{
# #   "clause_type": "string — e.g. Notice Period, IP Clause",
# #   "original_text": "string — exact sentence copied from document",
# #   "risk_level": "HIGH | MEDIUM | LOW | SAFE",
# #   "confidence": integer between 50 and 99,
# #   "reason": "string — why this is risky in simple terms",
# #   "negotiation_tip": "string — exactly what to say or ask to negotiate this clause"
# # }}

# # Rules:
# # - Return ONLY a valid JSON array
# # - No markdown, no text outside the array
# # - Include 2-3 SAFE clauses as well
# # - Minimum 4 items, maximum 10 items
# # - negotiation_tip must be specific and actionable, not generic

# # Document:
# # {text[:5000]}
# # """

# #     for attempt in range(3):
# #         try:
# #             response = llm.invoke(prompt)
# #             content = response.content.strip()

# #             # Robust JSON extraction
# #             json_match = re.search(r'\[.*\]', content, re.DOTALL)
# #             if json_match:
# #                 risks = json.loads(json_match.group())

# #                 # Validate structure
# #                 validated = []
# #                 for r in risks:
# #                     if all(k in r for k in ["clause_type", "risk_level", "confidence"]):
# #                         r.setdefault("original_text", "")
# #                         r.setdefault("reason", "")
# #                         r.setdefault("negotiation_tip", "Request clarification on this clause.")
# #                         r["confidence"] = max(50, min(99, int(r["confidence"])))
# #                         validated.append(r)

# #                 if validated:
# #                     logger.info(f"Risks found: {len(validated)} | attempt={attempt + 1}")
# #                     return validated
# #                 else:
# #                     return _fallback_response()

# #         except (json.JSONDecodeError, ValueError):
# #             logger.warning(f"JSON parse error on attempt {attempt + 1}")
# #             if attempt == 2:
# #                 return _fallback_response()
# #             time.sleep(2 ** attempt)
# #         except Exception as e:
# #             logger.warning(f"Unexpected error on attempt {attempt + 1}: {e}")
# #             if attempt == 2:
# #                 logger.error("All 3 attempts failed. Returning fallback response.")
# #                 return _fallback_response()
# #             time.sleep(2 ** attempt)

# #     return _fallback_response()


# # def _fallback_response() -> list:
# #     return [{
# #         "clause_type": "Analysis Failed",
# #         "original_text": "",
# #         "risk_level": "UNKNOWN",
# #         "confidence": 0,
# #         "reason": "Could not analyze document. Please try again.",
# #         "negotiation_tip": ""
# #     }]

# from langchain_groq import ChatGroq
# from dotenv import load_dotenv
# import os
# import json
# import re
# import time
# from utils.logger import get_logger

# logger = get_logger("risk_analyzer")

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
#             temperature=0.1,
#             max_tokens=3000,
#             timeout=60
#         )
#     return _llm


# RISK_CHECKS = {
#     "OFFER_LETTER": [
#         "Notice period duration and penalties",
#         "Intellectual property ownership including personal projects",
#         "Salary revision terms and discretion",
#         "Non-compete restrictions post employment",
#         "Termination conditions and severance",
#         "Relocation clauses",
#         "Moonlighting or side project restrictions",
#         "Bond period or training cost recovery",
#         "Anti-disparagement clauses",
#         "Variable pay conditions"
#     ],
#     "EMPLOYMENT_CONTRACT": [
#         "Notice period and buyout terms",
#         "IP and invention assignment",
#         "Salary revision discretion",
#         "Non-compete and non-solicitation",
#         "Termination for cause definitions",
#         "Garden leave provisions",
#         "Indemnity clauses",
#         "Jurisdiction for disputes",
#         "Anti-disparagement",
#         "Medical fitness termination"
#     ],
#     "RENT_AGREEMENT": [
#         "Security deposit amount and refund conditions",
#         "Notice period for vacating",
#         "Rent escalation clause",
#         "Maintenance responsibility",
#         "Subletting restrictions",
#         "Lock-in period penalties",
#         "Utility payment terms",
#         "Inspection rights of landlord"
#     ],
#     "INTERNSHIP_CONTRACT": [
#         "IP ownership of work done during internship",
#         "Confidentiality scope and duration",
#         "Conversion to full-time terms",
#         "Stipend payment conditions",
#         "Notice period",
#         "Non-disclosure duration after internship"
#     ],
#     "SERVICE_AGREEMENT": [
#         "Payment terms and delay penalties",
#         "Scope creep and change request handling",
#         "IP ownership of deliverables",
#         "Termination for convenience clause",
#         "Liability cap",
#         "Dispute resolution jurisdiction"
#     ],
#     "NDA": [
#         "Definition of confidential information — too broad?",
#         "Duration of confidentiality obligation",
#         "Residuals clause",
#         "Permitted disclosures",
#         "Return or destruction of information",
#         "Injunctive relief clause"
#     ]
# }

# DEFAULT_CHECKS = [
#     "Termination conditions",
#     "Notice period",
#     "IP clause",
#     "Non-compete",
#     "Payment or salary terms",
#     "Confidentiality scope",
#     "Liability and indemnity"
# ]

# # ── Chunk text smartly ────────────────────────────────────────
# def _prepare_text_sample(text: str, max_chars: int = 12000) -> str:
#     """
#     Use beginning + middle + end to cover full document.
#     Default 12000 chars covers ~6 pages — much better than 5000.
#     """
#     if len(text) <= max_chars:
#         return text

#     chunk = max_chars // 3
#     beginning = text[:chunk]
#     mid_start = len(text) // 2 - chunk // 2
#     middle = text[mid_start: mid_start + chunk]
#     end = text[-chunk:]
#     return f"{beginning}\n\n[...middle section...]\n\n{middle}\n\n[...end section...]\n\n{end}"


# def analyze_risks(text: str, doc_type: str) -> list:
#     """
#     Analyze document for risky clauses.
#     Returns list of risk objects with structured data.
#     """
#     logger.info(f"Analyzing risks | doc_type={doc_type} | chars={len(text)}")

#     checks = RISK_CHECKS.get(doc_type, DEFAULT_CHECKS)
#     checks_text = "\n".join(f"- {c}" for c in checks)
#     text_sample = _prepare_text_sample(text)

#     # Doc-type aware analyst persona
#     persona_map = {
#         "OFFER_LETTER": "employment lawyer specializing in Indian labor law",
#         "EMPLOYMENT_CONTRACT": "employment lawyer specializing in Indian labor law",
#         "RENT_AGREEMENT": "property lawyer specializing in Indian rental laws",
#         "INTERNSHIP_CONTRACT": "employment lawyer advising fresh graduates",
#         "SERVICE_AGREEMENT": "commercial contracts lawyer",
#         "NDA": "IP and confidentiality law specialist",
#         "OTHER": "senior legal analyst"
#     }
#     persona = persona_map.get(doc_type, "senior legal analyst")

#     prompt = f"""You are a {persona}.

# Analyze this document and identify ALL clauses that are risky or unfavorable for the signing party.

# Specifically check for:
# {checks_text}

# Return a JSON array. Each object must have EXACTLY these fields:
# {{
#   "clause_type": "string — e.g. Notice Period, IP Clause",
#   "original_text": "string — exact sentence copied from document (max 200 chars)",
#   "risk_level": "HIGH | MEDIUM | LOW | SAFE",
#   "confidence": integer between 50 and 99,
#   "reason": "string — why this is risky in simple terms",
#   "negotiation_tip": "string — exactly what to say or ask to negotiate this clause"
# }}

# Rules:
# - Return ONLY a valid JSON array, no markdown, no text outside the array
# - Include 2-3 SAFE clauses as well
# - Minimum 5 items, maximum 12 items
# - negotiation_tip must be specific and actionable, not generic
# - If a clause is missing from the document entirely, flag it as MEDIUM risk

# Document:
# {text_sample}
# """

#     for attempt in range(3):
#         try:
#             response = _get_llm().invoke(prompt)
#             content = response.content.strip()

#             json_match = re.search(r'\[.*\]', content, re.DOTALL)
#             if json_match:
#                 risks = json.loads(json_match.group())

#                 validated = []
#                 for r in risks:
#                     if all(k in r for k in ["clause_type", "risk_level", "confidence"]):
#                         r.setdefault("original_text", "")
#                         r.setdefault("reason", "")
#                         r.setdefault("negotiation_tip", "Request clarification or amendment on this clause.")
#                         r["confidence"] = max(50, min(99, int(r["confidence"])))
#                         validated.append(r)

#                 if validated:
#                     logger.info(f"Risks found: {len(validated)} | attempt={attempt + 1}")
#                     return validated

#             logger.warning(f"No valid JSON on attempt {attempt + 1}")
#             return _fallback_response()

#         except (json.JSONDecodeError, ValueError) as e:
#             logger.warning(f"JSON parse error on attempt {attempt + 1}: {e}")
#             if attempt == 2:
#                 return _fallback_response()
#             time.sleep(2 ** attempt)
#         except Exception as e:
#             logger.warning(f"Unexpected error on attempt {attempt + 1}: {e}")
#             if attempt == 2:
#                 logger.error("All 3 attempts failed. Returning fallback.")
#                 return _fallback_response()
#             time.sleep(2 ** attempt)

#     return _fallback_response()


# def _fallback_response() -> list:
#     return [{
#         "clause_type": "Analysis Failed",
#         "original_text": "",
#         "risk_level": "UNKNOWN",
#         "confidence": 0,
#         "reason": "Could not analyze document. Please try again.",
#         "negotiation_tip": ""
#     }]

from langchain_groq import ChatGroq
from dotenv import load_dotenv
import os
import json
import re
import time
from utils.logger import get_logger

logger = get_logger("risk_analyzer")

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
            temperature=0.1,
            max_tokens=3000,
            timeout=60
        )
    return _llm


RISK_CHECKS = {
    "OFFER_LETTER": [
        "Notice period duration and penalties",
        "Intellectual property ownership including personal projects",
        "Salary revision terms and discretion",
        "Non-compete restrictions post employment",
        "Termination conditions and severance",
        "Relocation clauses",
        "Moonlighting or side project restrictions",
        "Bond period or training cost recovery",
        "Anti-disparagement clauses",
        "Variable pay conditions"
    ],
    "EMPLOYMENT_CONTRACT": [
        "Notice period and buyout terms",
        "IP and invention assignment",
        "Salary revision discretion",
        "Non-compete and non-solicitation",
        "Termination for cause definitions",
        "Garden leave provisions",
        "Indemnity clauses",
        "Jurisdiction for disputes",
        "Anti-disparagement",
        "Medical fitness termination"
    ],
    "RENT_AGREEMENT": [
        "Security deposit amount and refund conditions",
        "Notice period for vacating",
        "Rent escalation clause",
        "Maintenance responsibility",
        "Subletting restrictions",
        "Lock-in period penalties",
        "Utility payment terms",
        "Inspection rights of landlord"
    ],
    "INTERNSHIP_CONTRACT": [
        "IP ownership of work done during internship",
        "Confidentiality scope and duration",
        "Conversion to full-time terms",
        "Stipend payment conditions",
        "Notice period",
        "Non-disclosure duration after internship"
    ],
    "SERVICE_AGREEMENT": [
        "Payment terms and delay penalties",
        "Scope creep and change request handling",
        "IP ownership of deliverables",
        "Termination for convenience clause",
        "Liability cap",
        "Dispute resolution jurisdiction"
    ],
    "NDA": [
        "Definition of confidential information — too broad?",
        "Duration of confidentiality obligation",
        "Residuals clause",
        "Permitted disclosures",
        "Return or destruction of information",
        "Injunctive relief clause"
    ]
}

DEFAULT_CHECKS = [
    "Termination conditions",
    "Notice period",
    "IP clause",
    "Non-compete",
    "Payment or salary terms",
    "Confidentiality scope",
    "Liability and indemnity"
]

# ── Chunk text smartly ────────────────────────────────────────
def _prepare_text_sample(text: str, max_chars: int = 12000) -> str:
    """
    Use beginning + middle + end to cover full document.
    Default 12000 chars covers ~6 pages — much better than 5000.
    """
    if len(text) <= max_chars:
        return text

    chunk = max_chars // 3
    beginning = text[:chunk]
    mid_start = len(text) // 2 - chunk // 2
    middle = text[mid_start: mid_start + chunk]
    end = text[-chunk:]
    return f"{beginning}\n\n[...middle section...]\n\n{middle}\n\n[...end section...]\n\n{end}"


def analyze_risks(text: str, doc_type: str) -> list:
    """
    Analyze document for risky clauses.
    Returns list of risk objects with structured data.
    """
    logger.info(f"Analyzing risks | doc_type={doc_type} | chars={len(text)}")

    checks = RISK_CHECKS.get(doc_type, DEFAULT_CHECKS)
    checks_text = "\n".join(f"- {c}" for c in checks)
    text_sample = _prepare_text_sample(text)

    # Doc-type aware analyst persona
    persona_map = {
        "OFFER_LETTER": "employment lawyer specializing in Indian labor law",
        "EMPLOYMENT_CONTRACT": "employment lawyer specializing in Indian labor law",
        "RENT_AGREEMENT": "property lawyer specializing in Indian rental laws",
        "INTERNSHIP_CONTRACT": "employment lawyer advising fresh graduates",
        "SERVICE_AGREEMENT": "commercial contracts lawyer",
        "NDA": "IP and confidentiality law specialist",
        "OTHER": "senior legal analyst"
    }
    persona = persona_map.get(doc_type, "senior legal analyst")

    prompt = f"""You are a {persona}.

Analyze this document and identify ALL clauses that are risky or unfavorable for the signing party.

Specifically check for:
{checks_text}

Return a JSON array. Each object must have EXACTLY these fields:
{{
  "clause_type": "string — e.g. Notice Period, IP Clause",
  "original_text": "string — exact sentence copied from document (max 200 chars)",
  "risk_level": "HIGH | MEDIUM | LOW | SAFE",
  "confidence": integer between 50 and 99,
  "reason": "string — why this is risky in simple terms",
  "negotiation_tip": "string — exactly what to say or ask to negotiate this clause"
}}

Rules:
- Return ONLY a valid JSON array, no markdown, no text outside the array
- Include 2-3 SAFE clauses as well
- Minimum 5 items, maximum 12 items
- negotiation_tip must be specific and actionable, not generic
- If a clause is missing from the document entirely, flag it as MEDIUM risk

Document:
{text_sample}
"""

    for attempt in range(3):
        try:
            response = _get_llm().invoke(prompt)
            content = response.content.strip()

            json_match = re.search(r'\[.*\]', content, re.DOTALL)
            if json_match:
                risks = json.loads(json_match.group())

                validated = []
                for r in risks:
                    if all(k in r for k in ["clause_type", "risk_level", "confidence"]):
                        r.setdefault("original_text", "")
                        r.setdefault("reason", "")
                        r.setdefault("negotiation_tip", "Request clarification or amendment on this clause.")
                        r["confidence"] = max(50, min(99, int(r["confidence"])))
                        validated.append(r)

                if validated:
                    logger.info(f"Risks found: {len(validated)} | attempt={attempt + 1}")
                    return validated

            logger.warning(f"No valid JSON on attempt {attempt + 1}")
            return _fallback_response()

        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"JSON parse error on attempt {attempt + 1}: {e}")
            if attempt == 2:
                return _fallback_response()
            time.sleep(2 ** attempt)
        except Exception as e:
            logger.warning(f"Unexpected error on attempt {attempt + 1}: {e}")
            if attempt == 2:
                logger.error("All 3 attempts failed. Returning fallback.")
                return _fallback_response()
            time.sleep(2 ** attempt)

    return _fallback_response()


def _fallback_response() -> list:
    return [{
        "clause_type": "Analysis Failed",
        "original_text": "",
        "risk_level": "UNKNOWN",
        "confidence": 0,
        "reason": "Could not analyze document. Please try again.",
        "negotiation_tip": ""
    }]