# from typing import TypedDict, Optional
# from langgraph.graph import StateGraph, END
# from agents.orchestrator import detect_document_type
# from agents.risk_analyzer import analyze_risks
# from agents.simplifier import simplify_risks
# from agents.reporter import generate_report
# from utils.pdf_reader import extract_text_from_pdf


# import streamlit as st

# @st.cache_data(show_spinner=False)
# def run_pipeline_cached(text: str, file_hash: str) -> dict:
#     return run_pipeline(text)


# # ── State Definition ──────────────────────────────────────────
# class DocumentState(TypedDict):
#     raw_text: str
#     doc_type: str
#     risks: list
#     simplified_risks: list
#     report: dict
#     error: Optional[str]
#     current_step: str


# # ── Node Functions ────────────────────────────────────────────
# def parser_node(state: DocumentState) -> DocumentState:
#     """Node 1: Validate and prepare text"""
#     try:
#         text = state["raw_text"]
#         if not text or len(text.strip()) < 100:
#             return {**state, "error": "Document too short or empty", "current_step": "failed"}
#         return {**state, "current_step": "parsing_done"}
#     except Exception as e:
#         return {**state, "error": str(e), "current_step": "failed"}


# def orchestrator_node(state: DocumentState) -> DocumentState:
#     """Node 2: Detect document type"""
#     try:
#         doc_type = detect_document_type(state["raw_text"])
#         return {**state, "doc_type": doc_type, "current_step": "type_detected"}
#     except Exception as e:
#         return {**state, "error": str(e), "current_step": "failed"}


# def risk_analyzer_node(state: DocumentState) -> DocumentState:
#     """Node 3: Analyze risks in document"""
#     try:
#         risks = analyze_risks(state["raw_text"], state["doc_type"])
#         return {**state, "risks": risks, "current_step": "risks_analyzed"}
#     except Exception as e:
#         return {**state, "error": str(e), "current_step": "failed"}


# def simplifier_node(state: DocumentState) -> DocumentState:
#     """Node 4: Simplify legal language"""
#     try:
#         simplified = simplify_risks(state["risks"], state["doc_type"])
#         return {**state, "simplified_risks": simplified, "current_step": "simplified"}
#     except Exception as e:
#         return {**state, "error": str(e), "current_step": "failed"}


# def reporter_node(state: DocumentState) -> DocumentState:
#     """Node 5: Generate final report"""
#     try:
#         report = generate_report(state["doc_type"], state["simplified_risks"])
#         return {**state, "report": report, "current_step": "complete"}
#     except Exception as e:
#         return {**state, "error": str(e), "current_step": "failed"}


# # ── Conditional Edge ──────────────────────────────────────────
# def should_continue(state: DocumentState) -> str:
#     if state.get("error"):
#         return "end"
#     return "continue"


# # ── Build Graph ───────────────────────────────────────────────
# def build_pipeline() -> StateGraph:
#     workflow = StateGraph(DocumentState)

#     # Add nodes
#     workflow.add_node("parser", parser_node)
#     workflow.add_node("orchestrator", orchestrator_node)
#     workflow.add_node("risk_analyzer", risk_analyzer_node)
#     workflow.add_node("simplifier", simplifier_node)
#     workflow.add_node("reporter", reporter_node)

#     # Set entry point
#     workflow.set_entry_point("parser")

#     # Add conditional edges
#     workflow.add_conditional_edges(
#         "parser",
#         should_continue,
#         {"continue": "orchestrator", "end": END}
#     )
#     workflow.add_conditional_edges(
#         "orchestrator",
#         should_continue,
#         {"continue": "risk_analyzer", "end": END}
#     )
#     workflow.add_conditional_edges(
#         "risk_analyzer",
#         should_continue,
#         {"continue": "simplifier", "end": END}
#     )
#     workflow.add_conditional_edges(
#         "simplifier",
#         should_continue,
#         {"continue": "reporter", "end": END}
#     )
#     workflow.add_edge("reporter", END)

#     return workflow.compile()


# # ── Run Pipeline ──────────────────────────────────────────────
# def run_pipeline(text: str) -> dict:
#     pipeline = build_pipeline()

#     initial_state: DocumentState = {
#         "raw_text": text,
#         "doc_type": "",
#         "risks": [],
#         "simplified_risks": [],
#         "report": {},
#         "error": None,
#         "current_step": "starting"
#     }

#     final_state = pipeline.invoke(initial_state)
#     return final_state


from typing import TypedDict, Optional
from langgraph.graph import StateGraph, END
from agents.orchestrator import detect_document_type
from agents.risk_analyzer import analyze_risks
from agents.simplifier import simplify_risks
from agents.reporter import generate_report
from utils.logger import get_logger

logger = get_logger("pipeline")


# ── State Definition ──────────────────────────────────────────
class DocumentState(TypedDict):
    raw_text:         str
    doc_type:         str
    risks:            list
    simplified_risks: list
    report:           dict
    error:            Optional[str]
    current_step:     str


# ── Node Functions ────────────────────────────────────────────
def parser_node(state: DocumentState) -> DocumentState:
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
    """Node 2: Detect document type."""
    try:
        doc_type = detect_document_type(state["raw_text"])
        logger.info(f"Doc type: {doc_type}")
        return {**state, "doc_type": doc_type, "current_step": "type_detected"}
    except Exception as e:
        return {**state, "error": str(e), "current_step": "failed"}


def risk_analyzer_node(state: DocumentState) -> DocumentState:
    """Node 3: Analyze risks in document."""
    try:
        risks = analyze_risks(state["raw_text"], state["doc_type"])
        logger.info(f"Risks found: {len(risks)}")
        return {**state, "risks": risks, "current_step": "risks_analyzed"}
    except Exception as e:
        return {**state, "error": str(e), "current_step": "failed"}


def simplifier_node(state: DocumentState) -> DocumentState:
    """Node 4: Simplify legal language."""
    try:
        simplified = simplify_risks(state["risks"], state["doc_type"])
        return {**state, "simplified_risks": simplified, "current_step": "simplified"}
    except Exception as e:
        return {**state, "error": str(e), "current_step": "failed"}


def reporter_node(state: DocumentState) -> DocumentState:
    """Node 5: Generate final report."""
    try:
        report = generate_report(state["doc_type"], state["simplified_risks"])
        return {**state, "report": report, "current_step": "complete"}
    except Exception as e:
        return {**state, "error": str(e), "current_step": "failed"}


# ── Conditional Edge ──────────────────────────────────────────
def should_continue(state: DocumentState) -> str:
    if state.get("error"):
        return "end"
    return "continue"


# ── Build Graph ───────────────────────────────────────────────
def build_pipeline() -> StateGraph:
    workflow = StateGraph(DocumentState)

    workflow.add_node("validator",     parser_node)
    workflow.add_node("orchestrator",  orchestrator_node)
    workflow.add_node("risk_analyzer", risk_analyzer_node)
    workflow.add_node("simplifier",    simplifier_node)
    workflow.add_node("reporter",      reporter_node)

    workflow.set_entry_point("validator")

    workflow.add_conditional_edges("validator",     should_continue, {"continue": "orchestrator",  "end": END})
    workflow.add_conditional_edges("orchestrator",  should_continue, {"continue": "risk_analyzer", "end": END})
    workflow.add_conditional_edges("risk_analyzer", should_continue, {"continue": "simplifier",    "end": END})
    workflow.add_conditional_edges("simplifier",    should_continue, {"continue": "reporter",      "end": END})
    workflow.add_edge("reporter", END)

    return workflow.compile()


# ── Run Pipeline ──────────────────────────────────────────────
def run_pipeline(text: str) -> dict:
    """Run full analysis pipeline on extracted text."""
    logger.info("Pipeline started")
    pipeline = build_pipeline()

    initial_state: DocumentState = {
        "raw_text":         text,
        "doc_type":         "",
        "risks":            [],
        "simplified_risks": [],
        "report":           {},
        "error":            None,
        "current_step":     "starting"
    }

    final_state = pipeline.invoke(initial_state)
    logger.info(f"Pipeline complete | step={final_state.get('current_step')}")
    return final_state