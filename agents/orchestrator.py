# from utils.llm import get_llm
# from utils.logger import get_logger

# logger = get_logger("orchestrator")

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
#     Detect document type using beginning + middle + end sampling.
#     Returns one of VALID_TYPES.
#     """
#     logger.info(f"Detecting document type | chars={len(text)}")

#     # Sample beginning + middle + end for robust detection
#     chunk_size = 1500
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
# - If it is a job offer or appointment letter, classify as OFFER_LETTER
# - If it is a formal employment agreement/contract, classify as EMPLOYMENT_CONTRACT
# - If uncertain between two types, pick the more specific one

# Document sample:
# {sample}
# """

#     llm = get_llm(max_tokens=50, temperature=0.0)

#     for attempt in range(3):
#         try:
#             response = llm.invoke(prompt)
#             result = response.content.strip().upper().replace(" ", "_")

#             # Match to valid type
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
#             import time
#             time.sleep(2 ** attempt)

#     return "OTHER"
"""
Orchestrator.
Detects document type and the document's own stated governing law/jurisdiction.

Both detections only need to read the document text — they're independent of
each other — so they run CONCURRENTLY instead of one after another, roughly
halving this step's latency. Bounded by ORCHESTRATOR_DEADLINE_SECONDS so this
step can never block the rest of the pipeline indefinitely.

FIX HISTORY:
1) (original) Concurrent detection with single deadline.
2) (2026-06-22, fix #1) [CURRENT]
   - DEADLINE MATH FIXED: _PER_CALL_TIMEOUT_SECONDS=4.0 × 2 attempts +
     0.5s backoff = 8.5s total possible per task, but
     ORCHESTRATOR_DEADLINE_SECONDS was only 6.0s — retries were being
     scheduled but the deadline killed them before they could run.
     FIX: deadline raised to 12s, per-call timeout reduced to 5s.
     Now: 5s attempt1 + 0.5s backoff + 5s attempt2 = 10.5s < 12s. ✓
   - Switched from get_llm() (70B) → get_fast_llm() (8B): both tasks
     return 1-5 words. Using the 70B model for "reply with ONE word" is
     wasteful and slower. 8B is more than sufficient.
   - Type detection sample reduced 4500 chars → 1200 chars (beginning only):
     document type is almost always determinable from the header/title/first
     paragraph. Sending middle+end was unnecessary prompt bloat.
   - Locale sample kept at beginning+end (governing law is usually at the
     end of a document), but reduced from 4000 chars → 2500 chars total.
   - mark_key_rate_limited integrated for rate-limit errors.
"""

import asyncio
import time
from utils.llm import get_fast_llm as get_llm, mark_key_rate_limited
from utils.logger import get_logger

logger = get_logger("orchestrator")

VALID_TYPES = [
    "OFFER_LETTER",
    "RENT_AGREEMENT",
    "INTERNSHIP_CONTRACT",
    "EMPLOYMENT_CONTRACT",
    "SERVICE_AGREEMENT",
    "NDA",
    "OTHER",
]

# Deadline math:
# _PER_CALL_TIMEOUT_SECONDS × _MAX_ATTEMPTS + _RETRY_BACKOFF × (_MAX_ATTEMPTS-1)
# = 5.0 × 2 + 0.5 × 1 = 10.5s < 12s deadline ✓
ORCHESTRATOR_DEADLINE_SECONDS = 12.0   # ↑ from 6.0
_PER_CALL_TIMEOUT_SECONDS     = 5.0    # ↓ from 4.0 (now actually fits)
_RETRY_BACKOFF_SECONDS        = 0.5
_MAX_ATTEMPTS                 = 2


def _build_type_prompt(text: str) -> str:
    # Type is almost always clear from the title/header/first paragraph.
    # 1200 chars is plenty — no need to send middle+end sections.
    sample = text[:1200].strip()

    return f"""You are a legal document classifier.

Classify this document into exactly ONE category:
OFFER_LETTER, RENT_AGREEMENT, INTERNSHIP_CONTRACT,
EMPLOYMENT_CONTRACT, SERVICE_AGREEMENT, NDA, OTHER

Rules:
- Reply with ONLY the category name — nothing else
- No explanation, no punctuation, no extra text
- If it is a job offer or appointment letter → OFFER_LETTER
- If it is a formal employment agreement/contract → EMPLOYMENT_CONTRACT
- If it is a leave and license or rental agreement → RENT_AGREEMENT
- If uncertain between two types, pick the more specific one

Document:
{sample}
"""


def _build_locale_prompt(text: str) -> str:
    # Governing law clauses appear at the END of most documents.
    # Send beginning (party details) + end (governing law section).
    beginning = text[:1000].strip()
    end       = text[-1500:].strip() if len(text) > 1500 else ""
    sample    = f"{beginning}\n...\n{end}".strip()

    return f"""Read this legal document excerpt and identify the governing law/jurisdiction
it is explicitly subject to (e.g. "California, USA", "Maharashtra, India", "United Kingdom").

Rules:
- Reply with ONLY the jurisdiction name
- If NO governing-law clause, jurisdiction clause, or state bar reference is
  explicitly mentioned, reply with exactly: UNKNOWN
- Do NOT guess from currency symbols, names, or tone — only explicit statements count
- No explanation, no extra punctuation

Document excerpt:
{sample}
"""


async def _detect_document_type_async(text: str) -> str:
    prompt = _build_type_prompt(text)
    llm    = get_llm(max_tokens=20, temperature=0.0)

    for attempt in range(_MAX_ATTEMPTS):
        try:
            response = await asyncio.wait_for(
                llm.ainvoke(prompt), timeout=_PER_CALL_TIMEOUT_SECONDS
            )
            result = response.content.strip().upper().replace(" ", "_")
            for doc_type in VALID_TYPES:
                if doc_type in result:
                    return doc_type
            logger.info("Doc-type: no exact match — returning OTHER")
            return "OTHER"
        except Exception as e:
            err = str(e)
            if "rate_limit" in err.lower() or "rate limit" in err.lower():
                try:
                    mark_key_rate_limited(llm.api_key)
                except Exception:
                    pass
            logger.warning(f"Doc-type detection attempt {attempt + 1} failed: {e}")
            if attempt < _MAX_ATTEMPTS - 1:
                await asyncio.sleep(_RETRY_BACKOFF_SECONDS)

    logger.error("Doc-type detection failed all attempts — defaulting to OTHER")
    return "OTHER"


async def _detect_locale_async(text: str) -> str | None:
    prompt = _build_locale_prompt(text)
    llm    = get_llm(max_tokens=20, temperature=0.0)

    for attempt in range(_MAX_ATTEMPTS):
        try:
            response = await asyncio.wait_for(
                llm.ainvoke(prompt), timeout=_PER_CALL_TIMEOUT_SECONDS
            )
            result = response.content.strip()
            if not result or "UNKNOWN" in result.upper():
                logger.info("No explicit jurisdiction found — staying locale-neutral")
                return None
            return result
        except Exception as e:
            err = str(e)
            if "rate_limit" in err.lower() or "rate limit" in err.lower():
                try:
                    mark_key_rate_limited(llm.api_key)
                except Exception:
                    pass
            logger.warning(f"Locale detection attempt {attempt + 1} failed: {e}")
            if attempt < _MAX_ATTEMPTS - 1:
                await asyncio.sleep(_RETRY_BACKOFF_SECONDS)

    logger.error("Locale detection failed all attempts — staying locale-neutral")
    return None


async def _detect_type_and_locale_async(text: str) -> tuple[str, str | None]:
    """Fire both detections concurrently; bound the pair by a single deadline."""
    type_task   = asyncio.ensure_future(_detect_document_type_async(text))
    locale_task = asyncio.ensure_future(_detect_locale_async(text))

    done, pending = await asyncio.wait(
        [type_task, locale_task], timeout=ORCHESTRATOR_DEADLINE_SECONDS
    )

    if pending:
        for t in pending:
            t.cancel()
        await asyncio.gather(*pending, return_exceptions=True)

    if type_task in pending:
        logger.error(
            f"Doc-type detection did not finish within "
            f"{ORCHESTRATOR_DEADLINE_SECONDS}s — defaulting to OTHER"
        )
        doc_type = "OTHER"
    else:
        try:
            doc_type = type_task.result()
        except Exception as e:
            logger.error(f"Doc-type detection raised: {e}")
            doc_type = "OTHER"

    if locale_task in pending:
        logger.error(
            f"Locale detection did not finish within "
            f"{ORCHESTRATOR_DEADLINE_SECONDS}s — staying locale-neutral"
        )
        locale_hint = None
    else:
        try:
            locale_hint = locale_task.result()
        except Exception as e:
            logger.error(f"Locale detection raised: {e}")
            locale_hint = None

    return doc_type, locale_hint


def detect_document_type(text: str) -> str:
    """Standalone sync entry point — kept for direct callers."""
    logger.info(f"Detecting document type | chars={len(text)}")
    return asyncio.run(_detect_document_type_async(text))


def detect_locale(text: str) -> str | None:
    """Standalone sync entry point — kept for direct callers."""
    return asyncio.run(_detect_locale_async(text))


def detect_type_and_locale(text: str) -> tuple[str, str | None]:
    """
    Run document-type and locale detection CONCURRENTLY and return both.
    This is the function the pipeline calls — roughly halves the wall-clock
    cost vs calling detect_document_type() + detect_locale() sequentially.
    """
    start = time.monotonic()
    logger.info(f"Detecting document type + locale | chars={len(text)}")
    doc_type, locale_hint = asyncio.run(_detect_type_and_locale_async(text))
    elapsed = time.monotonic() - start
    logger.info(f"Doc type: {doc_type} | Locale: {locale_hint} | took {elapsed:.1f}s")
    return doc_type, locale_hint