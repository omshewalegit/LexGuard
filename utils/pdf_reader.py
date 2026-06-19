import PyPDF2
import io
import hashlib
import os
import shutil
from utils.logger import get_logger

logger = get_logger("pdf_reader")

# ── OCR: optional, graceful degradation ──────────────────────
OCR_AVAILABLE = False
try:
    import pytesseract
    from pdf2image import convert_from_bytes
    from PIL import Image

    # Auto-detect tesseract — no hardcoded paths
    tesseract_path = shutil.which("tesseract")
    if tesseract_path:
        pytesseract.pytesseract.tesseract_cmd = tesseract_path
    else:
        # Fallback to common Windows install locations
        _win_paths = [
            r'C:\Program Files\Tesseract-OCR\tesseract.exe',
            r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
        ]
        for _path in _win_paths:
            if os.path.exists(_path):
                pytesseract.pytesseract.tesseract_cmd = _path
                break

    OCR_AVAILABLE = True
    logger.info("OCR available")
except ImportError:
    logger.info("OCR not available — text-based PDF only")


# ── Poppler path: cross-platform ─────────────────────────────
def _get_poppler_path() -> str | None:
    """Return poppler path if on Windows and found, else None."""
    candidates = [
        r'C:\poppler\poppler-26.02.0\Library\bin',
        r'C:\poppler\Library\bin',
        r'C:\Program Files\poppler\bin',
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return None  # Linux/Mac — pdf2image finds it automatically


def get_file_hash(file_bytes: bytes) -> str:
    """SHA-256 hash for cache keying."""
    return hashlib.sha256(file_bytes).hexdigest()


def extract_text_with_ocr(file_bytes: bytes) -> str:
    """Scanned PDF → OCR → text. Returns empty string on failure."""
    if not OCR_AVAILABLE:
        return ""
    try:
        poppler_path = _get_poppler_path()
        kwargs = {"dpi": 300}
        if poppler_path:
            kwargs["poppler_path"] = poppler_path

        images = convert_from_bytes(file_bytes, **kwargs)
        text = ""
        for image in images:
            page_text = pytesseract.image_to_string(image, lang='eng')
            if page_text:
                text += page_text + "\n"
        logger.info(f"OCR extracted {len(text)} chars")
        return text.strip()
    except Exception as e:
        logger.warning(f"OCR failed: {e}")
        return ""


def extract_text_from_pdf(uploaded_file) -> tuple:
    """
    Extract text from uploaded PDF.
    Returns: (text, error, file_hash)
    Always a 3-tuple — never raises.
    """
    try:
        file_bytes = uploaded_file.read()

        # ── Validations ──────────────────────────────────────
        if len(file_bytes) > 10 * 1024 * 1024:
            return None, "File too large. Maximum size is 10MB.", None

        if not file_bytes.startswith(b'%PDF'):
            return None, "Invalid file. Please upload a valid PDF.", None

        pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))

        if pdf_reader.is_encrypted:
            return None, "Password-protected PDF. Please remove password and re-upload.", None

        if len(pdf_reader.pages) > 50:
            return None, "Document too large. Maximum 50 pages supported.", None

        # ── Text extraction ───────────────────────────────────
        text_parts = []
        for page in pdf_reader.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)

        text = "\n".join(text_parts).strip()
        logger.info(f"Direct extraction: {len(text)} chars from {len(pdf_reader.pages)} pages")

        # ── OCR fallback for scanned PDFs ─────────────────────
        if len(text) < 100:
            logger.info("Text too short — attempting OCR")
            text = extract_text_with_ocr(file_bytes)

        if len(text) < 100:
            return None, "Could not extract text. Document may be image-only or corrupted.", None

        file_hash = get_file_hash(file_bytes)
        return text, None, file_hash

    except PyPDF2.errors.PdfReadError:
        return None, "Corrupted PDF file. Please try a different file.", None
    except Exception as e:
        logger.error(f"Unexpected error in pdf_reader: {e}")
        return None, f"Unexpected error: {str(e)}", None
