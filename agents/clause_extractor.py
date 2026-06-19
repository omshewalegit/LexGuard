"""
Pass 1: Clause Extraction.
Reads structural chunks and extracts every distinct legal clause,
obligation, condition, restriction, or right from the document.
This is a focused extraction task — no risk assessment yet.
"""

import json
import re
import time
from utils.llm import get_llm
from utils.logger import get_logger

logger = get_logger("clause_extractor")

# ── Categories the LLM should tag clauses with ────────────────
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


def _build_extraction_prompt(chunks: list[dict], doc_type: str) -> str:
    """Build the clause extraction prompt with all chunks."""
    doc_label = doc_type.replace("_", " ").title()
    categories_str = ", ".join(CLAUSE_CATEGORIES)

    chunks_text = ""
    for chunk in chunks:
        chunks_text += f"\n--- SECTION {chunk['chunk_id'] + 1} ({chunk['section_hint']}) ---\n"
        chunks_text += chunk["text"]
        chunks_text += "\n"

    return f"""You are a meticulous legal analyst extracting clauses from a {doc_label}.

TASK: Read EVERY section of this document carefully. Extract EVERY distinct legal clause, obligation, condition, restriction, right, or provision. Do NOT skip anything — even standard clauses matter.

For each clause found, provide:
- "clause_type": A short descriptive name (e.g., "Non-Compete Restriction", "IP Assignment", "Notice Period")
- "category": One of: {categories_str}
- "original_text": The EXACT text from the document, copied VERBATIM (max 300 characters). If the clause is longer, copy the most critical sentence.
- "section_ref": Which section number or heading this clause appears under

CRITICAL RULES:
1. Extract ONLY clauses that ACTUALLY EXIST in the document text below
2. Do NOT invent, assume, or fabricate clauses that are not present
3. If a common clause type is MISSING from the document, do NOT include it
4. Copy original_text EXACTLY as written — do not paraphrase or rewrite
5. Extract at MINIMUM one clause per document section/paragraph that contains legal terms
6. Return a JSON array — no markdown fences, no commentary

Think step by step: read each section, identify what legal obligations or conditions it creates, then extract.

DOCUMENT ({doc_label}):
{chunks_text}
"""


def _verify_original_text(clause_text: str, source_text: str) -> tuple[bool, float]:
    """
    Verify that the extracted original_text actually exists in the source.
    Returns (is_verified, match_quality) where match_quality is 0.0-1.0.
    """
    if not clause_text or clause_text.strip().lower() in (
        "not applicable", "n/a", "none", "na", "-", ""
    ):
        return False, 0.0

    clause_clean = clause_text.strip().lower()
    source_clean = source_text.lower()

    # Exact substring match
    if clause_clean in source_clean:
        return True, 1.0

    # Check if most words from the clause appear in the source (fuzzy)
    clause_words = set(re.findall(r'\b\w{4,}\b', clause_clean))
    if not clause_words:
        return False, 0.0

    source_words = set(re.findall(r'\b\w{4,}\b', source_clean))
    overlap = clause_words & source_words
    match_ratio = len(overlap) / len(clause_words)

    return match_ratio >= 0.6, match_ratio


def _deduplicate_clauses(clauses: list[dict]) -> list[dict]:
    """
    Remove duplicate clauses that were extracted from overlapping chunks.
    Uses clause_type + original_text similarity.
    """
    if len(clauses) <= 1:
        return clauses

    unique = []
    seen_texts = []

    for clause in clauses:
        c_type = clause.get("clause_type", "").lower().strip()
        c_text = clause.get("original_text", "").lower().strip()

        is_duplicate = False
        for seen_type, seen_text in seen_texts:
            # Same clause type with similar text
            if c_type == seen_type:
                # Check text overlap
                if c_text and seen_text:
                    c_words = set(c_text.split())
                    s_words = set(seen_text.split())
                    if c_words and s_words:
                        overlap = len(c_words & s_words) / min(len(c_words), len(s_words))
                        if overlap > 0.5:
                            is_duplicate = True
                            break

        if not is_duplicate:
            unique.append(clause)
            seen_texts.append((c_type, c_text))

    removed = len(clauses) - len(unique)
    if removed:
        logger.info(f"Deduplication: {len(clauses)} → {len(unique)} (removed {removed} duplicates)")

    return unique


def extract_clauses(chunks: list[dict], doc_type: str, full_text: str) -> list[dict]:
    """
    Pass 1: Extract all clauses from document chunks.
    Returns list of verified, deduplicated clause objects.
    """
    logger.info(f"Extracting clauses | chunks={len(chunks)} | doc_type={doc_type}")

    prompt = _build_extraction_prompt(chunks, doc_type)
    llm = get_llm(max_tokens=4000, temperature=0.05)

    for attempt in range(3):
        try:
            response = llm.invoke(prompt)
            content = response.content.strip()

            # Extract JSON array
            json_match = re.search(r'\[.*\]', content, re.DOTALL)
            if not json_match:
                logger.warning(f"No JSON array found on attempt {attempt + 1}")
                if attempt < 2:
                    time.sleep(2 ** attempt)
                continue

            raw_clauses = json.loads(json_match.group())

            # Validate and verify each clause
            verified = []
            for c in raw_clauses:
                if not isinstance(c, dict):
                    continue
                if "clause_type" not in c or "original_text" not in c:
                    continue

                original = c.get("original_text", "")
                is_verified, match_quality = _verify_original_text(original, full_text)

                if not is_verified:
                    logger.debug(
                        f"Filtered phantom clause: {c.get('clause_type')} "
                        f"(match_quality={match_quality:.2f})"
                    )
                    continue

                c["source_verified"] = True
                c["match_quality"] = round(match_quality, 2)
                verified.append(c)

            # Deduplicate
            verified = _deduplicate_clauses(verified)

            if verified:
                logger.info(
                    f"Extracted {len(verified)} verified clauses "
                    f"(filtered {len(raw_clauses) - len(verified)} phantom/duplicate) | "
                    f"attempt={attempt + 1}"
                )
                return verified

            logger.warning(f"No verified clauses on attempt {attempt + 1}")
            if attempt < 2:
                time.sleep(2 ** attempt)

        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse error on attempt {attempt + 1}: {e}")
            if attempt < 2:
                time.sleep(2 ** attempt)
        except Exception as e:
            logger.warning(f"Extraction error on attempt {attempt + 1}: {e}")
            if attempt < 2:
                time.sleep(2 ** attempt)

    logger.error("All extraction attempts failed")
    return []
