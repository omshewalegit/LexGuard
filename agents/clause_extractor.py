# """
# Pass 1: Clause Extraction.
# Reads structural chunks and extracts every distinct legal clause,
# obligation, condition, restriction, or right from the document.
# This is a focused extraction task — no risk assessment yet.
# """

# import json
# import re
# import time
# from utils.llm import get_llm
# from utils.logger import get_logger

# logger = get_logger("clause_extractor")

# # ── Categories the LLM should tag clauses with ────────────────
# CLAUSE_CATEGORIES = [
#     "Termination", "Notice Period", "Non-Compete", "Non-Solicitation",
#     "IP / Invention Assignment", "Confidentiality / NDA",
#     "Indemnity / Liability", "Payment / Compensation",
#     "Probation", "Leave Policy", "Working Hours",
#     "Dispute Resolution / Jurisdiction", "Governing Law",
#     "Force Majeure", "Severability", "Amendment",
#     "Bond / Training Cost Recovery", "Relocation",
#     "Security Deposit", "Rent Escalation", "Maintenance",
#     "Subletting", "Lock-in Period", "Inspection Rights",
#     "Scope of Work", "Deliverables", "Auto-Renewal",
#     "Data Protection / Privacy", "Warranty / Guarantee",
#     "Anti-Disparagement", "Garden Leave", "Moonlighting",
#     "Other",
# ]


# def _build_extraction_prompt(chunks: list[dict], doc_type: str) -> str:
#     """Build the clause extraction prompt with all chunks."""
#     doc_label = doc_type.replace("_", " ").title()
#     categories_str = ", ".join(CLAUSE_CATEGORIES)

#     chunks_text = ""
#     for chunk in chunks:
#         chunks_text += f"\n--- SECTION {chunk['chunk_id'] + 1} ({chunk['section_hint']}) ---\n"
#         chunks_text += chunk["text"]
#         chunks_text += "\n"

#     return f"""You are a meticulous legal analyst extracting clauses from a {doc_label}.

# TASK: Read EVERY section of this document carefully. Extract EVERY distinct legal clause, obligation, condition, restriction, right, or provision. Do NOT skip anything — even standard clauses matter.

# For each clause found, provide:
# - "clause_type": A short descriptive name (e.g., "Non-Compete Restriction", "IP Assignment", "Notice Period")
# - "category": One of: {categories_str}
# - "original_text": The EXACT text from the document, copied VERBATIM (max 300 characters). If the clause is longer, copy the most critical sentence.
# - "section_ref": Which section number or heading this clause appears under

# CRITICAL RULES:
# 1. Extract ONLY clauses that ACTUALLY EXIST in the document text below
# 2. Do NOT invent, assume, or fabricate clauses that are not present
# 3. If a common clause type is MISSING from the document, do NOT include it
# 4. Copy original_text EXACTLY as written — do not paraphrase or rewrite
# 5. Extract at MINIMUM one clause per document section/paragraph that contains legal terms
# 6. Return a JSON array — no markdown fences, no commentary

# Think step by step: read each section, identify what legal obligations or conditions it creates, then extract.

# DOCUMENT ({doc_label}):
# {chunks_text}
# """


# def _verify_original_text(clause_text: str, source_text: str) -> tuple[bool, float]:
#     """
#     Verify that the extracted original_text actually exists in the source.
#     Returns (is_verified, match_quality) where match_quality is 0.0-1.0.
#     """
#     if not clause_text or clause_text.strip().lower() in (
#         "not applicable", "n/a", "none", "na", "-", ""
#     ):
#         return False, 0.0

#     clause_clean = clause_text.strip().lower()
#     source_clean = source_text.lower()

#     # Exact substring match
#     if clause_clean in source_clean:
#         return True, 1.0

#     # Check if most words from the clause appear in the source (fuzzy)
#     clause_words = set(re.findall(r'\b\w{4,}\b', clause_clean))
#     if not clause_words:
#         return False, 0.0

#     source_words = set(re.findall(r'\b\w{4,}\b', source_clean))
#     overlap = clause_words & source_words
#     match_ratio = len(overlap) / len(clause_words)

#     return match_ratio >= 0.6, match_ratio


# def _deduplicate_clauses(clauses: list[dict]) -> list[dict]:
#     """
#     Remove duplicate clauses that were extracted from overlapping chunks.
#     Uses clause_type + original_text similarity.
#     """
#     if len(clauses) <= 1:
#         return clauses

#     unique = []
#     seen_texts = []

#     for clause in clauses:
#         c_type = clause.get("clause_type", "").lower().strip()
#         c_text = clause.get("original_text", "").lower().strip()

#         is_duplicate = False
#         for seen_type, seen_text in seen_texts:
#             # Same clause type with similar text
#             if c_type == seen_type:
#                 # Check text overlap
#                 if c_text and seen_text:
#                     c_words = set(c_text.split())
#                     s_words = set(seen_text.split())
#                     if c_words and s_words:
#                         overlap = len(c_words & s_words) / min(len(c_words), len(s_words))
#                         if overlap > 0.5:
#                             is_duplicate = True
#                             break

#         if not is_duplicate:
#             unique.append(clause)
#             seen_texts.append((c_type, c_text))

#     removed = len(clauses) - len(unique)
#     if removed:
#         logger.info(f"Deduplication: {len(clauses)} → {len(unique)} (removed {removed} duplicates)")

#     return unique


# def extract_clauses(chunks: list[dict], doc_type: str, full_text: str) -> list[dict]:
#     """
#     Pass 1: Extract all clauses from document chunks.
#     Returns list of verified, deduplicated clause objects.
#     """
#     logger.info(f"Extracting clauses | chunks={len(chunks)} | doc_type={doc_type}")

#     prompt = _build_extraction_prompt(chunks, doc_type)
#     llm = get_llm(max_tokens=4000, temperature=0.05)

#     for attempt in range(3):
#         try:
#             response = llm.invoke(prompt)
#             content = response.content.strip()

#             # Extract JSON array
#             json_match = re.search(r'\[.*\]', content, re.DOTALL)
#             if not json_match:
#                 logger.warning(f"No JSON array found on attempt {attempt + 1}")
#                 if attempt < 2:
#                     time.sleep(2 ** attempt)
#                 continue

#             raw_clauses = json.loads(json_match.group())

#             # Validate and verify each clause
#             verified = []
#             for c in raw_clauses:
#                 if not isinstance(c, dict):
#                     continue
#                 if "clause_type" not in c or "original_text" not in c:
#                     continue

#                 original = c.get("original_text", "")
#                 is_verified, match_quality = _verify_original_text(original, full_text)

#                 if not is_verified:
#                     logger.debug(
#                         f"Filtered phantom clause: {c.get('clause_type')} "
#                         f"(match_quality={match_quality:.2f})"
#                     )
#                     continue

#                 c["source_verified"] = True
#                 c["match_quality"] = round(match_quality, 2)
#                 verified.append(c)

#             # Deduplicate
#             verified = _deduplicate_clauses(verified)

#             if verified:
#                 logger.info(
#                     f"Extracted {len(verified)} verified clauses "
#                     f"(filtered {len(raw_clauses) - len(verified)} phantom/duplicate) | "
#                     f"attempt={attempt + 1}"
#                 )
#                 return verified

#             logger.warning(f"No verified clauses on attempt {attempt + 1}")
#             if attempt < 2:
#                 time.sleep(2 ** attempt)

#         except json.JSONDecodeError as e:
#             logger.warning(f"JSON parse error on attempt {attempt + 1}: {e}")
#             if attempt < 2:
#                 time.sleep(2 ** attempt)
#         except Exception as e:
#             logger.warning(f"Extraction error on attempt {attempt + 1}: {e}")
#             if attempt < 2:
#                 time.sleep(2 ** attempt)

#     logger.error("All extraction attempts failed")
#     return []
"""
Pass 1: Clause Extraction.
Reads structural chunks and extracts every distinct legal clause,
obligation, condition, restriction, or right from the document.

FIX HISTORY:
1) (original) Batched concurrent extraction with staggered start.
2) (2026-06-22, fix #1) [CURRENT]
   - EXTRACTION_OVERALL_DEADLINE raised 45s → 65s: batch 4 starts at 1.5s,
     needs up to 20s × 3 attempts + 0.75s × 2 backoff = 62.5s worst case.
     45s was mathematically impossible for a 4-batch doc with retries.
   - PER_ATTEMPT_LLM_TIMEOUT raised 20s → 24s: extraction prompts are
     larger than assessment prompts (include raw document text); the 8b
     model genuinely needs more time here.
   - MAX_ATTEMPTS_PER_BATCH raised 2 → 3 for consistency with risk_analyzer.
   - BATCH_STAGGER raised 0.5s → 1.0s: reduces simultaneous Groq key hits.
   - _deduplicate_clauses rewritten:
       * Now does TWO passes: intra-batch (same as before) then cross-batch
       * Dedup no longer requires matching clause_type — catches cases where
         the LLM labels the same clause differently across batches
         (e.g. "Damage Liability" vs "Liability for Damage")
       * Threshold tightened: text overlap > 0.75 (was 0.5) to avoid
         incorrectly merging genuinely distinct clauses
       * Short clauses (< 8 words) use exact text match instead of overlap
"""

import asyncio
import json
import re
import time
from utils.llm import get_fast_llm as get_llm
from utils.logger import get_logger
import nest_asyncio
nest_asyncio.apply()

logger = get_logger("clause_extractor")

# ── Categories the LLM should tag clauses with ────────────────────────────────
CLAUSE_CATEGORIES = [
    "Termination", "Notice Period", "Non-Compete", "Non-Solicitation",
    "IP / Invention Assignment", "Confidentiality / NDA",
    "Indemnity / Liability", "Payment / Compensation",
    "Probation", "Leave Policy", "Working Hours",
    "Dispute Resolution / Jurisdiction", "Governing Law",
    "Force Majeure", "Severability", "Amendment",
    "Bond / Training Cost Recovery", "Relocation",
    "Security Deposit", "Rent Escalation", "Maintenance",
    "Subletting", "Lock-in Period", "Inspection Rights",
    "Scope of Work", "Deliverables", "Auto-Renewal",
    "Data Protection / Privacy", "Warranty / Guarantee",
    "Anti-Disparagement", "Garden Leave", "Moonlighting",
    "Other",
]

MAX_ORIGINAL_TEXT_CHARS = 600
CHUNKS_PER_BATCH        = 3

# ── Timing knobs ──────────────────────────────────────────────────────────────
BATCH_STAGGER_SECONDS               = 1.0    # ↑ from 0.5: less Groq key contention
PER_ATTEMPT_LLM_TIMEOUT_SECONDS     = 24.0   # ↑ from 20: extraction prompts include raw text
MAX_ATTEMPTS_PER_BATCH              = 3      # ↑ from 2
RETRY_BACKOFF_SECONDS               = 1.0    # ↑ from 0.75
# Math: 4 batches × 1.0s stagger = batch4 starts at 3s
#       + 24s × 3 attempts + 1.0s × 2 backoff = 74s worst case
#       65s deadline means batch4 gets ~62s — enough for 2 full attempts + 1 retry
EXTRACTION_OVERALL_DEADLINE_SECONDS = 65.0   # ↑ from 45


def _build_extraction_prompt(chunks: list[dict], doc_type: str) -> str:
    doc_label      = doc_type.replace("_", " ").title()
    categories_str = ", ".join(CLAUSE_CATEGORIES)

    chunks_text = ""
    for chunk in chunks:
        chunks_text += f"\n--- SECTION {chunk['chunk_id'] + 1} ({chunk['section_hint']}) ---\n"
        chunks_text += chunk["text"]
        chunks_text += "\n"

    return f"""You are a meticulous legal analyst extracting clauses from a {doc_label}.

TASK: Read EVERY section below carefully. Extract EVERY distinct legal clause, obligation, condition, restriction, right, or provision. Do NOT skip anything — even standard clauses matter.

For each clause found, provide:
- "clause_type": A short descriptive name (e.g., "Non-Compete Restriction", "IP Assignment", "Notice Period")
- "category": One of: {categories_str}
- "original_text": The EXACT text from the document, copied VERBATIM. Pick ONE COMPLETE SENTENCE (or the smallest set of complete sentences) that best captures the clause's core obligation — aim for roughly 300 characters as a guideline, but NEVER cut a sentence off mid-word or mid-sentence to hit that target. A complete sentence that runs a bit longer than 300 characters is always better than a truncated fragment.
- "section_ref": Which section number or heading this clause appears under

CRITICAL RULES:
1. Extract ONLY clauses that ACTUALLY EXIST in the document text below
2. Do NOT invent, assume, or fabricate clauses that are not present
3. If a common clause type is MISSING from this text, do NOT include it
4. Copy original_text EXACTLY as written — do not paraphrase, rewrite, or truncate mid-sentence
5. Extract at MINIMUM one clause per section/paragraph that contains legal terms
6. If a clause is IDENTICAL to one you already extracted, DO NOT repeat it
7. Return a JSON array — no markdown fences, no commentary

Think step by step: read each section, identify what legal obligations or conditions it creates, then extract.

DOCUMENT SECTIONS ({doc_label}):
{chunks_text}
"""


def _verify_original_text(clause_text: str, source_text: str) -> tuple[bool, float]:
    if not clause_text or clause_text.strip().lower() in (
        "not applicable", "n/a", "none", "na", "-", ""
    ):
        return False, 0.0

    clause_clean = clause_text.strip().lower()
    source_clean = source_text.lower()

    if clause_clean in source_clean:
        return True, 1.0

    clause_words = set(re.findall(r'\b\w{4,}\b', clause_clean))
    if not clause_words:
        return False, 0.0

    source_words = set(re.findall(r'\b\w{4,}\b', source_clean))
    overlap      = clause_words & source_words
    match_ratio  = len(overlap) / len(clause_words)

    return match_ratio >= 0.6, match_ratio


def _clean_original_text(clause_text: str, source_text: str) -> str:
    if not clause_text:
        return clause_text

    stripped   = clause_text.strip()
    ends_clean = stripped[-1] in {'.', '!', '?', '"', "'", ')', ']', '\u201d', '\u2019'} if stripped else True

    if not ends_clean and len(stripped) <= MAX_ORIGINAL_TEXT_CHARS - 20:
        idx = source_text.lower().find(stripped.lower())
        if idx != -1:
            window_end = min(len(source_text), idx + MAX_ORIGINAL_TEXT_CHARS)
            window     = source_text[idx:window_end]
            match      = re.search(r'[.!?](?=\s|$)', window)
            if match:
                stripped = window[:match.end()].strip()

    if len(stripped) > MAX_ORIGINAL_TEXT_CHARS:
        capped         = stripped[:MAX_ORIGINAL_TEXT_CHARS]
        last_boundary  = max(capped.rfind("."), capped.rfind("!"), capped.rfind("?"))
        stripped       = capped[:last_boundary + 1] if last_boundary > 50 else capped

    return stripped


def _text_overlap_ratio(text_a: str, text_b: str) -> float:
    """
    Word-overlap ratio between two strings, normalised to [0, 1].
    Uses the smaller set as denominator so near-subsets score high.
    """
    words_a = set(re.findall(r'\b\w{3,}\b', text_a.lower()))
    words_b = set(re.findall(r'\b\w{3,}\b', text_b.lower()))
    if not words_a or not words_b:
        return 0.0
    return len(words_a & words_b) / min(len(words_a), len(words_b))


def _is_duplicate(candidate: dict, seen: list[dict]) -> bool:
    """
    Returns True if `candidate` is substantively the same as any clause
    already in `seen`.

    Two clauses are duplicates when:
      (a) their original_text overlap ratio > 0.75  (tightened from 0.5), OR
      (b) for short clauses (< 8 words), their texts match exactly.

    Clause_type is NO LONGER required to match — catches cases where the
    same clause is labelled differently across batches.
    """
    c_text  = candidate.get("original_text", "").strip().lower()
    c_words = c_text.split()

    for seen_clause in seen:
        s_text  = seen_clause.get("original_text", "").strip().lower()
        s_words = s_text.split()

        # Short clause: exact match only
        if len(c_words) < 8 or len(s_words) < 8:
            if c_text == s_text:
                return True
            continue

        # Normal clause: word-overlap threshold
        if _text_overlap_ratio(c_text, s_text) > 0.75:
            return True

    return False


def _deduplicate_clauses(clauses: list[dict]) -> list[dict]:
    """
    Single-pass global deduplication across ALL batches.
    Previous implementation only deduped within same clause_type, which
    missed cross-batch and differently-labelled duplicates.
    """
    if len(clauses) <= 1:
        return clauses

    unique: list[dict] = []
    for clause in clauses:
        if _is_duplicate(clause, unique):
            logger.debug(
                f"Dedup: dropped '{clause.get('clause_type', '?')}' "
                f"— text already seen"
            )
        else:
            unique.append(clause)

    removed = len(clauses) - len(unique)
    if removed:
        logger.info(
            f"Deduplication: {len(clauses)} → {len(unique)} "
            f"(removed {removed} duplicate(s))"
        )
    return unique


async def _extract_batch_async(
    batch_chunks: list[dict],
    doc_type: str,
    full_text: str,
    batch_num: int,
) -> list[dict]:
    logger.info(f"Extraction batch {batch_num}: {len(batch_chunks)} chunk(s)")
    prompt = _build_extraction_prompt(batch_chunks, doc_type)
    llm    = get_llm(max_tokens=2500, temperature=0.05)

    for attempt in range(MAX_ATTEMPTS_PER_BATCH):
        try:
            response = await asyncio.wait_for(
                llm.ainvoke(prompt), timeout=PER_ATTEMPT_LLM_TIMEOUT_SECONDS
            )
            content = response.content.strip()

            json_match = re.search(r'\[.*\]', content, re.DOTALL)
            if not json_match:
                logger.warning(
                    f"Extraction batch {batch_num}: no JSON array on attempt {attempt + 1}"
                )
                if attempt < MAX_ATTEMPTS_PER_BATCH - 1:
                    await asyncio.sleep(RETRY_BACKOFF_SECONDS)
                continue

            raw_clauses = json.loads(json_match.group())

            verified = []
            for c in raw_clauses:
                if not isinstance(c, dict):
                    continue
                if "clause_type" not in c or "original_text" not in c:
                    continue

                original = c.get("original_text", "")
                is_ok, match_quality = _verify_original_text(original, full_text)
                if not is_ok:
                    logger.debug(
                        f"Batch {batch_num}: filtered phantom "
                        f"'{c.get('clause_type')}' (match={match_quality:.2f})"
                    )
                    continue

                c["original_text"]   = _clean_original_text(original, full_text)
                c["source_verified"] = True
                c["match_quality"]   = round(match_quality, 2)
                verified.append(c)

            if verified:
                return verified

            logger.warning(
                f"Extraction batch {batch_num}: no verified clauses on attempt {attempt + 1}"
            )
            if attempt < MAX_ATTEMPTS_PER_BATCH - 1:
                await asyncio.sleep(RETRY_BACKOFF_SECONDS)

        except asyncio.TimeoutError:
            logger.warning(
                f"Extraction batch {batch_num}: LLM call exceeded "
                f"{PER_ATTEMPT_LLM_TIMEOUT_SECONDS}s on attempt {attempt + 1}"
            )
            if attempt < MAX_ATTEMPTS_PER_BATCH - 1:
                await asyncio.sleep(RETRY_BACKOFF_SECONDS)

        except json.JSONDecodeError as e:
            logger.warning(
                f"Extraction batch {batch_num}: JSON parse error on attempt {attempt + 1}: {e}"
            )
            if attempt < MAX_ATTEMPTS_PER_BATCH - 1:
                await asyncio.sleep(RETRY_BACKOFF_SECONDS)

        except Exception as e:
            logger.warning(
                f"Extraction batch {batch_num}: error on attempt {attempt + 1}: {e}"
            )
            if attempt < MAX_ATTEMPTS_PER_BATCH - 1:
                await asyncio.sleep(RETRY_BACKOFF_SECONDS)

    logger.error(
        f"Extraction batch {batch_num}: all {MAX_ATTEMPTS_PER_BATCH} attempts failed "
        f"for {len(batch_chunks)} chunk(s) — these section(s) were not analyzed"
    )
    return []


async def _extract_all_batches_with_deadline(
    batches: list[list[dict]],
    doc_type: str,
    full_text: str,
) -> tuple[list[dict], int]:
    async def _delayed(batch, batch_num, delay):
        if delay > 0:
            await asyncio.sleep(delay)
        return await _extract_batch_async(batch, doc_type, full_text, batch_num)

    tasks = [
        asyncio.ensure_future(
            _delayed(batch, i + 1, delay=i * BATCH_STAGGER_SECONDS)
        )
        for i, batch in enumerate(batches)
    ]

    done, pending = await asyncio.wait(tasks, timeout=EXTRACTION_OVERALL_DEADLINE_SECONDS)

    if pending:
        for t in pending:
            t.cancel()
        await asyncio.gather(*pending, return_exceptions=True)

    all_clauses    = []
    skipped_batches = 0

    for batch_num, task in enumerate(tasks, start=1):
        if task in pending:
            logger.error(
                f"Extraction batch {batch_num}: did not finish within the "
                f"{EXTRACTION_OVERALL_DEADLINE_SECONDS}s deadline — "
                f"its section(s) were not analyzed"
            )
            skipped_batches += 1
            continue
        try:
            all_clauses.extend(task.result())
        except Exception as e:
            logger.error(f"Extraction batch {batch_num}: raised after completion: {e}")
            skipped_batches += 1

    return all_clauses, skipped_batches


def extract_clauses(
    chunks: list[dict],
    doc_type: str,
    full_text: str,
) -> tuple[list[dict], int]:
    """
    Pass 1: Extract all clauses from document chunks.
    Returns (verified_deduplicated_clauses, skipped_batch_count).
    skipped_batch_count > 0 means some sections could not be analyzed in
    time — caller should surface this rather than silently presenting an
    incomplete analysis.
    """
    logger.info(f"Extracting clauses | chunks={len(chunks)} | doc_type={doc_type}")

    if not chunks:
        logger.warning("No chunks to extract from")
        return [], 0

    batches = [
        chunks[i:i + CHUNKS_PER_BATCH]
        for i in range(0, len(chunks), CHUNKS_PER_BATCH)
    ]

    start_time = time.monotonic()
    all_clauses, skipped_batches = asyncio.run(
        _extract_all_batches_with_deadline(batches, doc_type, full_text)
    )
    elapsed = time.monotonic() - start_time
    logger.info(
        f"Extraction: {len(batches)} batch(es) resolved in {elapsed:.1f}s "
        f"(deadline={EXTRACTION_OVERALL_DEADLINE_SECONDS}s, skipped={skipped_batches})"
    )

    # Global dedup across ALL batches — catches cross-batch and
    # differently-labelled duplicates that intra-batch dedup misses
    verified = _deduplicate_clauses(all_clauses)

    logger.info(
        f"Extracted {len(verified)} verified clauses | "
        f"skipped_batches={skipped_batches}/{len(batches)}"
    )
    return verified, skipped_batches