import pytest
from unittest.mock import patch
from agents.pipeline import run_pipeline

MOCK_REPORT = {
    "doc_type":      "Offer Letter",
    "risk_score":    5.0,
    "verdict":       {"verdict": "Moderate Risk — Review Carefully", "color": "orange", "advice": "Check clauses.", "severity": "moderate"},
    "coverage":      {"total_clauses_found": 5, "sections_analyzed": 3, "risky_clauses": 2, "safe_clauses": 3, "avg_confidence": 80.0},
    "high_risks":    [],
    "medium_risks":  [],
    "low_risks":     [],
    "safe_clauses":  [],
    "total_flags":   0,
    "analyzed_at":   "01 January 2026, 12:00 PM"
}

MOCK_EXTRACTED_CLAUSES = [
    {"clause_type": "Non-Compete", "original_text": "shall not compete", "category": "Non-Compete", "section_ref": "Section 5"},
]

MOCK_RISKS = [
    {"clause_type": "Non-Compete", "original_text": "shall not compete", "risk_level": "HIGH", "confidence": 90, "reason": "test", "negotiation_tip": "test"},
]


def test_pipeline_returns_dict():
    """Pipeline must always return a dict"""
    with patch("agents.pipeline.detect_document_type",  return_value="OFFER_LETTER"), \
         patch("agents.pipeline.chunk_document",        return_value=[{"chunk_id": 0, "text": "test", "section_hint": "test"}]), \
         patch("agents.pipeline.extract_clauses",       return_value=MOCK_EXTRACTED_CLAUSES), \
         patch("agents.pipeline.assess_risks",          return_value=MOCK_RISKS), \
         patch("agents.pipeline.simplify_risks",        return_value=MOCK_RISKS), \
         patch("agents.pipeline.generate_report",       return_value=MOCK_REPORT):

        result = run_pipeline("sample legal text " * 20)
        assert isinstance(result, dict)


def test_pipeline_short_text_sets_error():
    """Very short text should trigger error state, not raise exception"""
    result = run_pipeline("too short")
    assert result.get("error") is not None
    assert isinstance(result["error"], str)


def test_pipeline_has_all_state_keys():
    """Final state must contain all DocumentState keys"""
    with patch("agents.pipeline.detect_document_type",  return_value="OTHER"), \
         patch("agents.pipeline.chunk_document",        return_value=[{"chunk_id": 0, "text": "test", "section_hint": "test"}]), \
         patch("agents.pipeline.extract_clauses",       return_value=MOCK_EXTRACTED_CLAUSES), \
         patch("agents.pipeline.assess_risks",          return_value=MOCK_RISKS), \
         patch("agents.pipeline.simplify_risks",        return_value=MOCK_RISKS), \
         patch("agents.pipeline.generate_report",       return_value=MOCK_REPORT):

        result = run_pipeline("this is a valid legal document " * 10)

        expected_keys = [
            "raw_text", "doc_type", "chunks", "extracted_clauses",
            "risks", "simplified_risks", "report", "error", "current_step"
        ]
        for key in expected_keys:
            assert key in result, f"Missing key: {key}"


def test_pipeline_complete_step_on_success():
    """On success, current_step must be 'complete'"""
    with patch("agents.pipeline.detect_document_type",  return_value="OFFER_LETTER"), \
         patch("agents.pipeline.chunk_document",        return_value=[{"chunk_id": 0, "text": "test", "section_hint": "test"}]), \
         patch("agents.pipeline.extract_clauses",       return_value=MOCK_EXTRACTED_CLAUSES), \
         patch("agents.pipeline.assess_risks",          return_value=MOCK_RISKS), \
         patch("agents.pipeline.simplify_risks",        return_value=MOCK_RISKS), \
         patch("agents.pipeline.generate_report",       return_value=MOCK_REPORT):

        result = run_pipeline("this is a valid legal document " * 10)
        assert result.get("current_step") == "complete"


def test_pipeline_preserves_raw_text():
    """raw_text in final state must match input"""
    text = "this is a valid legal document " * 10
    with patch("agents.pipeline.detect_document_type",  return_value="OTHER"), \
         patch("agents.pipeline.chunk_document",        return_value=[{"chunk_id": 0, "text": "test", "section_hint": "test"}]), \
         patch("agents.pipeline.extract_clauses",       return_value=MOCK_EXTRACTED_CLAUSES), \
         patch("agents.pipeline.assess_risks",          return_value=MOCK_RISKS), \
         patch("agents.pipeline.simplify_risks",        return_value=MOCK_RISKS), \
         patch("agents.pipeline.generate_report",       return_value=MOCK_REPORT):

        result = run_pipeline(text)
        assert result["raw_text"] == text


def test_pipeline_no_clauses_sets_error():
    """If clause extraction returns empty, pipeline should set an error"""
    with patch("agents.pipeline.detect_document_type",  return_value="OTHER"), \
         patch("agents.pipeline.chunk_document",        return_value=[{"chunk_id": 0, "text": "test", "section_hint": "test"}]), \
         patch("agents.pipeline.extract_clauses",       return_value=[]):

        result = run_pipeline("this is a valid legal document " * 10)
        assert result.get("error") is not None