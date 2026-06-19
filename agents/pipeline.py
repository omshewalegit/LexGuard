"""
LexGuard Analysis Pipeline.
LangGraph workflow: validator → orchestrator → clause_extractor → risk_assessor → simplifier → reporter

Two-pass architecture:
  Pass 1 (clause_extractor): Extract every clause from structural chunks
  Pass 2 (risk_assessor):    Assess risk for each extracted clause
"""

from typing import TypedDict, Optional
from langgraph.graph import StateGraph, END
from agents.orchestrator import detect_document_type
from agents.clause_extractor import extract_clauses
from agents.risk_analyzer import assess_risks
from agents.simplifier import simplify_risks
from agents.reporter import generate_report
from utils.text_chunker import chunk_document
from utils.logger import get_logger

logger = get_logger("pipeline")


# ── State Definition ──────────────────────────────────────────
class DocumentState(TypedDict):
    raw_text:           str
    doc_type:           str
    chunks:             list          # Structural chunks from text_chunker
    extracted_clauses:  list          # Raw clauses from Pass 1
    risks:              list          # Assessed risks from Pass 2
    simplified_risks:   list
    report:             dict
    error:              Optional[str]
    current_step:       str


# ── Node Functions ────────────────────────────────────────────
def validator_node(state: DocumentState) -> DocumentState:
    """Node 1: Validate extracted text before processing."""
    try:
        text = state["raw_text"]
        if not text or len(text.strip()) < 100:
            return {**state, "error": "Document too short or empty", "current_step": "failed"}
        logger.info(f"Validation passed | chars={len(text)}")
        return {**state, "current_step": "validation_done"}
    except Exception as e:
        return {**state, "error": str(e), "current_step": "failed"}


def orchestrator_node(state: DocumentState) -> DocumentState:
    """Node 2: Detect document type and chunk the document."""
    try:
        text = state["raw_text"]
        doc_type = detect_document_type(text)
        chunks = chunk_document(text)
        logger.info(f"Doc type: {doc_type} | Chunks: {len(chunks)}")
        return {
            **state,
            "doc_type": doc_type,
            "chunks": chunks,
            "current_step": "type_detected",
        }
    except Exception as e:
        return {**state, "error": str(e), "current_step": "failed"}


def clause_extractor_node(state: DocumentState) -> DocumentState:
    """Node 3 (Pass 1): Extract all clauses from document chunks."""
    try:
        extracted = extract_clauses(
            chunks=state["chunks"],
            doc_type=state["doc_type"],
            full_text=state["raw_text"],
        )
        logger.info(f"Clauses extracted: {len(extracted)}")

        if not extracted:
            return {
                **state,
                "error": "No clauses could be extracted from the document. "
                         "Please ensure the document contains readable legal text.",
                "current_step": "failed",
            }

        return {**state, "extracted_clauses": extracted, "current_step": "clauses_extracted"}
    except Exception as e:
        return {**state, "error": str(e), "current_step": "failed"}


def risk_assessor_node(state: DocumentState) -> DocumentState:
    """Node 4 (Pass 2): Assess risk for each extracted clause."""
    try:
        risks = assess_risks(
            extracted_clauses=state["extracted_clauses"],
            doc_type=state["doc_type"],
            full_text=state["raw_text"],
        )
        logger.info(f"Risks assessed: {len(risks)}")
        return {**state, "risks": risks, "current_step": "risks_assessed"}
    except Exception as e:
        return {**state, "error": str(e), "current_step": "failed"}


def simplifier_node(state: DocumentState) -> DocumentState:
    """Node 5: Simplify legal language."""
    try:
        simplified = simplify_risks(state["risks"], state["doc_type"])
        return {**state, "simplified_risks": simplified, "current_step": "simplified"}
    except Exception as e:
        return {**state, "error": str(e), "current_step": "failed"}


def reporter_node(state: DocumentState) -> DocumentState:
    """Node 6: Generate final report."""
    try:
        total_chunks = len(state.get("chunks", []))
        report = generate_report(state["doc_type"], state["simplified_risks"], total_chunks)
        return {**state, "report": report, "current_step": "complete"}
    except Exception as e:
        return {**state, "error": str(e), "current_step": "failed"}


# ── Conditional Edge ──────────────────────────────────────────
def should_continue(state: DocumentState) -> str:
    if state.get("error"):
        return "end"
    return "continue"


# ── Build Graph (compiled ONCE at module level) ──────────────
def _build_pipeline():
    workflow = StateGraph(DocumentState)

    workflow.add_node("validator",         validator_node)
    workflow.add_node("orchestrator",      orchestrator_node)
    workflow.add_node("clause_extractor",  clause_extractor_node)
    workflow.add_node("risk_assessor",     risk_assessor_node)
    workflow.add_node("simplifier",        simplifier_node)
    workflow.add_node("reporter",          reporter_node)

    workflow.set_entry_point("validator")

    workflow.add_conditional_edges("validator",        should_continue, {"continue": "orchestrator",     "end": END})
    workflow.add_conditional_edges("orchestrator",     should_continue, {"continue": "clause_extractor", "end": END})
    workflow.add_conditional_edges("clause_extractor", should_continue, {"continue": "risk_assessor",    "end": END})
    workflow.add_conditional_edges("risk_assessor",    should_continue, {"continue": "simplifier",       "end": END})
    workflow.add_conditional_edges("simplifier",       should_continue, {"continue": "reporter",         "end": END})
    workflow.add_edge("reporter", END)

    return workflow.compile()


# Compile once — no rebuilding on every request
_compiled_pipeline = _build_pipeline()


# ── Run Pipeline ──────────────────────────────────────────────
def run_pipeline(text: str) -> dict:
    """Run full analysis pipeline on extracted text."""
    logger.info("Pipeline started")

    initial_state: DocumentState = {
        "raw_text":          text,
        "doc_type":          "",
        "chunks":            [],
        "extracted_clauses": [],
        "risks":             [],
        "simplified_risks":  [],
        "report":            {},
        "error":             None,
        "current_step":      "starting",
    }

    final_state = _compiled_pipeline.invoke(initial_state)
    logger.info(f"Pipeline complete | step={final_state.get('current_step')}")
    return final_state
