import pytest
from agents.reporter import calculate_risk_score, get_verdict, generate_report


# ── Reusable fixtures ─────────────────────────────────────────
def make_risk(risk_level: str, confidence: int) -> dict:
    """Helper — always produces a complete, consistent risk dict."""
    return {
        "clause_type":      f"Test {risk_level} Clause",
        "original_text":    "Some legal text here.",
        "risk_level":       risk_level,
        "confidence":       confidence,
        "reason":           "Test reason.",
        "negotiation_tip":  "Test tip."
    }


SAMPLE_RISKS = [
    make_risk("HIGH",   90),
    make_risk("MEDIUM", 75),
    make_risk("SAFE",   95),
]


# ── calculate_risk_score ──────────────────────────────────────
def test_risk_score_range():
    """Score must always be between 0.0 and 10.0"""
    score = calculate_risk_score(SAMPLE_RISKS)
    assert 0.0 <= score <= 10.0


def test_empty_risks_returns_zero():
    """Empty list should return exactly 0.0"""
    assert calculate_risk_score([]) == 0.0


def test_all_high_risks_gives_high_score():
    """All HIGH risks with high confidence should score >= 7.0"""
    risks = [make_risk("HIGH", conf) for conf in [95, 90, 88]]
    score = calculate_risk_score(risks)
    assert score >= 7.0


def test_all_safe_gives_zero_score():
    """All SAFE clauses should produce score of 0.0"""
    risks = [make_risk("SAFE", 95) for _ in range(5)]
    assert calculate_risk_score(risks) == 0.0


def test_score_is_float():
    """Score must be a float, not int"""
    score = calculate_risk_score(SAMPLE_RISKS)
    assert isinstance(score, float)


def test_score_capped_at_ten():
    """Score must never exceed 10.0 regardless of inputs"""
    risks = [make_risk("HIGH", 99) for _ in range(20)]
    assert calculate_risk_score(risks) <= 10.0


# ── get_verdict ───────────────────────────────────────────────
def test_verdict_red_for_high_score():
    assert get_verdict(8.0)["color"] == "red"


def test_verdict_red_at_boundary():
    assert get_verdict(7.0)["color"] == "red"


def test_verdict_orange_for_mid_score():
    assert get_verdict(5.0)["color"] == "orange"


def test_verdict_orange_at_boundary():
    assert get_verdict(4.0)["color"] == "orange"


def test_verdict_green_for_low_score():
    assert get_verdict(2.0)["color"] == "green"


def test_verdict_has_required_keys():
    """Verdict dict must have verdict, color, advice"""
    verdict = get_verdict(5.0)
    assert "verdict" in verdict
    assert "color"   in verdict
    assert "advice"  in verdict


# ── generate_report ───────────────────────────────────────────
def test_report_has_all_keys():
    """Report must contain every required key"""
    report = generate_report("OFFER_LETTER", SAMPLE_RISKS)
    required = [
        "doc_type", "risk_score", "verdict",
        "high_risks", "medium_risks", "low_risks",
        "safe_clauses", "total_flags", "analyzed_at"
    ]
    for key in required:
        assert key in report, f"Missing key: {key}"


def test_report_counts_match_input():
    """Filtered list counts must match actual risk levels in input"""
    report = generate_report("OFFER_LETTER", SAMPLE_RISKS)
    assert len(report["high_risks"])   == 1
    assert len(report["medium_risks"]) == 1
    assert len(report["safe_clauses"]) == 1
    assert len(report["low_risks"])    == 0


def test_report_total_flags_excludes_safe():
    """total_flags must not count SAFE clauses"""
    report = generate_report("OFFER_LETTER", SAMPLE_RISKS)
    assert report["total_flags"] == 2  # HIGH + MEDIUM only


def test_report_doc_type_formatted():
    """doc_type should be title-cased with underscores removed"""
    report = generate_report("OFFER_LETTER", SAMPLE_RISKS)
    assert report["doc_type"] == "Offer Letter"


def test_report_empty_risks():
    """Report on empty risks should not crash"""
    report = generate_report("NDA", [])
    assert report["risk_score"] == 0.0
    assert report["total_flags"] == 0