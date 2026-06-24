# import PyPDF2
# import io
# import hashlib
# import os
# import shutil
# from utils.logger import get_logger

# logger = get_logger("pdf_reader")

# # ── OCR: optional, graceful degradation ──────────────────────
# OCR_AVAILABLE = False
# try:
#     import pytesseract
#     from pdf2image import convert_from_bytes
#     from PIL import Image

#     # Auto-detect tesseract — no hardcoded paths
#     tesseract_path = shutil.which("tesseract")
#     if tesseract_path:
#         pytesseract.pytesseract.tesseract_cmd = tesseract_path
#     else:
#         # Fallback to common Windows install locations
#         _win_paths = [
#             r'C:\Program Files\Tesseract-OCR\tesseract.exe',
#             r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
#         ]
#         for _path in _win_paths:
#             if os.path.exists(_path):
#                 pytesseract.pytesseract.tesseract_cmd = _path
#                 break

#     OCR_AVAILABLE = True
#     logger.info("OCR available")
# except ImportError:
#     logger.info("OCR not available — text-based PDF only")


# # ── Poppler path: cross-platform ─────────────────────────────
# def _get_poppler_path() -> str | None:
#     """Return poppler path if on Windows and found, else None."""
#     candidates = [
#         r'C:\poppler\poppler-26.02.0\Library\bin',
#         r'C:\poppler\Library\bin',
#         r'C:\Program Files\poppler\bin',
#     ]
#     for p in candidates:
#         if os.path.exists(p):
#             return p
#     return None  # Linux/Mac — pdf2image finds it automatically


# def get_file_hash(file_bytes: bytes) -> str:
#     """SHA-256 hash for cache keying."""
#     return hashlib.sha256(file_bytes).hexdigest()


# def extract_text_with_ocr(file_bytes: bytes) -> str:
#     """Scanned PDF → OCR → text. Returns empty string on failure."""
#     if not OCR_AVAILABLE:
#         return ""
#     try:
#         poppler_path = _get_poppler_path()
#         kwargs = {"dpi": 300}
#         if poppler_path:
#             kwargs["poppler_path"] = poppler_path

#         images = convert_from_bytes(file_bytes, **kwargs)
#         text = ""
#         for image in images:
#             page_text = pytesseract.image_to_string(image, lang='eng')
#             if page_text:
#                 text += page_text + "\n"
#         logger.info(f"OCR extracted {len(text)} chars")
#         return text.strip()
#     except Exception as e:
#         logger.warning(f"OCR failed: {e}")
#         return ""


# def extract_text_from_pdf(uploaded_file) -> tuple:
#     """
#     Extract text from uploaded PDF.
#     Returns: (text, error, file_hash)
#     Always a 3-tuple — never raises.
#     """
#     try:
#         file_bytes = uploaded_file.read()

#         # ── Validations ──────────────────────────────────────
#         if len(file_bytes) > 10 * 1024 * 1024:
#             return None, "File too large. Maximum size is 10MB.", None

#         if not file_bytes.startswith(b'%PDF'):
#             return None, "Invalid file. Please upload a valid PDF.", None

#         pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))

#         if pdf_reader.is_encrypted:
#             return None, "Password-protected PDF. Please remove password and re-upload.", None

#         if len(pdf_reader.pages) > 50:
#             return None, "Document too large. Maximum 50 pages supported.", None

#         # ── Text extraction ───────────────────────────────────
#         text_parts = []
#         for page in pdf_reader.pages:
#             page_text = page.extract_text()
#             if page_text:
#                 text_parts.append(page_text)

#         text = "\n".join(text_parts).strip()
#         logger.info(f"Direct extraction: {len(text)} chars from {len(pdf_reader.pages)} pages")

#         # ── OCR fallback for scanned PDFs ─────────────────────
#         if len(text) < 100:
#             logger.info("Text too short — attempting OCR")
#             text = extract_text_with_ocr(file_bytes)

#         if len(text) < 100:
#             return None, "Could not extract text. Document may be image-only or corrupted.", None

#         file_hash = get_file_hash(file_bytes)
#         return text, None, file_hash

#     except PyPDF2.errors.PdfReadError:
#         return None, "Corrupted PDF file. Please try a different file.", None
#     except Exception as e:
#         logger.error(f"Unexpected error in pdf_reader: {e}")
#         return None, f"Unexpected error: {str(e)}", None
# import PyPDF2
# import io
# import hashlib
# import os
# import shutil
# import time
# import concurrent.futures
# from utils.logger import get_logger

# logger = get_logger("pdf_reader")

# # ── OCR: optional, graceful degradation ──────────────────────
# OCR_AVAILABLE = False
# try:
#     import pytesseract
#     from pdf2image import convert_from_bytes
#     from PIL import Image

#     # Auto-detect tesseract — no hardcoded paths
#     tesseract_path = shutil.which("tesseract")
#     if tesseract_path:
#         pytesseract.pytesseract.tesseract_cmd = tesseract_path
#     else:
#         # Fallback to common Windows install locations
#         _win_paths = [
#             r'C:\Program Files\Tesseract-OCR\tesseract.exe',
#             r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
#         ]
#         for _path in _win_paths:
#             if os.path.exists(_path):
#                 pytesseract.pytesseract.tesseract_cmd = _path
#                 break

#     OCR_AVAILABLE = True
#     logger.info("OCR available")
# except ImportError:
#     logger.info("OCR not available — text-based PDF only")


# # ── OCR timing/concurrency knobs ───────────────────────────────
# # OCR is a pre-pipeline step (runs before the LLM analysis pipeline even
# # starts), so its time is ADDED on top of the pipeline's own ~36s budget.
# # Pages are processed in a thread pool (pytesseract's actual OCR work runs
# # in a tesseract subprocess/C call, so it releases the GIL — real
# # parallelism, not just async-flavored concurrency), bounded by a single
# # hard deadline. If the deadline hits, whatever pages finished are used;
# # the unfinished ones are dropped from the result and the caller is told
# # the extraction was INCOMPLETE so it can warn the user — never silently
# # presented as a full read of the document.
# #
# # Caveat: concurrent.futures cannot forcibly kill an already-running
# # thread. "Cancelling" a page whose OCR call is already in flight only
# # stops us from waiting on it / using its result — the underlying
# # tesseract call may keep running in the background until it finishes on
# # its own. This is a known Python limitation, not a bug in this code.
# OCR_MAX_WORKERS = 4
# OCR_OVERALL_DEADLINE_SECONDS = 15.0


# # ── Poppler path: cross-platform ─────────────────────────────
# def _get_poppler_path() -> str | None:
#     """Return poppler path if on Windows and found, else None."""
#     candidates = [
#         r'C:\poppler\poppler-26.02.0\Library\bin',
#         r'C:\poppler\Library\bin',
#         r'C:\Program Files\poppler\bin',
#     ]
#     for p in candidates:
#         if os.path.exists(p):
#             return p
#     return None  # Linux/Mac — pdf2image finds it automatically


# def get_file_hash(file_bytes: bytes) -> str:
#     """SHA-256 hash for cache keying."""
#     return hashlib.sha256(file_bytes).hexdigest()


# def _ocr_single_page(image, lang: str = 'eng') -> str:
#     """Run OCR on one rendered page image. Never raises — empty string on failure."""
#     try:
#         return pytesseract.image_to_string(image, lang=lang) or ""
#     except Exception as e:
#         logger.warning(f"OCR failed on a page: {e}")
#         return ""


# def extract_text_with_ocr(file_bytes: bytes) -> tuple[str, bool]:
#     """
#     Scanned PDF → OCR → text.

#     Returns (text, complete):
#       - text: whatever was successfully OCR'd (partial if the deadline hit)
#       - complete: False if OCR_OVERALL_DEADLINE_SECONDS was hit before every
#         page finished — the caller MUST surface this to the user rather
#         than presenting partial text as a full extraction.

#     Never raises. Returns ("", True) if OCR isn't available or page
#     rendering itself fails (nothing to be "incomplete" about in that case).
#     """
#     if not OCR_AVAILABLE:
#         return "", True

#     start = time.monotonic()

#     try:
#         poppler_path = _get_poppler_path()
#         kwargs = {"dpi": 300}
#         if poppler_path:
#             kwargs["poppler_path"] = poppler_path
#         images = convert_from_bytes(file_bytes, **kwargs)
#     except Exception as e:
#         logger.warning(f"OCR page rendering failed: {e}")
#         return "", True

#     if not images:
#         return "", True

#     page_texts: list[str | None] = [None] * len(images)

#     with concurrent.futures.ThreadPoolExecutor(max_workers=OCR_MAX_WORKERS) as executor:
#         future_to_idx = {
#             executor.submit(_ocr_single_page, img): idx
#             for idx, img in enumerate(images)
#         }

#         remaining = OCR_OVERALL_DEADLINE_SECONDS - (time.monotonic() - start)
#         done, pending = concurrent.futures.wait(
#             future_to_idx.keys(), timeout=max(0.0, remaining)
#         )

#         for fut in done:
#             idx = future_to_idx[fut]
#             try:
#                 page_texts[idx] = fut.result()
#             except Exception as e:
#                 logger.warning(f"OCR page {idx + 1} raised: {e}")
#                 page_texts[idx] = ""

#         complete = not pending
#         if pending:
#             skipped_pages = sorted(future_to_idx[f] + 1 for f in pending)
#             logger.error(
#                 f"OCR deadline ({OCR_OVERALL_DEADLINE_SECONDS}s) hit — "
#                 f"{len(pending)}/{len(images)} page(s) not OCR'd in time "
#                 f"(pages {skipped_pages}). Proceeding with partial text; "
#                 f"those pages' content will be missing from this report."
#             )
#             for fut in pending:
#                 fut.cancel()  # best-effort only — see module note above

#     text = "\n".join(t for t in page_texts if t).strip()
#     elapsed = time.monotonic() - start
#     pages_done = sum(1 for t in page_texts if t)
#     logger.info(
#         f"OCR extracted {len(text)} chars from {pages_done}/{len(images)} "
#         f"page(s) in {elapsed:.1f}s (deadline={OCR_OVERALL_DEADLINE_SECONDS}s, "
#         f"complete={complete})"
#     )
#     return text, complete


# def extract_text_from_pdf(uploaded_file) -> tuple:
#     """
#     Extract text from uploaded PDF.
#     Returns: (text, error, file_hash, warning)
#     Always a 4-tuple — never raises.

#     warning is None on a clean extraction. It is set to a human-readable
#     message if OCR was used but couldn't finish all pages within the time
#     budget — the caller should show this to the user rather than silently
#     treating the result as a complete read of the document.

#     NOTE: this is a 4-tuple, one more than before. Any caller doing
#     `text, error, file_hash = extract_text_from_pdf(...)` needs to be
#     updated to unpack 4 values.
#     """
#     try:
#         file_bytes = uploaded_file.read()

#         # ── Validations ──────────────────────────────────────
#         if len(file_bytes) > 10 * 1024 * 1024:
#             return None, "File too large. Maximum size is 10MB.", None, None

#         if not file_bytes.startswith(b'%PDF'):
#             return None, "Invalid file. Please upload a valid PDF.", None, None

#         pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))

#         if pdf_reader.is_encrypted:
#             return None, "Password-protected PDF. Please remove password and re-upload.", None, None

#         if len(pdf_reader.pages) > 50:
#             return None, "Document too large. Maximum 50 pages supported.", None, None

#         # ── Text extraction ───────────────────────────────────
#         text_parts = []
#         for page in pdf_reader.pages:
#             page_text = page.extract_text()
#             if page_text:
#                 text_parts.append(page_text)

#         text = "\n".join(text_parts).strip()
#         logger.info(f"Direct extraction: {len(text)} chars from {len(pdf_reader.pages)} pages")

#         # ── OCR fallback for scanned PDFs ─────────────────────
#         warning = None
#         if len(text) < 100:
#             logger.info("Text too short — attempting OCR")
#             text, ocr_complete = extract_text_with_ocr(file_bytes)
#             if not ocr_complete:
#                 warning = (
#                     "This appears to be a scanned document. Some pages could not "
#                     "be read within the time budget, so the analysis below may be "
#                     "based on partial text — please review the original document "
#                     "for completeness."
#                 )

#         if len(text) < 100:
#             return None, "Could not extract text. Document may be image-only or corrupted.", None, None

#         file_hash = get_file_hash(file_bytes)
#         return text, None, file_hash, warning

#     except PyPDF2.errors.PdfReadError:
#         return None, "Corrupted PDF file. Please try a different file.", None, None
#     except Exception as e:
#         logger.error(f"Unexpected error in pdf_reader: {e}")
#         return None, f"Unexpected error: {str(e)}", None, None
"""
PDF text extractor with OCR fallback for scanned documents.

FIX HISTORY:
1) (original) PyPDF2-based extraction with OCR fallback, deadline-bounded
   parallel page processing, and graceful degradation.
2) (2026-06-22, fix #1) [CURRENT]
   - PyPDF2 → pypdf: PyPDF2 was deprecated in 2023 and is no longer
     maintained. pypdf is the direct successor with identical API —
     drop-in replacement. Keeps PyPDF2 as fallback for envs that haven't
     updated yet.
   - Ligature artifact handling added to _clean_extracted_text: legal
     documents with fancy fonts produce Unicode ligatures (ﬁ→fi, ﬀ→ff,
     ﬃ→ffi etc.) that break keyword matching downstream. Fixed with a
     simple substitution table.
   - PDF header check relaxed: valid PDFs occasionally have whitespace or
     a BOM before %PDF — was incorrectly rejecting these as invalid.
   - Partial OCR warning now includes which page numbers were missed so
     the user knows exactly what to review manually.
   - Minor: file size limit error message now shows actual file size.
"""

import io
import hashlib
import os
import shutil
import time
import re
import concurrent.futures
from utils.logger import get_logger

logger = get_logger("pdf_reader")

# ── PDF library: prefer pypdf (maintained), fall back to PyPDF2 (deprecated) ─
try:
    import pypdf as pdf_lib
    _PDF_LIB = "pypdf"
except ImportError:
    try:
        import PyPDF2 as pdf_lib
        _PDF_LIB = "PyPDF2"
        logger.warning(
            "PyPDF2 is deprecated — install pypdf for better compatibility: "
            "pip install pypdf"
        )
    except ImportError:
        raise ImportError(
            "No PDF library found. Install pypdf: pip install pypdf"
        )

# ── OCR: optional, graceful degradation ──────────────────────────────────────
OCR_AVAILABLE = False
try:
    import pytesseract
    from pdf2image import convert_from_bytes
    from PIL import Image

    tesseract_path = shutil.which("tesseract")
    if tesseract_path:
        pytesseract.pytesseract.tesseract_cmd = tesseract_path
    else:
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

OCR_MAX_WORKERS              = 4
OCR_OVERALL_DEADLINE_SECONDS = 15.0

# ── Unicode ligature substitution table ──────────────────────────────────────
# Legal PDFs with fancy fonts produce these; they break keyword matching
_LIGATURES = {
    '\ufb00': 'ff',   # ﬀ
    '\ufb01': 'fi',   # ﬁ
    '\ufb02': 'fl',   # ﬂ
    '\ufb03': 'ffi',  # ﬃ
    '\ufb04': 'ffl',  # ﬄ
    '\ufb05': 'st',   # ﬅ
    '\ufb06': 'st',   # ﬆ
    '\u2019': "'",    # right single quote → apostrophe
    '\u2018': "'",    # left single quote
    '\u201c': '"',    # left double quote
    '\u201d': '"',    # right double quote
    '\u2013': '-',    # en dash
    '\u2014': '--',   # em dash
    '\u00a0': ' ',    # non-breaking space
}


def _get_poppler_path() -> str | None:
    candidates = [
        r'C:\poppler\poppler-26.02.0\Library\bin',
        r'C:\poppler\Library\bin',
        r'C:\Program Files\poppler\bin',
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return None


def get_file_hash(file_bytes: bytes) -> str:
    return hashlib.sha256(file_bytes).hexdigest()


def _clean_extracted_text(text: str) -> str:
    """
    Fix PDF extraction artifacts — only fix genuinely broken patterns,
    not normal word spacing.
    """
    # Fix Unicode ligatures and smart quotes
    for ligature, replacement in _LIGATURES.items():
        text = text.replace(ligature, replacement)

    # Fix hyphenation across lines: "competi-\ntion" → "competition"
    text = re.sub(r'-\n([a-z])', r'\1', text)

    # Fix multiple consecutive spaces → single space
    text = re.sub(r' {2,}', ' ', text)

    # Fix excessive newlines → max 2
    text = re.sub(r'\n{3,}', '\n\n', text)

    return text.strip()


def _ocr_single_page(image, lang: str = 'eng') -> str:
    try:
        return pytesseract.image_to_string(image, lang=lang) or ""
    except Exception as e:
        logger.warning(f"OCR failed on a page: {e}")
        return ""


def extract_text_with_ocr(file_bytes: bytes) -> tuple[str, bool, list[int]]:
    """
    Returns (text, is_complete, skipped_page_numbers).
    skipped_page_numbers is 1-indexed list of pages that timed out.
    """
    if not OCR_AVAILABLE:
        return "", True, []

    start = time.monotonic()

    try:
        poppler_path = _get_poppler_path()
        kwargs = {"dpi": 300}
        if poppler_path:
            kwargs["poppler_path"] = poppler_path
        images = convert_from_bytes(file_bytes, **kwargs)
    except Exception as e:
        logger.warning(f"OCR page rendering failed: {e}")
        return "", True, []

    if not images:
        return "", True, []

    page_texts: list[str | None] = [None] * len(images)
    skipped_pages: list[int]     = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=OCR_MAX_WORKERS) as executor:
        future_to_idx = {
            executor.submit(_ocr_single_page, img): idx
            for idx, img in enumerate(images)
        }

        remaining = OCR_OVERALL_DEADLINE_SECONDS - (time.monotonic() - start)
        done, pending = concurrent.futures.wait(
            future_to_idx.keys(), timeout=max(0.0, remaining)
        )

        for fut in done:
            idx = future_to_idx[fut]
            try:
                page_texts[idx] = fut.result()
            except Exception as e:
                logger.warning(f"OCR page {idx + 1} raised: {e}")
                page_texts[idx] = ""

        complete = not pending
        if pending:
            skipped_pages = sorted(future_to_idx[f] + 1 for f in pending)
            logger.error(
                f"OCR deadline ({OCR_OVERALL_DEADLINE_SECONDS}s) hit — "
                f"{len(pending)}/{len(images)} page(s) not OCR'd: "
                f"pages {skipped_pages}"
            )
            for fut in pending:
                fut.cancel()

    text      = "\n".join(t for t in page_texts if t).strip()
    elapsed   = time.monotonic() - start
    pages_done = sum(1 for t in page_texts if t)
    logger.info(
        f"OCR extracted {len(text)} chars from {pages_done}/{len(images)} "
        f"page(s) in {elapsed:.1f}s (complete={complete})"
    )
    return text, complete, skipped_pages


def extract_text_from_pdf(uploaded_file) -> tuple:
    """
    Extract text from uploaded PDF.
    Returns: (text, error, file_hash, warning) — always a 4-tuple.
    """
    try:
        file_bytes = uploaded_file.read()
        file_size_mb = len(file_bytes) / (1024 * 1024)

        if len(file_bytes) > 10 * 1024 * 1024:
            return (
                None,
                f"File too large ({file_size_mb:.1f} MB). Maximum size is 10 MB.",
                None, None,
            )

        # Relaxed header check: some valid PDFs have whitespace/BOM before %PDF
        if b'%PDF' not in file_bytes[:1024]:
            return None, "Invalid file. Please upload a valid PDF.", None, None

        pdf_reader = pdf_lib.PdfReader(io.BytesIO(file_bytes))

        if pdf_reader.is_encrypted:
            return (
                None,
                "Password-protected PDF. Please remove the password and re-upload.",
                None, None,
            )

        if len(pdf_reader.pages) > 50:
            return (
                None,
                f"Document too large ({len(pdf_reader.pages)} pages). "
                f"Maximum 50 pages supported.",
                None, None,
            )

        # ── Direct text extraction ────────────────────────────────────────────
        text_parts = []
        for page in pdf_reader.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)

        text = "\n".join(text_parts).strip()
        text = _clean_extracted_text(text)
        logger.info(
            f"Direct extraction: {len(text)} chars from {len(pdf_reader.pages)} pages"
        )

        # ── OCR fallback for scanned PDFs ─────────────────────────────────────
        warning = None
        if len(text) < 100:
            logger.info("Text too short — attempting OCR")
            text, ocr_complete, skipped_pages = extract_text_with_ocr(file_bytes)

            if not ocr_complete and skipped_pages:
                warning = (
                    f"This appears to be a scanned document. "
                    f"Page(s) {skipped_pages} could not be read within the time limit — "
                    f"the analysis below may be incomplete. "
                    f"Please review those pages in the original document manually."
                )
            elif not ocr_complete:
                warning = (
                    "This appears to be a scanned document. Some pages could not be "
                    "read within the time limit — the analysis below may be incomplete."
                )

            text = _clean_extracted_text(text)

        if len(text) < 100:
            return (
                None,
                "Could not extract readable text. The document may be image-only, "
                "corrupted, or in an unsupported format.",
                None, None,
            )

        file_hash = get_file_hash(file_bytes)
        return text, None, file_hash, warning

    except Exception as e:
        # Handle pdf errors generically across both pypdf and PyPDF2
        err_str = str(e).lower()
        if "pdf" in err_str and ("read" in err_str or "corrupt" in err_str or "invalid" in err_str):
            return None, "Corrupted or unreadable PDF. Please try a different file.", None, None
        logger.error(f"Unexpected error in pdf_reader: {type(e).__name__}: {e}")
        return None, f"Unexpected error reading PDF: {str(e)}", None, None