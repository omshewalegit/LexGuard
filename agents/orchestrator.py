from utils.llm import get_llm
from utils.logger import get_logger

logger = get_logger("orchestrator")

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
    Detect document type using beginning + middle + end sampling.
    Returns one of VALID_TYPES.
    """
    logger.info(f"Detecting document type | chars={len(text)}")

    # Sample beginning + middle + end for robust detection
    chunk_size = 1500
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
- If it is a job offer or appointment letter, classify as OFFER_LETTER
- If it is a formal employment agreement/contract, classify as EMPLOYMENT_CONTRACT
- If uncertain between two types, pick the more specific one

Document sample:
{sample}
"""

    llm = get_llm(max_tokens=50, temperature=0.0)

    for attempt in range(3):
        try:
            response = llm.invoke(prompt)
            result = response.content.strip().upper().replace(" ", "_")

            # Match to valid type
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
            import time
            time.sleep(2 ** attempt)

    return "OTHER"
