"""
Report generator.
Calculates risk scores, coverage metrics, and compiles the final report.
"""

from datetime import datetime
from utils.logger import get_logger

logger = get_logger("reporter")

SCORE_MAP  = {"HIGH": 9, "MEDIUM": 5, "LOW": 2, "SAFE": 0, "UNKNOWN": 3}
WEIGHT_MAP = {"HIGH": 3, "MEDIUM": 2, "LOW": 1, "SAFE": 0, "UNKNOWN": 1}


def calculate_risk_score(risks: list) -> float:
    """
    Weighted risk score from 0.0 to 10.0.
    SAFE clauses have zero weight (they don't dilute the score).
    """
    if not risks:
        return 0.0

    total_score  = 0.0
    total_weight = 0.0

    for risk in risks:
        level      = risk.get("risk_level", "UNKNOWN").upper()
        confidence = risk.get("confidence", 50) / 100
        score      = SCORE_MAP.get(level, 3)
        weight     = WEIGHT_MAP.get(level, 1)

        total_score  += score * weight * confidence
        total_weight += weight

    if total_weight == 0:
        return 0.0

    return round(min(10.0, total_score / total_weight), 1)


def get_verdict(score: float) -> dict:
    """
    5-tier verdict system for more nuanced assessment.
    """
    if score >= 8.0:
        return {
            "verdict": "Do Not Sign — Serious Issues Found",
            "color":   "red",
            "advice":  "Critical clauses detected that could cause significant financial or career harm. Seek legal counsel before proceeding.",
            "severity": "critical",
        }
    elif score >= 6.0:
        return {
            "verdict": "High Risk — Negotiate Before Signing",
            "color":   "red",
            "advice":  "Multiple unfavorable clauses detected. Request amendments on flagged items before signing.",
            "severity": "high",
        }
    elif score >= 4.0:
        return {
            "verdict": "Moderate Risk — Review Carefully",
            "color":   "orange",
            "advice":  "Some clauses need attention. Negotiate the flagged points where possible.",
            "severity": "moderate",
        }
    elif score >= 2.0:
        return {
            "verdict": "Low Risk — Generally Fair",
            "color":   "green",
            "advice":  "Minor concerns noted but overall a fair document. Review flagged items for awareness.",
            "severity": "low",
        }
    else:
        return {
            "verdict": "Safe to Sign — Well Balanced",
            "color":   "green",
            "advice":  "No significant red flags detected. Standard, balanced clauses throughout.",
            "severity": "safe",
        }


def _calculate_coverage(risks: list, total_chunks: int) -> dict:
    """
    Calculate how thoroughly the document was analyzed.
    """
    total_clauses = len(risks)
    risky_count = sum(1 for r in risks if r.get("risk_level") in ("HIGH", "MEDIUM", "LOW"))
    safe_count = sum(1 for r in risks if r.get("risk_level") == "SAFE")

    # Calculate average confidence
    confidences = [r.get("confidence", 0) for r in risks if r.get("confidence", 0) > 0]
    avg_confidence = round(sum(confidences) / len(confidences), 1) if confidences else 0.0

    return {
        "total_clauses_found": total_clauses,
        "sections_analyzed": total_chunks,
        "risky_clauses": risky_count,
        "safe_clauses": safe_count,
        "avg_confidence": avg_confidence,
    }


def generate_report(doc_type: str, risks: list, total_chunks: int = 0) -> dict:
    """Compile final report dict from analyzed risks."""
    score   = calculate_risk_score(risks)
    verdict = get_verdict(score)
    coverage = _calculate_coverage(risks, total_chunks)

    report = {
        "doc_type":      doc_type.replace("_", " ").title(),
        "risk_score":    score,
        "verdict":       verdict,
        "coverage":      coverage,
        "high_risks":    [r for r in risks if r.get("risk_level") == "HIGH"],
        "medium_risks":  [r for r in risks if r.get("risk_level") == "MEDIUM"],
        "low_risks":     [r for r in risks if r.get("risk_level") == "LOW"],
        "safe_clauses":  [r for r in risks if r.get("risk_level") == "SAFE"],
        "total_flags":   sum(1 for r in risks if r.get("risk_level") in ["HIGH", "MEDIUM", "LOW"]),
        "analyzed_at":   datetime.now().strftime("%d %B %Y, %I:%M %p")
    }

    logger.info(
        f"Report generated | doc={doc_type} | score={score} | "
        f"high={len(report['high_risks'])} | medium={len(report['medium_risks'])} | "
        f"low={len(report['low_risks'])} | safe={len(report['safe_clauses'])} | "
        f"coverage={coverage['total_clauses_found']} clauses from {coverage['sections_analyzed']} sections"
    )
    return report
