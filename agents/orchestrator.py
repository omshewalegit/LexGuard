# # from langchain_groq import ChatGroq
# # from dotenv import load_dotenv
# # import os
# # import time
# # from utils.logger import get_logger

# # logger = get_logger("orchestrator")

# # load_dotenv()

# # # Validate API key on import
# # GROQ_API_KEY = os.getenv("GROQ_API_KEY")
# # if not GROQ_API_KEY:
# #     raise EnvironmentError("GROQ_API_KEY not found in .env file")

# # llm = ChatGroq(
# #     api_key=GROQ_API_KEY,
# #     model_name="llama-3.3-70b-versatile",
# #     temperature=0.1,
# #     max_tokens=100,
# #     timeout=30
# # )

# # VALID_TYPES = [
# #     "OFFER_LETTER",
# #     "RENT_AGREEMENT",
# #     "INTERNSHIP_CONTRACT",
# #     "EMPLOYMENT_CONTRACT",
# #     "SERVICE_AGREEMENT",
# #     "NDA",
# #     "OTHER"
# # ]


# # def detect_document_type(text: str) -> str:
# #     """
# #     Detect document type with retry logic.
# #     Returns one of VALID_TYPES.
# #     """
# #     logger.info(f"Detecting document type | chars={len(text)}")

# #     prompt = f"""You are a legal document classifier.

# # Classify this document into exactly ONE category:
# # OFFER_LETTER, RENT_AGREEMENT, INTERNSHIP_CONTRACT, 
# # EMPLOYMENT_CONTRACT, SERVICE_AGREEMENT, NDA, OTHER

# # Rules:
# # - Reply with ONLY the category name
# # - No explanation, no punctuation, no extra text

# # Document (first 1500 chars):
# # {text[:1500]}
# # """

# #     for attempt in range(3):
# #         try:
# #             response = llm.invoke(prompt)
# #             result = response.content.strip().upper()

# #             # Match to valid type
# #             for doc_type in VALID_TYPES:
# #                 if doc_type in result:
# #                     logger.info(f"Document type detected: {doc_type}")
# #                     return doc_type

# #             logger.info(f"Document type detected: OTHER")
# #             return "OTHER"

# #         except Exception as e:
# #             logger.warning(f"Attempt {attempt + 1} failed: {e}")
# #             if attempt == 2:
# #                 logger.error("All 3 attempts failed. Returning OTHER.")
# #                 return "OTHER"
# #             time.sleep(2 ** attempt)  # Exponential backoff

# #     return "OTHER"

# from langchain_groq import ChatGroq
# from dotenv import load_dotenv
# import os
# import time
# from utils.logger import get_logger

# logger = get_logger("orchestrator")

# load_dotenv()

# GROQ_API_KEY = os.getenv("GROQ_API_KEY")
# if not GROQ_API_KEY:
#     raise EnvironmentError("GROQ_API_KEY not found in .env file")

# # ── Lazy init — created once on first use ─────────────────────
# _llm = None

# def _get_llm():
#     global _llm
#     if _llm is None:
#         _llm = ChatGroq(
#             api_key=GROQ_API_KEY,
#             model_name="llama-3.3-70b-versatile",
#             temperature=0.1,
#             max_tokens=100,
#             timeout=30
#         )
#     return _llm


# VALID_TYPES = [
#     "OFFER_LETTER",
#     "RENT_AGREEMENT",
#     "INTERNSHIP_CONTRACT",
#     "EMPLOYMENT_CONTRACT",
#     "SERVICE_AGREEMENT",
#     "NDA",
#     "OTHER"
# ]


# def detect_document_type(text: str) -> str:
#     """
#     Detect document type using first + middle + last section.
#     Returns one of VALID_TYPES.
#     """
#     logger.info(f"Detecting document type | chars={len(text)}")

#     # Use beginning + middle + end for better detection
#     # Avoids missing type hints that appear mid-document
#     chunk_size = 1000
#     beginning = text[:chunk_size]
#     middle_start = max(0, len(text) // 2 - chunk_size // 2)
#     middle = text[middle_start: middle_start + chunk_size]
#     end = text[-chunk_size:] if len(text) > chunk_size else ""

#     sample = f"{beginning}\n...\n{middle}\n...\n{end}".strip()

#     prompt = f"""You are a legal document classifier.

# Classify this document into exactly ONE category:
# OFFER_LETTER, RENT_AGREEMENT, INTERNSHIP_CONTRACT,
# EMPLOYMENT_CONTRACT, SERVICE_AGREEMENT, NDA, OTHER

# Rules:
# - Reply with ONLY the category name
# - No explanation, no punctuation, no extra text

# Document sample:
# {sample}
# """

#     for attempt in range(3):
#         try:
#             response = _get_llm().invoke(prompt)
#             result = response.content.strip().upper()

#             for doc_type in VALID_TYPES:
#                 if doc_type in result:
#                     logger.info(f"Document type detected: {doc_type}")
#                     return doc_type

#             logger.info("No exact match — returning OTHER")
#             return "OTHER"

#         except Exception as e:
#             logger.warning(f"Attempt {attempt + 1} failed: {e}")
#             if attempt == 2:
#                 logger.error("All 3 attempts failed. Returning OTHER.")
#                 return "OTHER"
#             time.sleep(2 ** attempt)

#     return "OTHER"


from langchain_groq import ChatGroq
from dotenv import load_dotenv
import os
import time
from utils.logger import get_logger

logger = get_logger("orchestrator")

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise EnvironmentError("GROQ_API_KEY not found in .env file")

# ── Lazy init — created once on first use ─────────────────────
_llm = None

def _get_llm():
    global _llm
    if _llm is None:
        _llm = ChatGroq(
            api_key=GROQ_API_KEY,
            model_name="llama-3.3-70b-versatile",
            temperature=0.1,
            max_tokens=100,
            timeout=30
        )
    return _llm


VALID_TYPES = [
    "OFFER_LETTER",
    "RENT_AGREEMENT",
    "INTERNSHIP_CONTRACT",
    "EMPLOYMENT_CONTRACT",
    "SERVICE_AGREEMENT",
    "NDA",
    "OTHER"
]


def detect_document_type(text: str) -> str:
    """
    Detect document type using first + middle + last section.
    Returns one of VALID_TYPES.
    """
    logger.info(f"Detecting document type | chars={len(text)}")

    # Use beginning + middle + end for better detection
    # Avoids missing type hints that appear mid-document
    chunk_size = 1000
    beginning = text[:chunk_size]
    middle_start = max(0, len(text) // 2 - chunk_size // 2)
    middle = text[middle_start: middle_start + chunk_size]
    end = text[-chunk_size:] if len(text) > chunk_size else ""

    sample = f"{beginning}\n...\n{middle}\n...\n{end}".strip()

    prompt = f"""You are a legal document classifier.

Classify this document into exactly ONE category:
OFFER_LETTER, RENT_AGREEMENT, INTERNSHIP_CONTRACT,
EMPLOYMENT_CONTRACT, SERVICE_AGREEMENT, NDA, OTHER

Rules:
- Reply with ONLY the category name
- No explanation, no punctuation, no extra text

Document sample:
{sample}
"""

    for attempt in range(3):
        try:
            response = _get_llm().invoke(prompt)
            result = response.content.strip().upper()

            for doc_type in VALID_TYPES:
                if doc_type in result:
                    logger.info(f"Document type detected: {doc_type}")
                    return doc_type

            logger.info("No exact match — returning OTHER")
            return "OTHER"

        except Exception as e:
            logger.warning(f"Attempt {attempt + 1} failed: {e}")
            if attempt == 2:
                logger.error("All 3 attempts failed. Returning OTHER.")
                return "OTHER"
            time.sleep(2 ** attempt)

    return "OTHER"