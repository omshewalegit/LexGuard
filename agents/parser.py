# # PDF parsing is handled by utils/pdf_reader.py
# # This module is reserved for future enhancements
# # like OCR support for scanned PDFs

# from utils.pdf_reader import extract_text_from_pdf

# def parse_document(uploaded_file):
#     text, error = extract_text_from_pdf(uploaded_file)
# #     return text, error
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
#         logger.info(f"Parse success | chars={len(text)} | hash={file_hash}")

#     return text, error, file_hash

from utils.pdf_reader import extract_text_from_pdf
from utils.logger import get_logger

logger = get_logger("parser")


def parse_document(uploaded_file) -> tuple:
    """
    Parse uploaded PDF file into text.
    Returns: (text, error, file_hash) — always a 3-tuple.
    """
    logger.info(f"Parsing document: {getattr(uploaded_file, 'name', 'unknown')}")
    text, error, file_hash = extract_text_from_pdf(uploaded_file)

    if error:
        logger.warning(f"Parse failed: {error}")
    else:
        logger.info(f"Parse success | chars={len(text)} | hash={file_hash}")

    return text, error, file_hash