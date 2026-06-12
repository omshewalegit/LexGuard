# # from datetime import datetime


# # SCORE_MAP   = {"HIGH": 9, "MEDIUM": 5, "LOW": 2, "SAFE": 0, "UNKNOWN": 3}
# # WEIGHT_MAP  = {"HIGH": 3, "MEDIUM": 2, "LOW": 1, "SAFE": 0, "UNKNOWN": 1}


# # def calculate_risk_score(risks: list) -> float:
# #     if not risks:
# #         return 0.0

# #     total_score  = 0.0
# #     total_weight = 0.0

# #     for risk in risks:
# #         level      = risk.get("risk_level", "UNKNOWN").upper()
# #         confidence = risk.get("confidence", 50) / 100
# #         score      = SCORE_MAP.get(level, 3)
# #         weight     = WEIGHT_MAP.get(level, 1)

# #         total_score  += score * weight * confidence
# #         total_weight += weight

# #     if total_weight == 0:
# #         return 0.0

# #     return round(min(10.0, total_score / total_weight), 1)


# # def get_verdict(score: float) -> dict:
# #     if score >= 7.0:
# #         return {
# #             "verdict": "Do Not Sign — Negotiate First",
# #             "color":   "red",
# #             "advice":  "Multiple high-risk clauses detected. Request amendments before signing."
# #         }
# #     elif score >= 4.0:
# #         return {
# #             "verdict": "Review Carefully Before Signing",
# #             "color":   "orange",
# #             "advice":  "Some clauses require attention. Negotiate flagged points where possible."
# #         }
# #     else:
# #         return {
# #             "verdict": "Relatively Safe to Sign",
# #             "color":   "green",
# #             "advice":  "No major red flags detected. Standard clauses observed."
# #         }


# # def generate_report(doc_type: str, risks: list) -> dict:
# #     score   = calculate_risk_score(risks)
# #     verdict = get_verdict(score)

# #     return {
# #         "doc_type":      doc_type.replace("_", " ").title(),
# #         "risk_score":    score,
# #         "verdict":       verdict,
# #         "high_risks":    [r for r in risks if r.get("risk_level") == "HIGH"],
# #         "medium_risks":  [r for r in risks if r.get("risk_level") == "MEDIUM"],
# #         "low_risks":     [r for r in risks if r.get("risk_level") == "LOW"],
# #         "safe_clauses":  [r for r in risks if r.get("risk_level") == "SAFE"],
# #         "total_flags":   sum(1 for r in risks if r.get("risk_level") in ["HIGH", "MEDIUM", "LOW"]),
# #         "analyzed_at":   datetime.now().strftime("%d %B %Y, %I:%M %p")
# #     }

# from datetime import datetime
# from utils.logger import get_logger

# logger = get_logger("reporter")

# SCORE_MAP  = {"HIGH": 9, "MEDIUM": 5, "LOW": 2, "SAFE": 0, "UNKNOWN": 3}
# WEIGHT_MAP = {"HIGH": 3, "MEDIUM": 2, "LOW": 1, "SAFE": 0, "UNKNOWN": 1}


# def calculate_risk_score(risks: list) -> float:
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
#     if score >= 7.0:
#         return {
#             "verdict": "Do Not Sign — Negotiate First",
#             "color":   "red",
#             "advice":  "Multiple high-risk clauses detected. Request amendments before signing."
#         }
#     elif score >= 4.0:
#         return {
#             "verdict": "Review Carefully Before Signing",
#             "color":   "orange",
#             "advice":  "Some clauses require attention. Negotiate flagged points where possible."
#         }
#     else:
#         return {
#             "verdict": "Relatively Safe to Sign",
#             "color":   "green",
#             "advice":  "No major red flags detected. Standard clauses observed."
#         }


# def generate_report(doc_type: str, risks: list) -> dict:
#     score   = calculate_risk_score(risks)
#     verdict = get_verdict(score)

#     report = {
#         "doc_type":      doc_type.replace("_", " ").title(),
#         "risk_score":    score,
#         "verdict":       verdict,
#         "high_risks":    [r for r in risks if r.get("risk_level") == "HIGH"],
#         "medium_risks":  [r for r in risks if r.get("risk_level") == "MEDIUM"],
#         "low_risks":     [r for r in risks if r.get("risk_level") == "LOW"],
#         "safe_clauses":  [r for r in risks if r.get("risk_level") == "SAFE"],
#         "total_flags":   sum(1 for r in risks if r.get("risk_level") in ["HIGH", "MEDIUM", "LOW"]),
#         "analyzed_at":   datetime.now().strftime("%d %B %Y, %I:%M %p")
#     }

#     logger.info(
#         f"Report generated | doc={doc_type} | score={score} | "
#         f"high={len(report['high_risks'])} | medium={len(report['medium_risks'])}"
#     )
#     return report

from datetime import datetime
from utils.logger import get_logger

logger = get_logger("reporter")

SCORE_MAP  = {"HIGH": 9, "MEDIUM": 5, "LOW": 2, "SAFE": 0, "UNKNOWN": 3}
WEIGHT_MAP = {"HIGH": 3, "MEDIUM": 2, "LOW": 1, "SAFE": 0, "UNKNOWN": 1}


def calculate_risk_score(risks: list) -> float:
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
    if score >= 7.0:
        return {
            "verdict": "Do Not Sign — Negotiate First",
            "color":   "red",
            "advice":  "Multiple high-risk clauses detected. Request amendments before signing."
        }
    elif score >= 4.0:
        return {
            "verdict": "Review Carefully Before Signing",
            "color":   "orange",
            "advice":  "Some clauses require attention. Negotiate flagged points where possible."
        }
    else:
        return {
            "verdict": "Relatively Safe to Sign",
            "color":   "green",
            "advice":  "No major red flags detected. Standard clauses observed."
        }


def generate_report(doc_type: str, risks: list) -> dict:
    score   = calculate_risk_score(risks)
    verdict = get_verdict(score)

    report = {
        "doc_type":      doc_type.replace("_", " ").title(),
        "risk_score":    score,
        "verdict":       verdict,
        "high_risks":    [r for r in risks if r.get("risk_level") == "HIGH"],
        "medium_risks":  [r for r in risks if r.get("risk_level") == "MEDIUM"],
        "low_risks":     [r for r in risks if r.get("risk_level") == "LOW"],
        "safe_clauses":  [r for r in risks if r.get("risk_level") == "SAFE"],
        "total_flags":   sum(1 for r in risks if r.get("risk_level") in ["HIGH", "MEDIUM", "LOW"]),
        "analyzed_at":   datetime.now().strftime("%d %B %Y, %I:%M %p")
    }

    logger.info(
        f"Report generated | doc={doc_type} | score={score} | "
        f"high={len(report['high_risks'])} | medium={len(report['medium_risks'])}"
    )
    return report