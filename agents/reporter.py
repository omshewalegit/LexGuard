# """
# Report generator.
# Calculates risk scores, coverage metrics, and compiles the final report.
# """

# from datetime import datetime
# from utils.logger import get_logger

# logger = get_logger("reporter")

# SCORE_MAP  = {"HIGH": 9, "MEDIUM": 5, "LOW": 2, "SAFE": 0, "UNKNOWN": 3}
# WEIGHT_MAP = {"HIGH": 3, "MEDIUM": 2, "LOW": 1, "SAFE": 0, "UNKNOWN": 1}


# def calculate_risk_score(risks: list) -> float:
#     """
#     Weighted risk score from 0.0 to 10.0.
#     SAFE clauses have zero weight (they don't dilute the score).
#     """
#     if not risks:
#         return 0.0

#     total_score  = 0.0
#     total_weight = 0.0

#     for risk in risks:
#         level      = risk.get("risk_level", "UNKNOWN").upper()
#         confidence = risk.get("confidence", 50) / 100
#         score      = SCORE_MAP.get(level, 3)
#         weight     = WEIGHT_MAP.get(level, 1)

#         total_score  += score * weight * confidence
#         total_weight += weight

#     if total_weight == 0:
#         return 0.0

#     return round(min(10.0, total_score / total_weight), 1)


# def get_verdict(score: float) -> dict:
#     """
#     5-tier verdict system for more nuanced assessment.
#     """
#     if score >= 8.0:
#         return {
#             "verdict": "Do Not Sign — Serious Issues Found",
#             "color":   "red",
#             "advice":  "Critical clauses detected that could cause significant financial or career harm. Seek legal counsel before proceeding.",
#             "severity": "critical",
#         }
#     elif score >= 6.0:
#         return {
#             "verdict": "High Risk — Negotiate Before Signing",
#             "color":   "red",
#             "advice":  "Multiple unfavorable clauses detected. Request amendments on flagged items before signing.",
#             "severity": "high",
#         }
#     elif score >= 4.0:
#         return {
#             "verdict": "Moderate Risk — Review Carefully",
#             "color":   "orange",
#             "advice":  "Some clauses need attention. Negotiate the flagged points where possible.",
#             "severity": "moderate",
#         }
#     elif score >= 2.0:
#         return {
#             "verdict": "Low Risk — Generally Fair",
#             "color":   "green",
#             "advice":  "Minor concerns noted but overall a fair document. Review flagged items for awareness.",
#             "severity": "low",
#         }
#     else:
#         return {
#             "verdict": "Safe to Sign — Well Balanced",
#             "color":   "green",
#             "advice":  "No significant red flags detected. Standard, balanced clauses throughout.",
#             "severity": "safe",
#         }


# def _calculate_coverage(risks: list, total_chunks: int) -> dict:
#     """
#     Calculate how thoroughly the document was analyzed.
#     """
#     total_clauses = len(risks)
#     risky_count = sum(1 for r in risks if r.get("risk_level") in ("HIGH", "MEDIUM", "LOW"))
#     safe_count = sum(1 for r in risks if r.get("risk_level") == "SAFE")

#     # Calculate average confidence
#     confidences = [r.get("confidence", 0) for r in risks if r.get("confidence", 0) > 0]
#     avg_confidence = round(sum(confidences) / len(confidences), 1) if confidences else 0.0

#     return {
#         "total_clauses_found": total_clauses,
#         "sections_analyzed": total_chunks,
#         "risky_clauses": risky_count,
#         "safe_clauses": safe_count,
#         "avg_confidence": avg_confidence,
#     }


# def generate_report(doc_type: str, risks: list, total_chunks: int = 0) -> dict:
#     """Compile final report dict from analyzed risks."""
#     score   = calculate_risk_score(risks)
#     verdict = get_verdict(score)
#     coverage = _calculate_coverage(risks, total_chunks)

#     report = {
#         "doc_type":      doc_type.replace("_", " ").title(),
#         "risk_score":    score,
#         "verdict":       verdict,
#         "coverage":      coverage,
#         "high_risks":    [r for r in risks if r.get("risk_level") == "HIGH"],
#         "medium_risks":  [r for r in risks if r.get("risk_level") == "MEDIUM"],
#         "low_risks":     [r for r in risks if r.get("risk_level") == "LOW"],
#         "safe_clauses":  [r for r in risks if r.get("risk_level") == "SAFE"],
#         "total_flags":   sum(1 for r in risks if r.get("risk_level") in ["HIGH", "MEDIUM", "LOW"]),
#         "analyzed_at":   datetime.now().strftime("%d %B %Y, %I:%M %p")
#     }

#     logger.info(
#         f"Report generated | doc={doc_type} | score={score} | "
#         f"high={len(report['high_risks'])} | medium={len(report['medium_risks'])} | "
#         f"low={len(report['low_risks'])} | safe={len(report['safe_clauses'])} | "
#         f"coverage={coverage['total_clauses_found']} clauses from {coverage['sections_analyzed']} sections"
#     )
#     return report
"""
Report generator.
Calculates risk scores, coverage metrics, and compiles the final report.

FIX HISTORY:
1) (2026-06-22, fix #1) [CURRENT]
   - calculate_risk_score: None-safe confidence handling — risk_analyzer.py
     now sets confidence=None for UNKNOWN clauses instead of 0; dividing
     None by 100 was a TypeError crash waiting to happen.
   - Score explanation added to report: "3.9/10" now includes a plain-English
     breakdown of how the score was calculated so users and evaluators
     understand it isn't arbitrary.
   - Top 3 priorities added: post-processing picks the 3 most actionable
     flagged clauses (HIGH first, then MEDIUM by confidence) and surfaces
     them as "negotiate these before signing" — the single most useful
     addition for a non-lawyer user.
   - avg_confidence fixed: UNKNOWN clauses (confidence=None) are now
     excluded from the average — they're timeouts, not low-confidence
     assessments, and were unfairly dragging the number down.
   - _detect_generic_tips: post-processing pass that flags negotiation_tips
     that are boilerplate/copy-pasted rather than clause-specific. Logged
     as a warning so it's visible during development.
   - Scoring methodology documented inline so it's reproducible and
     explainable in a placement presentation.
"""

from datetime import datetime
from utils.logger import get_logger

logger = get_logger("reporter")

# ── Scoring methodology ───────────────────────────────────────────────────────
# Score = weighted average of (clause_severity × confidence), scaled 0–10.
# SAFE clauses have weight=0 so they don't dilute the score — a contract
# with 50 safe clauses and 1 HIGH clause should still score high.
# UNKNOWN clauses use a fixed mid-penalty (no confidence adjustment) because
# an unanalyzed clause represents hidden risk, not zero risk.
#
# Formula per clause:
#   contribution = SCORE_MAP[level] × WEIGHT_MAP[level] × (confidence / 100)
#   [UNKNOWN uses fixed score×weight, no confidence factor]
# Final score = sum(contributions) / sum(weights), capped at 10.0

SCORE_MAP  = {"HIGH": 9, "MEDIUM": 5, "LOW": 2, "SAFE": 0, "UNKNOWN": 6}
WEIGHT_MAP = {"HIGH": 3, "MEDIUM": 2, "LOW": 1, "SAFE": 0, "UNKNOWN": 2}

# Tips that are copy-pasted boilerplate — flagged in logs during development
_GENERIC_TIP_PHRASES = [
    "request clarification or amendment",
    "no action needed",
    "consider including a cap on the amount that can be billed",
    "consult a lawyer",
    "seek legal advice",
    "please review this clause manually",
]


def calculate_risk_score(risks: list) -> float:
    """
    Weighted risk score from 0.0 to 10.0.
    SAFE clauses have zero weight (they don't dilute the score).
    UNKNOWN clauses are penalized — unanalyzed = potential hidden risk.
    confidence=None is treated as 0.5 (50%) — genuinely uncertain.
    """
    if not risks:
        return 0.0

    total_score  = 0.0
    total_weight = 0.0

    for risk in risks:
        level = risk.get("risk_level", "UNKNOWN").upper()

        # None-safe: confidence=None (from unanalyzed clauses) → treat as 50%
        raw_conf   = risk.get("confidence")
        confidence = (raw_conf / 100.0) if isinstance(raw_conf, (int, float)) else 0.5

        if level == "UNKNOWN":
            # Fixed penalty — no confidence adjustment for unanalyzed clauses
            total_score  += SCORE_MAP["UNKNOWN"] * WEIGHT_MAP["UNKNOWN"]
            total_weight += WEIGHT_MAP["UNKNOWN"]
            continue

        score  = SCORE_MAP.get(level, 3)
        weight = WEIGHT_MAP.get(level, 1)

        total_score  += score * weight * confidence
        total_weight += weight

    if total_weight == 0:
        return 0.0

    return round(min(10.0, total_score / total_weight), 1)


def explain_score(score: float, risks: list) -> str:
    """
    Plain-English explanation of how the score was derived.
    Shown in the report so users understand it's not arbitrary.
    """
    high   = sum(1 for r in risks if r.get("risk_level") == "HIGH")
    medium = sum(1 for r in risks if r.get("risk_level") == "MEDIUM")
    low    = sum(1 for r in risks if r.get("risk_level") == "LOW")
    safe   = sum(1 for r in risks if r.get("risk_level") == "SAFE")
    unk    = sum(1 for r in risks if r.get("risk_level") == "UNKNOWN")

    parts = []
    if high:
        parts.append(f"{high} high-risk clause{'s' if high > 1 else ''} (weight ×3)")
    if medium:
        parts.append(f"{medium} medium-risk clause{'s' if medium > 1 else ''} (weight ×2)")
    if low:
        parts.append(f"{low} low-risk clause{'s' if low > 1 else ''} (weight ×1)")
    if safe:
        parts.append(f"{safe} safe clause{'s' if safe > 1 else ''} (not counted)")
    if unk:
        parts.append(f"{unk} unanalyzed clause{'s' if unk > 1 else ''} (penalized as hidden risk)")

    composition = ", ".join(parts) if parts else "no clauses found"
    return (
        f"Score of {score}/10 based on: {composition}. "
        f"Each clause is weighted by severity and the model's confidence. "
        f"Safe clauses do not reduce the score — only risky clauses raise it."
    )


def get_verdict(score: float) -> dict:
    """5-tier verdict system."""
    if score >= 8.0:
        return {
            "verdict":  "Do Not Sign — Serious Issues Found",
            "color":    "red",
            "advice":   "Critical clauses detected that could cause significant financial or legal harm. Seek legal counsel before proceeding.",
            "severity": "critical",
        }
    elif score >= 6.0:
        return {
            "verdict":  "High Risk — Negotiate Before Signing",
            "color":    "red",
            "advice":   "Multiple unfavorable clauses detected. Request amendments on flagged items before signing.",
            "severity": "high",
        }
    elif score >= 4.0:
        return {
            "verdict":  "Moderate Risk — Review Carefully",
            "color":    "orange",
            "advice":   "Some clauses need attention. Negotiate the flagged points where possible.",
            "severity": "moderate",
        }
    elif score >= 2.0:
        return {
            "verdict":  "Low Risk — Generally Fair",
            "color":    "green",
            "advice":   "Minor concerns noted but overall a fair document. Review flagged items for awareness.",
            "severity": "low",
        }
    else:
        return {
            "verdict":  "Safe to Sign — Well Balanced",
            "color":    "green",
            "advice":   "No significant red flags detected. Standard, balanced clauses throughout.",
            "severity": "safe",
        }


def _get_top_priorities(risks: list, n: int = 3) -> list[dict]:
    """
    Pick the N most actionable clauses to negotiate.
    Priority order: HIGH (by confidence desc) → MEDIUM (by confidence desc).
    Only includes clauses that have a non-generic negotiation tip.
    Returns simplified dicts for the report summary section.
    """
    def _priority_key(r):
        level      = r.get("risk_level", "SAFE")
        raw_conf   = r.get("confidence")
        confidence = raw_conf if isinstance(raw_conf, (int, float)) else 50
        order      = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}.get(level, 9)
        return (order, -confidence)

    actionable = [
        r for r in risks
        if r.get("risk_level") in ("HIGH", "MEDIUM", "LOW")
        and r.get("negotiation_tip", "").strip()
        and not _is_generic_tip(r.get("negotiation_tip", ""))
    ]

    # Fall back to including generic tips if we don't have enough specific ones
    if len(actionable) < n:
        fallback = [
            r for r in risks
            if r.get("risk_level") in ("HIGH", "MEDIUM", "LOW")
            and r not in actionable
        ]
        actionable += fallback

    top = sorted(actionable, key=_priority_key)[:n]

    return [
        {
            "clause_type":     r.get("clause_type", "Unknown"),
            "risk_level":      r.get("risk_level", "MEDIUM"),
            "negotiation_tip": r.get("negotiation_tip", ""),
            "original_text":   r.get("original_text", "")[:150],
        }
        for r in top
    ]


def _is_generic_tip(tip: str) -> bool:
    """Returns True if the tip is boilerplate rather than clause-specific."""
    tip_lower = tip.lower().strip()
    return any(phrase in tip_lower for phrase in _GENERIC_TIP_PHRASES)


def _detect_generic_tips(risks: list) -> int:
    """
    Log a warning for each clause whose negotiation_tip is generic/boilerplate.
    Returns count of generic tips found (useful for dev monitoring).
    """
    generic_count = 0
    for r in risks:
        tip = r.get("negotiation_tip", "")
        if tip and _is_generic_tip(tip):
            generic_count += 1
            logger.debug(
                f"Generic tip detected on '{r.get('clause_type', '?')}': \"{tip[:80]}...\""
            )
    if generic_count:
        logger.warning(
            f"{generic_count} clause(s) have generic/boilerplate negotiation tips — "
            f"check risk_analyzer prompt quality"
        )
    return generic_count


def _calculate_coverage(
    risks: list,
    total_chunks: int,
    unanalyzed_count: int,
) -> dict:
    total_clauses = len(risks)
    risky_count   = sum(1 for r in risks if r.get("risk_level") in ("HIGH", "MEDIUM", "LOW"))
    safe_count    = sum(1 for r in risks if r.get("risk_level") == "SAFE")

    # Exclude UNKNOWN (confidence=None) from avg_confidence — they're
    # timeouts, not low-confidence assessments
    confidences = [
        r["confidence"] for r in risks
        if isinstance(r.get("confidence"), (int, float))
        and r.get("risk_level") != "UNKNOWN"
    ]
    avg_confidence = round(sum(confidences) / len(confidences), 1) if confidences else 0.0

    return {
        "total_clauses_found": total_clauses,
        "sections_analyzed":   total_chunks,
        "risky_clauses":       risky_count,
        "safe_clauses":        safe_count,
        "unanalyzed_clauses":  unanalyzed_count,
        "avg_confidence":      avg_confidence,
    }


def generate_report(
    doc_type: str,
    risks: list,
    total_chunks: int = 0,
    extraction_warning: str = None,
) -> dict:
    """Compile final report dict from analyzed risks."""
    score   = calculate_risk_score(risks)
    verdict = get_verdict(score)

    unanalyzed    = [r for r in risks if r.get("risk_level", "UNKNOWN").upper() == "UNKNOWN"]
    coverage      = _calculate_coverage(risks, total_chunks, len(unanalyzed))
    generic_count = _detect_generic_tips(risks)

    report = {
        "doc_type":           doc_type.replace("_", " ").title(),
        "risk_score":         score,
        "score_explanation":  explain_score(score, risks),   # ← NEW: no more mystery number
        "verdict":            verdict,
        "coverage":           coverage,
        "top_priorities":     _get_top_priorities(risks, n=3),  # ← NEW: "negotiate these 3"
        "high_risks":         [r for r in risks if r.get("risk_level") == "HIGH"],
        "medium_risks":       [r for r in risks if r.get("risk_level") == "MEDIUM"],
        "low_risks":          [r for r in risks if r.get("risk_level") == "LOW"],
        "safe_clauses":       [r for r in risks if r.get("risk_level") == "SAFE"],
        "unanalyzed_clauses": unanalyzed,
        "total_flags":        sum(1 for r in risks if r.get("risk_level") in ("HIGH", "MEDIUM", "LOW")),
        "generic_tip_count":  generic_count,   # dev metric — visible in logs
        "analyzed_at":        datetime.now().strftime("%d %B %Y, %I:%M %p"),
    }

    warning_parts = []
    if extraction_warning:
        warning_parts.append(extraction_warning)
    if unanalyzed:
        warning_parts.append(
            f"{len(unanalyzed)} clause(s) could not be analyzed within the time limit "
            f"and need manual review."
        )
        logger.warning(
            f"{len(unanalyzed)} clause(s) returned UNKNOWN — flagged in report, not dropped"
        )

    if warning_parts:
        report["warning"] = " ".join(warning_parts)

    logger.info(
        f"Report generated | doc={doc_type} | score={score} | "
        f"high={len(report['high_risks'])} | medium={len(report['medium_risks'])} | "
        f"low={len(report['low_risks'])} | safe={len(report['safe_clauses'])} | "
        f"unanalyzed={len(unanalyzed)} | "
        f"coverage={coverage['total_clauses_found']} clauses from {coverage['sections_analyzed']} sections"
    )
    return report