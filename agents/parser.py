# """
# PDF parsing wrapper.
# Currently delegates to utils.pdf_reader.
# Reserved for future enhancements (e.g., DOCX support, multi-format).
# """

# from utils.pdf_reader import extract_text_from_pdf
# from utils.logger import get_logger

# logger = get_logger("parser")


# def parse_document(uploaded_file) -> tuple:
#     """
#     Parse uploaded PDF file into text.
#     Returns: (text, error, file_hash) — always a 3-tuple.
#     """
#     logger.info(f"Parsing document: {getattr(uploaded_file, 'name', 'unknown')}")
#     text, error, file_hash = extract_text_from_pdf(uploaded_file)

#     if error:
#         logger.warning(f"Parse failed: {error}")
#     else:
#         logger.info(f"Parse success | chars={len(text)} | hash={file_hash[:12]}")

#     return text, error, file_hash
"""
PDF parsing wrapper.
Currently delegates to utils.pdf_reader.
Reserved for future enhancements (e.g., DOCX support, multi-format).
"""

from utils.pdf_reader import extract_text_from_pdf
from utils.logger import get_logger

logger = get_logger("parser")


def parse_document(uploaded_file) -> tuple:
    """
    Parse uploaded PDF file into text.
    Returns: (text, error, file_hash, warning) — always a 4-tuple.
    warning is None on clean extraction, or a human-readable message
    if OCR was used but couldn't finish all pages within the time budget.
    """
    logger.info(f"Parsing document: {getattr(uploaded_file, 'name', 'unknown')}")
    text, error, file_hash, warning = extract_text_from_pdf(uploaded_file)  # ✅ 4-tuple

    if error:
        logger.warning(f"Parse failed: {error}")
    else:
        logger.info(f"Parse success | chars={len(text)} | hash={file_hash[:12]}")
        if warning:
            logger.warning(f"Parse warning: {warning}")

    return text, error, file_hash, warning  