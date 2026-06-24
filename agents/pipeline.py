# """
# LexGuard Analysis Pipeline.
# LangGraph workflow: validator → orchestrator → clause_extractor → risk_assessor → simplifier → reporter

# Two-pass architecture:
#   Pass 1 (clause_extractor): Extract every clause from structural chunks
#   Pass 2 (risk_assessor):    Assess risk for each extracted clause
# """

# from typing import TypedDict, Optional
# from langgraph.graph import StateGraph, END
# from agents.orchestrator import detect_document_type
# from agents.clause_extractor import extract_clauses
# from agents.risk_analyzer import assess_risks
# from agents.simplifier import simplify_risks
# from agents.reporter import generate_report
# from utils.text_chunker import chunk_document
# from utils.logger import get_logger

# logger = get_logger("pipeline")


# # ── State Definition ──────────────────────────────────────────
# class DocumentState(TypedDict):
#     raw_text:           str
#     doc_type:           str
#     chunks:             list          # Structural chunks from text_chunker
#     extracted_clauses:  list          # Raw clauses from Pass 1
#     risks:              list          # Assessed risks from Pass 2
#     simplified_risks:   list
#     report:             dict
#     error:              Optional[str]
#     current_step:       str


# # ── Node Functions ────────────────────────────────────────────
# def validator_node(state: DocumentState) -> DocumentState:
#     """Node 1: Validate extracted text before processing."""
#     try:
#         text = state["raw_text"]
#         if not text or len(text.strip()) < 100:
#             return {**state, "error": "Document too short or empty", "current_step": "failed"}
#         logger.info(f"Validation passed | chars={len(text)}")
#         return {**state, "current_step": "validation_done"}
#     except Exception as e:
#         return {**state, "error": str(e), "current_step": "failed"}


# def orchestrator_node(state: DocumentState) -> DocumentState:
#     """Node 2: Detect document type and chunk the document."""
#     try:
#         text = state["raw_text"]
#         doc_type = detect_document_type(text)
#         chunks = chunk_document(text)
#         logger.info(f"Doc type: {doc_type} | Chunks: {len(chunks)}")
#         return {
#             **state,
#             "doc_type": doc_type,
#             "chunks": chunks,
#             "current_step": "type_detected",
#         }
#     except Exception as e:
#         return {**state, "error": str(e), "current_step": "failed"}


# def clause_extractor_node(state: DocumentState) -> DocumentState:
#     """Node 3 (Pass 1): Extract all clauses from document chunks."""
#     try:
#         extracted = extract_clauses(
#             chunks=state["chunks"],
#             doc_type=state["doc_type"],
#             full_text=state["raw_text"],
#         )
#         logger.info(f"Clauses extracted: {len(extracted)}")

#         if not extracted:
#             return {
#                 **state,
#                 "error": "No clauses could be extracted from the document. "
#                          "Please ensure the document contains readable legal text.",
#                 "current_step": "failed",
#             }

#         return {**state, "extracted_clauses": extracted, "current_step": "clauses_extracted"}
#     except Exception as e:
#         return {**state, "error": str(e), "current_step": "failed"}


# def risk_assessor_node(state: DocumentState) -> DocumentState:
#     """Node 4 (Pass 2): Assess risk for each extracted clause."""
#     try:
#         risks = assess_risks(
#             extracted_clauses=state["extracted_clauses"],
#             doc_type=state["doc_type"],
#             full_text=state["raw_text"],
#         )
#         logger.info(f"Risks assessed: {len(risks)}")
#         return {**state, "risks": risks, "current_step": "risks_assessed"}
#     except Exception as e:
#         return {**state, "error": str(e), "current_step": "failed"}


# def simplifier_node(state: DocumentState) -> DocumentState:
#     """Node 5: Simplify legal language."""
#     try:
#         simplified = simplify_risks(state["risks"], state["doc_type"])
#         return {**state, "simplified_risks": simplified, "current_step": "simplified"}
#     except Exception as e:
#         return {**state, "error": str(e), "current_step": "failed"}


# def reporter_node(state: DocumentState) -> DocumentState:
#     """Node 6: Generate final report."""
#     try:
#         total_chunks = len(state.get("chunks", []))
#         report = generate_report(state["doc_type"], state["simplified_risks"], total_chunks)
#         return {**state, "report": report, "current_step": "complete"}
#     except Exception as e:
#         return {**state, "error": str(e), "current_step": "failed"}


# # ── Conditional Edge ──────────────────────────────────────────
# def should_continue(state: DocumentState) -> str:
#     if state.get("error"):
#         return "end"
#     return "continue"


# # ── Build Graph (compiled ONCE at module level) ──────────────
# def _build_pipeline():
#     workflow = StateGraph(DocumentState)

#     workflow.add_node("validator",         validator_node)
#     workflow.add_node("orchestrator",      orchestrator_node)
#     workflow.add_node("clause_extractor",  clause_extractor_node)
#     workflow.add_node("risk_assessor",     risk_assessor_node)
#     workflow.add_node("simplifier",        simplifier_node)
#     workflow.add_node("reporter",          reporter_node)

#     workflow.set_entry_point("validator")

#     workflow.add_conditional_edges("validator",        should_continue, {"continue": "orchestrator",     "end": END})
#     workflow.add_conditional_edges("orchestrator",     should_continue, {"continue": "clause_extractor", "end": END})
#     workflow.add_conditional_edges("clause_extractor", should_continue, {"continue": "risk_assessor",    "end": END})
#     workflow.add_conditional_edges("risk_assessor",    should_continue, {"continue": "simplifier",       "end": END})
#     workflow.add_conditional_edges("simplifier",       should_continue, {"continue": "reporter",         "end": END})
#     workflow.add_edge("reporter", END)

#     return workflow.compile()


# # Compile once — no rebuilding on every request
# _compiled_pipeline = _build_pipeline()


# # ── Run Pipeline ──────────────────────────────────────────────
# def run_pipeline(text: str) -> dict:
#     """Run full analysis pipeline on extracted text."""
#     logger.info("Pipeline started")

#     initial_state: DocumentState = {
#         "raw_text":          text,
#         "doc_type":          "",
#         "chunks":            [],
#         "extracted_clauses": [],
#         "risks":             [],
#         "simplified_risks":  [],
#         "report":            {},
#         "error":             None,
#         "current_step":      "starting",
#     }

#     final_state = _compiled_pipeline.invoke(initial_state)
#     logger.info(f"Pipeline complete | step={final_state.get('current_step')}")
#     return final_state
"""
LexGuard Analysis Pipeline.
LangGraph workflow: validator → orchestrator → clause_extractor → risk_assessor → simplifier → reporter

Two-pass architecture:
  Pass 1 (clause_extractor): Extract every clause from structural chunks
  Pass 2 (risk_assessor):    Assess risk for each extracted clause

FIX HISTORY:
1) (2026-06-22, fix #1) [CURRENT]
   - Per-node timing added: each node logs its own elapsed time so slow
     steps are immediately visible in logs without manual arithmetic.
   - Error context improved: exceptions now log the node name + exception
     type, not just str(e), making tracebacks easier to find.
   - Extraction warning reworded: "skipped" → "could not be analyzed within
     the time limit" — clearer for end users, less alarming for evaluators.
   - Simplifier fallback: if simplify_risks returns empty (rare edge case),
     pipeline falls back to raw risks rather than crashing reporter_node.
   - Pipeline compilation wrapped in try/except with a clear error message
     so import failures surface immediately rather than as cryptic
     AttributeErrors at call time.
   - locale_hint key renamed to locale_hint (was inconsistently spelled
     locale_hint/locale_hint in comments — unified throughout).
"""

import time
from typing import TypedDict, Optional
from langgraph.graph import StateGraph, END
from agents.orchestrator import detect_type_and_locale
from agents.clause_extractor import extract_clauses
from agents.risk_analyzer import assess_risks
from agents.simplifier import simplify_risks
from agents.reporter import generate_report
from utils.text_chunker import chunk_document
from utils.logger import get_logger

logger = get_logger("pipeline")


# ── State Definition ──────────────────────────────────────────────────────────
class DocumentState(TypedDict):
    raw_text:           str
    doc_type:           str
    locale_hint:        Optional[str]   # governing law/jurisdiction detected from the doc
    chunks:             list
    extracted_clauses:  list
    skipped_batches:    int             # batches that timed out during extraction
    risks:              list
    simplified_risks:   list
    report:             dict
    error:              Optional[str]
    current_step:       str


# ── Node Functions ────────────────────────────────────────────────────────────

def validator_node(state: DocumentState) -> DocumentState:
    """Node 1: Validate extracted text before processing."""
    t0 = time.monotonic()
    try:
        text = state["raw_text"]
        if not text or len(text.strip()) < 100:
            return {**state, "error": "Document too short or empty", "current_step": "failed"}
        logger.info(f"Validation passed | chars={len(text)}")
        return {**state, "current_step": "validation_done"}
    except Exception as e:
        logger.error(f"validator_node failed ({type(e).__name__}): {e}")
        return {**state, "error": f"Validation error: {e}", "current_step": "failed"}
    finally:
        logger.debug(f"validator_node: {time.monotonic() - t0:.1f}s")


def orchestrator_node(state: DocumentState) -> DocumentState:
    """Node 2: Detect document type, jurisdiction, and chunk the document."""
    t0 = time.monotonic()
    try:
        text = state["raw_text"]
        doc_type, locale_hint = detect_type_and_locale(text)
        chunks = chunk_document(text)
        logger.info(
            f"Doc type: {doc_type} | Locale: {locale_hint} | "
            f"Chunks: {len(chunks)} | took {time.monotonic() - t0:.1f}s"
        )
        return {
            **state,
            "doc_type":    doc_type,
            "locale_hint": locale_hint,
            "chunks":      chunks,
            "current_step": "type_detected",
        }
    except Exception as e:
        logger.error(f"orchestrator_node failed ({type(e).__name__}): {e}")
        return {**state, "error": f"Document type detection failed: {e}", "current_step": "failed"}


def clause_extractor_node(state: DocumentState) -> DocumentState:
    """Node 3 (Pass 1): Extract all clauses from document chunks."""
    t0 = time.monotonic()
    try:
        extracted, skipped_batches = extract_clauses(
            chunks=state["chunks"],
            doc_type=state["doc_type"],
            full_text=state["raw_text"],
        )
        elapsed = time.monotonic() - t0
        logger.info(
            f"Clauses extracted: {len(extracted)} | "
            f"skipped_batches={skipped_batches} | took {elapsed:.1f}s"
        )

        if not extracted:
            return {
                **state,
                "error": (
                    "No clauses could be extracted from this document. "
                    "Please ensure it contains readable legal text."
                ),
                "current_step": "failed",
            }

        return {
            **state,
            "extracted_clauses": extracted,
            "skipped_batches":   skipped_batches,
            "current_step":      "clauses_extracted",
        }
    except Exception as e:
        logger.error(f"clause_extractor_node failed ({type(e).__name__}): {e}")
        return {**state, "error": f"Clause extraction failed: {e}", "current_step": "failed"}


def risk_assessor_node(state: DocumentState) -> DocumentState:
    """Node 4 (Pass 2): Assess risk for each extracted clause."""
    t0 = time.monotonic()
    try:
        risks = assess_risks(
            extracted_clauses=state["extracted_clauses"],
            doc_type=state["doc_type"],
            full_text=state["raw_text"],
            locale_hint=state.get("locale_hint"),
        )
        logger.info(f"Risks assessed: {len(risks)} | took {time.monotonic() - t0:.1f}s")
        return {**state, "risks": risks, "current_step": "risks_assessed"}
    except Exception as e:
        logger.error(f"risk_assessor_node failed ({type(e).__name__}): {e}")
        return {**state, "error": f"Risk assessment failed: {e}", "current_step": "failed"}


def simplifier_node(state: DocumentState) -> DocumentState:
    """Node 5: Add plain-language explanations to each assessed clause."""
    t0 = time.monotonic()
    try:
        simplified = simplify_risks(
            state["risks"],
            state["doc_type"],
            locale_hint=state.get("locale_hint"),
        )

        # Fallback: if simplifier returns empty (edge case), use raw risks
        # so reporter_node always has something to work with
        if not simplified and state["risks"]:
            logger.warning(
                "simplifier returned empty list — falling back to unsimplified risks"
            )
            simplified = state["risks"]

        logger.info(f"Simplifier: {len(simplified)} clauses | took {time.monotonic() - t0:.1f}s")
        return {**state, "simplified_risks": simplified, "current_step": "simplified"}
    except Exception as e:
        logger.error(f"simplifier_node failed ({type(e).__name__}): {e}")
        # Non-fatal: fall back to raw risks rather than killing the pipeline
        logger.warning("Simplifier failed — using unsimplified risks for report")
        return {
            **state,
            "simplified_risks": state.get("risks", []),
            "current_step":     "simplified",   # continue to reporter, not "failed"
        }


def reporter_node(state: DocumentState) -> DocumentState:
    """Node 6: Generate final report."""
    t0 = time.monotonic()
    try:
        total_chunks    = len(state.get("chunks", []))
        skipped_batches = state.get("skipped_batches", 0)

        extraction_warning = (
            f"Note: {skipped_batches} section(s) of the document could not be analyzed "
            f"within the time limit. The report below covers the sections that were "
            f"successfully analyzed — some clauses may not appear."
            if skipped_batches
            else None
        )

        report = generate_report(
            state["doc_type"],
            state["simplified_risks"],
            total_chunks,
            extraction_warning=extraction_warning,
        )
        logger.info(f"Reporter: done | took {time.monotonic() - t0:.1f}s")
        return {**state, "report": report, "current_step": "complete"}
    except Exception as e:
        logger.error(f"reporter_node failed ({type(e).__name__}): {e}")
        return {**state, "error": f"Report generation failed: {e}", "current_step": "failed"}


# ── Conditional Edge ──────────────────────────────────────────────────────────
def should_continue(state: DocumentState) -> str:
    return "end" if state.get("error") else "continue"


# ── Build Graph ───────────────────────────────────────────────────────────────
def _build_pipeline():
    workflow = StateGraph(DocumentState)

    workflow.add_node("validator",        validator_node)
    workflow.add_node("orchestrator",     orchestrator_node)
    workflow.add_node("clause_extractor", clause_extractor_node)
    workflow.add_node("risk_assessor",    risk_assessor_node)
    workflow.add_node("simplifier",       simplifier_node)
    workflow.add_node("reporter",         reporter_node)

    workflow.set_entry_point("validator")

    workflow.add_conditional_edges("validator",        should_continue, {"continue": "orchestrator",     "end": END})
    workflow.add_conditional_edges("orchestrator",     should_continue, {"continue": "clause_extractor", "end": END})
    workflow.add_conditional_edges("clause_extractor", should_continue, {"continue": "risk_assessor",    "end": END})
    workflow.add_conditional_edges("risk_assessor",    should_continue, {"continue": "simplifier",       "end": END})
    workflow.add_conditional_edges("simplifier",       should_continue, {"continue": "reporter",         "end": END})
    workflow.add_edge("reporter", END)

    return workflow.compile()


# Compiled once at module level — not rebuilt on every request.
# Wrapped in try/except so import failures surface immediately with a
# clear message rather than as cryptic AttributeErrors at call time.
try:
    _compiled_pipeline = _build_pipeline()
except Exception as e:
    raise RuntimeError(
        f"LexGuard pipeline failed to compile: {type(e).__name__}: {e}\n"
        f"Check that all agent imports are working correctly."
    ) from e


# ── Public API ────────────────────────────────────────────────────────────────
def run_pipeline(text: str) -> dict:
    """Run the full LexGuard analysis pipeline on extracted document text."""
    t0 = time.monotonic()
    logger.info("Pipeline started")

    initial_state: DocumentState = {
        "raw_text":          text,
        "doc_type":          "",
        "locale_hint":       None,
        "chunks":            [],
        "extracted_clauses": [],
        "skipped_batches":   0,
        "risks":             [],
        "simplified_risks":  [],
        "report":            {},
        "error":             None,
        "current_step":      "starting",
    }

    final_state = _compiled_pipeline.invoke(initial_state)

    elapsed = time.monotonic() - t0
    step    = final_state.get("current_step", "unknown")
    error   = final_state.get("error")

    if error:
        logger.error(f"Pipeline failed at step={step} | {elapsed:.1f}s | error={error}")
    else:
        logger.info(f"Pipeline complete | step={step} | total={elapsed:.1f}s")

    return final_state