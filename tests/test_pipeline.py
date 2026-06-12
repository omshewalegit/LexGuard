import pytest
from unittest.mock import patch
from agents.pipeline import run_pipeline

MOCK_REPORT = {
    "doc_type":      "Offer Letter",
    "risk_score":    5.0,
    "verdict":       {"verdict": "Review Carefully", "color": "orange", "advice": "Check clauses."},
    "high_risks":    [],
    "medium_risks":  [],
    "low_risks":     [],
    "safe_clauses":  [],
    "total_flags":   0,
    "analyzed_at":   "01 January 2026, 12:00 PM"
}


def test_pipeline_returns_dict():
    """Pipeline must always return a dict"""
    with patch("agents.pipeline.detect_document_type", return_value="OFFER_LETTER"), \
         patch("agents.pipeline.analyze_risks",        return_value=[]), \
         patch("agents.pipeline.simplify_risks",       return_value=[]), \
         patch("agents.pipeline.generate_report",      return_value=MOCK_REPORT):

        result = run_pipeline("sample legal text " * 20)
        assert isinstance(result, dict)


def test_pipeline_short_text_sets_error():
    """Very short text should trigger error state, not raise exception"""
    result = run_pipeline("too short")
    assert result.get("error") is not None
    assert isinstance(result["error"], str)


def test_pipeline_has_all_state_keys():
    """Final state must contain all DocumentState keys"""
    with patch("agents.pipeline.detect_document_type", return_value="OTHER"), \
         patch("agents.pipeline.analyze_risks",        return_value=[]), \
         patch("agents.pipeline.simplify_risks",       return_value=[]), \
         patch("agents.pipeline.generate_report",      return_value=MOCK_REPORT):

        result = run_pipeline("this is a valid legal document " * 10)

        expected_keys = [
            "raw_text", "doc_type", "risks",
            "simplified_risks", "report", "error", "current_step"
        ]
        for key in expected_keys:
            assert key in result, f"Missing key: {key}"


def test_pipeline_complete_step_on_success():
    """On success, current_step must be 'complete'"""
    with patch("agents.pipeline.detect_document_type", return_value="OFFER_LETTER"), \
         patch("agents.pipeline.analyze_risks",        return_value=[]), \
         patch("agents.pipeline.simplify_risks",       return_value=[]), \
         patch("agents.pipeline.generate_report",      return_value=MOCK_REPORT):

        result = run_pipeline("this is a valid legal document " * 10)
        assert result.get("current_step") == "complete"


def test_pipeline_preserves_raw_text():
    """raw_text in final state must match input"""
    text = "this is a valid legal document " * 10
    with patch("agents.pipeline.detect_document_type", return_value="OTHER"), \
         patch("agents.pipeline.analyze_risks",        return_value=[]), \
         patch("agents.pipeline.simplify_risks",       return_value=[]), \
         patch("agents.pipeline.generate_report",      return_value=MOCK_REPORT):

        result = run_pipeline(text)
        assert result["raw_text"] == text