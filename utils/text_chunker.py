"""
Structural text chunker for legal documents.
Splits by section boundaries (numbered clauses, headers, paragraphs)
with overlap to ensure no clause is lost at chunk edges.
"""

import re
from utils.logger import get_logger

logger = get_logger("text_chunker")

# ── Section boundary patterns (ordered by priority) ────────────
_SECTION_PATTERNS = [
    # Numbered sections: "1.", "1.1", "12.", "Section 1", "Clause 3"
    re.compile(r'\n\s*(?:Section|Clause|Article)\s+\d+', re.IGNORECASE),
    re.compile(r'\n\s*\d{1,3}\.\d*\s+[A-Z]'),
    re.compile(r'\n\s*\d{1,3}\)\s+'),
    # ALL-CAPS headers: "TERMINATION", "NON-COMPETE CLAUSE"
    re.compile(r'\n\s*[A-Z][A-Z\s]{4,}[A-Z]\s*\n'),
    # Lettered subsections: "(a)", "(b)", "a.", "b."
    re.compile(r'\n\s*\([a-z]\)\s+'),
    re.compile(r'\n\s*[a-z]\.\s+[A-Z]'),
    # Double newlines (paragraph breaks)
    re.compile(r'\n\s*\n'),
]

# ── Configuration ──────────────────────────────────────────────
MIN_CHUNK_CHARS = 800      # Don't create tiny chunks
MAX_CHUNK_CHARS = 3000     # Upper bound per chunk
OVERLAP_CHARS   = 200      # Overlap between adjacent chunks


def _find_section_breaks(text: str) -> list[int]:
    """
    Find all section boundary positions in the text.
    Returns sorted, deduplicated list of character offsets.
    """
    breaks = set()
    for pattern in _SECTION_PATTERNS:
        for match in pattern.finditer(text):
            breaks.add(match.start())
    return sorted(breaks)


def _merge_small_segments(segments: list[str]) -> list[str]:
    """
    Merge segments that are too small into their neighbors.
    """
    if not segments:
        return segments

    merged = [segments[0]]
    for seg in segments[1:]:
        if len(merged[-1]) < MIN_CHUNK_CHARS:
            # Merge into the previous segment
            merged[-1] += seg
        else:
            merged.append(seg)

    # If the last segment is too small, merge it back
    if len(merged) > 1 and len(merged[-1]) < MIN_CHUNK_CHARS:
        merged[-2] += merged[-1]
        merged.pop()

    return merged


def _split_oversized(segment: str) -> list[str]:
    """
    Split a segment that exceeds MAX_CHUNK_CHARS at sentence
    boundaries. Falls back to hard split if no sentences found.
    """
    if len(segment) <= MAX_CHUNK_CHARS:
        return [segment]

    # Try splitting at sentence boundaries
    sentence_ends = [m.end() for m in re.finditer(r'[.!?]\s+', segment)]

    parts = []
    start = 0
    for end_pos in sentence_ends:
        if end_pos - start >= MAX_CHUNK_CHARS:
            parts.append(segment[start:end_pos])
            start = end_pos
        elif end_pos - start >= MIN_CHUNK_CHARS and len(segment) - end_pos < MIN_CHUNK_CHARS:
            # Remaining text is small — don't split here
            continue

    if start < len(segment):
        parts.append(segment[start:])

    # If sentence splitting didn't work, hard split
    if not parts or any(len(p) > MAX_CHUNK_CHARS * 1.5 for p in parts):
        parts = []
        for i in range(0, len(segment), MAX_CHUNK_CHARS):
            parts.append(segment[i:i + MAX_CHUNK_CHARS])

    return parts


def _add_overlap(chunks: list[str]) -> list[str]:
    """
    Add overlap between adjacent chunks so clauses at
    chunk boundaries aren't lost.
    """
    if len(chunks) <= 1:
        return chunks

    overlapped = [chunks[0]]
    for i in range(1, len(chunks)):
        # Prepend tail of previous chunk
        prev_tail = chunks[i - 1][-OVERLAP_CHARS:]
        overlapped.append(prev_tail + chunks[i])

    return overlapped


def _extract_section_hint(text: str) -> str:
    """
    Pull the first recognizable heading or section number
    from a chunk for labeling purposes.
    """
    # Look for numbered section
    m = re.search(
        r'(?:Section|Clause|Article)\s+\d+[.\s:]*([^\n]{0,60})',
        text, re.IGNORECASE
    )
    if m:
        return m.group(0).strip()[:80]

    # Look for ALL-CAPS heading
    m = re.search(r'([A-Z][A-Z\s]{4,}[A-Z])', text)
    if m:
        return m.group(1).strip()[:80]

    # Fall back to first non-empty line
    for line in text.split('\n'):
        line = line.strip()
        if len(line) > 10:
            return line[:80]

    return "Document section"


def chunk_document(text: str) -> list[dict]:
    """
    Split a legal document into structural chunks.

    Returns:
        List of dicts: [
            {"chunk_id": 0, "text": "...", "section_hint": "Section 1: Definitions"},
            ...
        ]
    """
    if not text or len(text.strip()) < 100:
        return [{"chunk_id": 0, "text": text, "section_hint": "Full document"}]

    # Step 1: Find structural boundaries
    breaks = _find_section_breaks(text)

    # Step 2: Split text at boundaries
    if not breaks:
        # No structure found — split by paragraphs / hard split
        segments = [text]
    else:
        segments = []
        prev = 0
        for brk in breaks:
            if brk > prev:
                segments.append(text[prev:brk])
            prev = brk
        if prev < len(text):
            segments.append(text[prev:])

    # Step 3: Merge tiny segments
    segments = _merge_small_segments(segments)

    # Step 4: Split oversized segments
    final_segments = []
    for seg in segments:
        final_segments.extend(_split_oversized(seg))

    # Step 5: Add overlap
    final_segments = _add_overlap(final_segments)

    # Step 6: Build output with hints
    chunks = []
    for i, seg in enumerate(final_segments):
        chunks.append({
            "chunk_id": i,
            "text": seg.strip(),
            "section_hint": _extract_section_hint(seg),
        })

    logger.info(
        f"Chunked document: {len(text)} chars → {len(chunks)} chunks "
        f"(avg {len(text) // max(len(chunks), 1)} chars/chunk)"
    )
    return chunks
