# import html
# import streamlit as st
# from utils.pdf_reader import extract_text_from_pdf
# from agents.pipeline import run_pipeline

# st.set_page_config(
#     page_title="LexGuard",
#     page_icon="⚖",
#     layout="wide",
#     initial_sidebar_state="collapsed"
# )

# st.markdown("""
# <style>
#     @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
#     * { font-family: 'Inter', sans-serif; }
#     .stApp { background-color: #050508; color: #e2e8f0; }

#     /* ── NAV BAR ── */
#     .navbar {
#         display: flex; align-items: center; justify-content: space-between;
#         padding: 1.2rem 2rem; border-bottom: 1px solid #0f172a;
#         background: #07070d; margin-bottom: 3rem;
#         position: sticky; top: 0; z-index: 999; margin-top: -1rem;
#     }
#     .nav-logo { font-size: 1.1rem; font-weight: 700; color: #f1f5f9; letter-spacing: 0.05em; }
#     .nav-logo span { color: #6366f1; }
#     .nav-badge {
#         font-size: 0.7rem; color: #475569; border: 1px solid #1e293b;
#         padding: 0.25rem 0.75rem; border-radius: 999px;
#         letter-spacing: 0.08em; text-transform: uppercase;
#     }

#     /* ── HERO ── */
#     .hero { max-width: 680px; margin: 0 auto 3.5rem auto; text-align: center; padding: 0 1rem; }
#     .hero-tag {
#         display: inline-block; font-size: 0.72rem; font-weight: 500;
#         letter-spacing: 0.12em; text-transform: uppercase; color: #6366f1;
#         background: #0f0f1a; border: 1px solid #1e1b4b;
#         padding: 0.3rem 1rem; border-radius: 999px; margin-bottom: 1.5rem;
#     }
#     .hero h1 { font-size: 2.8rem; font-weight: 700; color: #f8fafc; line-height: 1.2; margin-bottom: 1rem; letter-spacing: -0.02em; }
#     .hero h1 span { color: #6366f1; }
#     .hero p { font-size: 1rem; color: #64748b; line-height: 1.7; }

#     /* ── UPLOAD CARD ── */
#     .upload-card { max-width: 580px; margin: 0 auto 2rem auto; background: #0c0c14; border: 1px solid #1e293b; border-radius: 12px; padding: 2rem; }

#     /* ── PIPELINE STEPS ── */
#     .pipeline-wrap { max-width: 580px; margin: 0 auto 2.5rem auto; }
#     .step {
#         display: flex; align-items: center; gap: 0.9rem;
#         padding: 0.75rem 1rem; border-radius: 8px; margin-bottom: 0.4rem;
#         font-size: 0.88rem; color: #94a3b8; background: #0a0a12; border: 1px solid #0f172a;
#     }
#     .step.done { color: #e2e8f0; border-color: #1e293b; }
#     .step-dot { width: 8px; height: 8px; border-radius: 50%; background: #1e293b; flex-shrink: 0; }
#     .step.done .step-dot { background: #6366f1; }
#     .step-num { font-size: 0.7rem; color: #334155; min-width: 1.5rem; }

#     /* ── REPORT HEADER ── */
#     .report-header {
#         max-width: 860px; margin: 0 auto 2rem auto; padding: 1.8rem 2rem;
#         background: #0c0c14; border: 1px solid #1e293b; border-radius: 12px;
#         display: flex; justify-content: space-between; align-items: center;
#     }
#     .report-title { font-size: 0.75rem; color: #475569; text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 0.4rem; }
#     .report-doctype { font-size: 1.1rem; font-weight: 600; color: #f1f5f9; }
#     .report-meta { font-size: 0.75rem; color: #334155; margin-top: 0.3rem; }

#     /* ── SCORE BLOCK ── */
#     .score-block { text-align: right; }
#     .score-number { font-size: 2.8rem; font-weight: 700; line-height: 1; letter-spacing: -0.03em; }
#     .score-label { font-size: 0.72rem; color: #475569; text-transform: uppercase; letter-spacing: 0.1em; margin-top: 0.2rem; }

#     /* ── STAT ROW ── */
#     .stat-row { max-width: 860px; margin: 0 auto 2rem auto; display: flex; gap: 1rem; }
#     .stat-box { flex: 1; background: #0c0c14; border: 1px solid #1e293b; border-radius: 10px; padding: 1.2rem 1.5rem; }
#     .stat-val { font-size: 1.8rem; font-weight: 700; color: #f1f5f9; letter-spacing: -0.02em; }
#     .stat-lbl { font-size: 0.72rem; color: #475569; text-transform: uppercase; letter-spacing: 0.09em; margin-top: 0.25rem; }

#     /* ── VERDICT ── */
#     .verdict { max-width: 860px; margin: 0 auto 2.5rem auto; padding: 1.4rem 2rem; border-radius: 10px; border-left: 3px solid; }
#     .verdict.red   { background:#0f0505; border-color:#ef4444; }
#     .verdict.amber { background:#0d0900; border-color:#f59e0b; }
#     .verdict.green { background:#030f08; border-color:#22c55e; }
#     .verdict-label { font-size: 0.7rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.12em; margin-bottom: 0.4rem; }
#     .verdict.red   .verdict-label { color:#ef4444; }
#     .verdict.amber .verdict-label { color:#f59e0b; }
#     .verdict.green .verdict-label { color:#22c55e; }
#     .verdict-text { font-size: 1rem; font-weight: 600; color: #f1f5f9; margin-bottom: 0.3rem; }
#     .verdict-sub  { font-size: 0.875rem; color: #64748b; }

#     /* ── SECTION LABEL ── */
#     .section-label {
#         max-width: 860px; margin: 0 auto 1rem auto;
#         font-size: 0.72rem; font-weight: 600; text-transform: uppercase;
#         letter-spacing: 0.12em; color: #475569;
#         padding-bottom: 0.6rem; border-bottom: 1px solid #0f172a;
#     }

#     /* ── CLAUSE CARD ── */
#     .clause-card { max-width: 860px; margin: 0 auto 0.75rem auto; background: #0c0c14; border: 1px solid #1e293b; border-radius: 10px; padding: 1.4rem 1.6rem; }
#     .clause-top { display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.9rem; }
#     .clause-name { font-size: 0.92rem; font-weight: 600; color: #f1f5f9; }
#     .badge { font-size: 0.68rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.08em; padding: 0.25rem 0.7rem; border-radius: 4px; }
#     .badge-high   { background:#1a0505; color:#ef4444; border:1px solid #7f1d1d; }
#     .badge-medium { background:#100900; color:#f59e0b; border:1px solid #78350f; }
#     .badge-low    { background:#0d0700; color:#f97316; border:1px solid #7c2d12; }
#     .badge-safe   { background:#030f06; color:#22c55e; border:1px solid #14532d; }
#     .clause-original { font-size: 0.82rem; color: #334155; font-style: italic; border-left: 2px solid #1e293b; padding-left: 0.9rem; margin-bottom: 0.9rem; line-height: 1.6; }
#     .clause-explanation { font-size: 0.88rem; color: #94a3b8; line-height: 1.7; margin-bottom: 0.7rem; }
#     .clause-tip {
#         font-size: 0.82rem; color: #6366f1; background: #0f0f1a;
#         border: 1px solid #1e1b4b; border-radius: 6px;
#         padding: 0.6rem 0.9rem; margin-bottom: 0.7rem; line-height: 1.6;
#     }
#     .clause-tip-label { font-size: 0.68rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.1em; color: #4f46e5; margin-bottom: 0.3rem; }
#     .clause-reason { font-size: 0.8rem; color: #475569; padding-top: 0.7rem; border-top: 1px solid #0f172a; }
#     .conf-pill { font-size: 0.68rem; color: #475569; border: 1px solid #1e293b; padding: 0.2rem 0.6rem; border-radius: 999px; margin-left: 0.6rem; font-weight: 400; }

#     /* ── BUTTONS ── */
#     .stDownloadButton > button, .stButton > button {
#         background: #6366f1 !important; color: white !important; border: none !important;
#         border-radius: 8px !important; font-size: 0.85rem !important;
#         font-weight: 500 !important; padding: 0.6rem 1.5rem !important; letter-spacing: 0.02em !important;
#     }

#     /* ── HIDE DEFAULTS ── */
#     #MainMenu, footer, .stDeployButton, header[data-testid="stHeader"] { display: none !important; }
#     .block-container { padding-top: 0 !important; }
#     hr { border-color: #0f172a; }
#     [data-testid="stFileUploader"] { background: #07070d; border: 1px dashed #1e293b; border-radius: 8px; padding: 0.5rem; }
# </style>
# """, unsafe_allow_html=True)


# # ── Helpers ───────────────────────────────────────────────────
# def esc(text) -> str:
#     """Escape HTML to prevent XSS from LLM output."""
#     if text is None:
#         return ""
#     return html.escape(str(text))


# # ── Cache wrapper ─────────────────────────────────────────────
# @st.cache_data(show_spinner=False)
# def run_pipeline_cached(text: str, file_hash: str) -> dict:
#     """Cache results by file hash — same file won't re-analyze."""
#     return run_pipeline(text)


# # ── NAVBAR ────────────────────────────────────────────────────
# st.markdown("""
# <div class="navbar">
#     <div class="nav-logo">Lex<span>Guard</span></div>
#     <div class="nav-badge">AI Legal Analyzer — Beta</div>
# </div>
# """, unsafe_allow_html=True)


# # ── HERO ──────────────────────────────────────────────────────
# st.markdown("""
# <div class="hero">
#     <div class="hero-tag">Powered by LLaMA 3.3 · 70B</div>
#     <h1>Know your risks<br>before you <span>sign</span></h1>
#     <p>Upload any legal document — offer letter, rent agreement,
#     NDA, or freelance contract. Get a plain-language risk report
#     in 30 seconds. Know exactly what you're signing.</p>
# </div>
# """, unsafe_allow_html=True)


# # ── UPLOAD ────────────────────────────────────────────────────
# _, col, _ = st.columns([1, 2, 1])
# with col:
#     uploaded_file = st.file_uploader(
#         "Upload PDF",
#         type=["pdf"],
#         label_visibility="collapsed",
#         help="Maximum file size: 10MB | Maximum 50 pages"
#     )
#     if uploaded_file:
#         st.caption(f"Ready to analyze: **{uploaded_file.name}**")
#         analyze = st.button("Run Analysis", use_container_width=True)
#     else:
#         st.markdown("""
#         <style>
#         [data-testid="stFileUploaderDropzoneInstructions"] div small { display: none; }
#         </style>
#         <div style='text-align:center;color:#334155;font-size:0.8rem;padding:0.5rem 0;'>
#             PDF · Max 10MB · 50 Pages · Any Legal Document
#         </div>""", unsafe_allow_html=True)
#         analyze = False


# # ── PIPELINE ─────────────────────────────────────────────────
# if uploaded_file and analyze:

#     text, error, file_hash = extract_text_from_pdf(uploaded_file)
#     if error:
#         st.error(error)
#         st.stop()

#     steps = [
#         "Extracting document text",
#         "Detecting document type",
#         "Extracting legal clauses",
#         "Assessing clause risks",
#         "Simplifying legal language",
#         "Compiling report"
#     ]

#     pipe_placeholder = st.empty()

#     def render_steps(done_count: int) -> str:
#         step_html = '<div class="pipeline-wrap">'
#         for i, s in enumerate(steps):
#             cls = "step done" if i < done_count else "step"
#             step_html += f'<div class="{cls}"><div class="step-dot"></div><span class="step-num">{i + 1:02d}</span><span>{esc(s)}</span></div>'
#         step_html += '</div>'
#         return step_html

#     pipe_placeholder.markdown(render_steps(1), unsafe_allow_html=True)

#     with st.spinner(""):
#         # Use cache — same file won't be re-analyzed
#         final_state = run_pipeline_cached(text, file_hash or "no_hash")

#     pipe_placeholder.markdown(render_steps(6), unsafe_allow_html=True)

#     if final_state.get("error"):
#         st.error(final_state["error"])
#         st.stop()

#     report  = final_state["report"]
#     verdict = report["verdict"]
#     score   = report["risk_score"]
#     doc     = report["doc_type"]

#     score_color = "#ef4444" if score >= 7 else "#f59e0b" if score >= 4 else "#22c55e"

#     st.markdown("<br>", unsafe_allow_html=True)

#     # ── REPORT HEADER ─────────────────────────────────────────
#     header_html = '<div class="report-header">'
#     header_html += '<div>'
#     header_html += '<div class="report-title">Document analyzed</div>'
#     header_html += f'<div class="report-doctype">{esc(doc)}</div>'
#     header_html += f'<div class="report-meta">{esc(report["analyzed_at"])}</div>'
#     header_html += '</div>'
#     header_html += '<div class="score-block">'
#     header_html += f'<div class="score-number" style="color:{score_color}">{score}</div>'
#     header_html += '<div class="score-label">Risk Score / 10</div>'
#     header_html += '</div></div>'
#     st.markdown(header_html, unsafe_allow_html=True)

#     # ── STAT ROW ──────────────────────────────────────────────
#     st.markdown(f"""
#     <div class="stat-row">
#         <div class="stat-box"><div class="stat-val" style="color:#ef4444">{len(report['high_risks'])}</div><div class="stat-lbl">High Risk</div></div>
#         <div class="stat-box"><div class="stat-val" style="color:#f59e0b">{len(report['medium_risks'])}</div><div class="stat-lbl">Medium Risk</div></div>
#         <div class="stat-box"><div class="stat-val" style="color:#f97316">{len(report['low_risks'])}</div><div class="stat-lbl">Low Risk</div></div>
#         <div class="stat-box"><div class="stat-val" style="color:#22c55e">{len(report['safe_clauses'])}</div><div class="stat-lbl">Safe</div></div>
#     </div>
#     """, unsafe_allow_html=True)

#     # ── VERDICT ───────────────────────────────────────────────
#     vc_class = "red" if verdict["color"] == "red" else "amber" if verdict["color"] == "orange" else "green"
#     verdict_html = f'<div class="verdict {vc_class}">'
#     verdict_html += '<div class="verdict-label">Assessment</div>'
#     verdict_html += f'<div class="verdict-text">{esc(verdict["verdict"])}</div>'
#     verdict_html += f'<div class="verdict-sub">{esc(verdict["advice"])}</div>'
#     verdict_html += '</div>'
#     st.markdown(verdict_html, unsafe_allow_html=True)

#     # ── COVERAGE ─────────────────────────────────────────────
#     coverage = report.get("coverage", {})
#     if coverage:
#         cov_html = '<div class="stat-row">'
#         cov_html += f'<div class="stat-box"><div class="stat-val">{coverage.get("total_clauses_found", 0)}</div><div class="stat-lbl">Clauses Found</div></div>'
#         cov_html += f'<div class="stat-box"><div class="stat-val">{coverage.get("sections_analyzed", 0)}</div><div class="stat-lbl">Sections Analyzed</div></div>'
#         cov_html += f'<div class="stat-box"><div class="stat-val">{coverage.get("avg_confidence", 0)}%</div><div class="stat-lbl">Avg Confidence</div></div>'
#         cov_html += '</div>'
#         st.markdown(cov_html, unsafe_allow_html=True)

#     # ── CLAUSE RENDERER ───────────────────────────────────────
#     def render_clauses(clauses: list, badge_class: str, badge_label: str):
#         for c in clauses:
#             original = esc(c.get("original_text", ""))
#             original_html = (
#                 f'<div class="clause-original">{original[:300]}{"..." if len(original) > 300 else ""}</div>'
#                 if original else ""
#             )

#             tip = esc(c.get("negotiation_tip", ""))
#             tip_html = ""
#             if tip and tip.strip() and badge_label != "Safe":
#                 tip_html = f'<div class="clause-tip"><div class="clause-tip-label">Negotiation Tip</div>{tip}</div>'

#             reason_html = ""
#             reason = esc(c.get("reason", ""))
#             if reason and reason.strip():
#                 reason_html = f'<div class="clause-reason">{reason}</div>'

#             # Build card HTML as a single string — no f-string indentation
#             # to avoid Streamlit's markdown parser treating indented HTML as code blocks
#             card = '<div class="clause-card">'
#             card += '<div class="clause-top">'
#             card += f'<span class="clause-name">{esc(c.get("clause_type", "Unknown"))}<span class="conf-pill">{c.get("confidence", 0)}% confidence</span></span>'
#             card += f'<span class="badge {badge_class}">{badge_label}</span>'
#             card += '</div>'
#             card += original_html
#             card += f'<div class="clause-explanation">{esc(c.get("simple_explanation", ""))}</div>'
#             card += tip_html
#             card += reason_html
#             card += '</div>'
#             st.markdown(card, unsafe_allow_html=True)

#     if report["high_risks"]:
#         st.markdown('<div class="section-label">High Risk</div>', unsafe_allow_html=True)
#         render_clauses(report["high_risks"], "badge-high", "High")

#     if report["medium_risks"]:
#         st.markdown('<div class="section-label">Medium Risk</div>', unsafe_allow_html=True)
#         render_clauses(report["medium_risks"], "badge-medium", "Medium")

#     if report["low_risks"]:
#         st.markdown('<div class="section-label">Low Risk</div>', unsafe_allow_html=True)
#         render_clauses(report["low_risks"], "badge-low", "Low")

#     if report["safe_clauses"]:
#         st.markdown('<div class="section-label">Safe Clauses</div>', unsafe_allow_html=True)
#         render_clauses(report["safe_clauses"], "badge-safe", "Safe")

#     st.markdown("<br>", unsafe_allow_html=True)

#     # ── DOWNLOAD REPORT ──────────────────────────────────────
#     def _build_download_section(label: str, clauses: list) -> str:
#         """Build a text section for the downloadable report."""
#         section = f"\n{label} ({len(clauses)} clauses)\n{'-' * 60}\n"
#         for i, r in enumerate(clauses, 1):
#             section += f"\n{i}. {r.get('clause_type', 'Unknown')} — {r.get('confidence', 0)}% confidence\n"
#             original = r.get("original_text", "")
#             if original:
#                 section += f"   Original : {original[:200]}\n"
#             section += f"   Meaning  : {r.get('simple_explanation', '')}\n"
#             tip = r.get("negotiation_tip", "")
#             if tip and tip.strip():
#                 section += f"   Tip      : {tip}\n"
#         return section

#     report_text = f"""LEXGUARD RISK REPORT
# {'=' * 60}
# Document  : {doc}
# Score     : {score} / 10
# Verdict   : {verdict['verdict']}
# Analyzed  : {report['analyzed_at']}
# {'=' * 60}
# """
#     report_text += _build_download_section("HIGH RISK", report["high_risks"])
#     report_text += _build_download_section("MEDIUM RISK", report["medium_risks"])
#     report_text += _build_download_section("LOW RISK", report["low_risks"])

#     report_text += f"\nSAFE ({len(report['safe_clauses'])} clauses)\n{'-' * 60}\n"
#     for r in report["safe_clauses"]:
#         report_text += f"- {r.get('clause_type', 'Unknown')}\n"

#     report_text += f"\n{'=' * 60}\nDisclaimer: Informational only. Not legal advice.\n{'=' * 60}\n"

#     _, dc, _ = st.columns([1, 2, 1])
#     with dc:
#         st.download_button(
#             "Download Report",
#             data=report_text,
#             file_name=f"lexguard_{doc.lower().replace(' ', '_')}.txt",
#             mime="text/plain",
#             use_container_width=True
#         )

#     st.markdown("""
#     <div style='text-align:center;color:#1e293b;font-size:0.75rem;margin-top:3rem;padding-bottom:2rem;'>
#         LexGuard — Informational use only. Not a substitute for legal advice.
#     </div>
#     """, unsafe_allow_html=True)
import html
import re
import streamlit as st
from utils.pdf_reader import extract_text_from_pdf
from agents.pipeline import run_pipeline

st.set_page_config(
    page_title="LexGuard",
    page_icon="⚖",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    * { font-family: 'Inter', sans-serif; }
    .stApp { background-color: #050508; color: #e2e8f0; }

    /* ── NAV BAR ── */
    .navbar {
        display: flex; align-items: center; justify-content: space-between;
        padding: 1.2rem 2rem; border-bottom: 1px solid #0f172a;
        background: #07070d; margin-bottom: 3rem;
        position: sticky; top: 0; z-index: 999; margin-top: -1rem;
    }
    .nav-logo { font-size: 1.1rem; font-weight: 700; color: #f1f5f9; letter-spacing: 0.05em; }
    .nav-logo span { color: #6366f1; }
    .nav-badge {
        font-size: 0.7rem; color: #475569; border: 1px solid #1e293b;
        padding: 0.25rem 0.75rem; border-radius: 999px;
        letter-spacing: 0.08em; text-transform: uppercase;
    }

    /* ── HERO ── */
    .hero { max-width: 680px; margin: 0 auto 3.5rem auto; text-align: center; padding: 0 1rem; }
    .hero-tag {
        display: inline-block; font-size: 0.72rem; font-weight: 500;
        letter-spacing: 0.12em; text-transform: uppercase; color: #6366f1;
        background: #0f0f1a; border: 1px solid #1e1b4b;
        padding: 0.3rem 1rem; border-radius: 999px; margin-bottom: 1.5rem;
    }
    .hero h1 { font-size: 2.8rem; font-weight: 700; color: #f8fafc; line-height: 1.2; margin-bottom: 1rem; letter-spacing: -0.02em; }
    .hero h1 span { color: #6366f1; }
    .hero p { font-size: 1rem; color: #64748b; line-height: 1.7; }

    /* ── UPLOAD CARD ── */
    .upload-card { max-width: 580px; margin: 0 auto 2rem auto; background: #0c0c14; border: 1px solid #1e293b; border-radius: 12px; padding: 2rem; }

    /* ── PIPELINE STEPS ── */
    .pipeline-wrap { max-width: 580px; margin: 0 auto 2.5rem auto; }
    .step {
        display: flex; align-items: center; gap: 0.9rem;
        padding: 0.75rem 1rem; border-radius: 8px; margin-bottom: 0.4rem;
        font-size: 0.88rem; color: #94a3b8; background: #0a0a12; border: 1px solid #0f172a;
    }
    .step.done { color: #e2e8f0; border-color: #1e293b; }
    .step-dot { width: 8px; height: 8px; border-radius: 50%; background: #1e293b; flex-shrink: 0; }
    .step.done .step-dot { background: #6366f1; }
    .step-num { font-size: 0.7rem; color: #334155; min-width: 1.5rem; }

    /* ── REPORT HEADER ── */
    .report-header {
        max-width: 860px; margin: 0 auto 2rem auto; padding: 1.8rem 2rem;
        background: #0c0c14; border: 1px solid #1e293b; border-radius: 12px;
        display: flex; justify-content: space-between; align-items: center;
    }
    .report-title { font-size: 0.75rem; color: #475569; text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 0.4rem; }
    .report-doctype { font-size: 1.1rem; font-weight: 600; color: #f1f5f9; }
    .report-meta { font-size: 0.75rem; color: #334155; margin-top: 0.3rem; }

    /* ── SCORE BLOCK ── */
    .score-block { text-align: right; }
    .score-number { font-size: 2.8rem; font-weight: 700; line-height: 1; letter-spacing: -0.03em; }
    .score-label { font-size: 0.72rem; color: #475569; text-transform: uppercase; letter-spacing: 0.1em; margin-top: 0.2rem; }

    /* ── STAT ROW ── */
    .stat-row { max-width: 860px; margin: 0 auto 2rem auto; display: flex; gap: 1rem; }
    .stat-box { flex: 1; background: #0c0c14; border: 1px solid #1e293b; border-radius: 10px; padding: 1.2rem 1.5rem; }
    .stat-val { font-size: 1.8rem; font-weight: 700; color: #f1f5f9; letter-spacing: -0.02em; }
    .stat-lbl { font-size: 0.72rem; color: #475569; text-transform: uppercase; letter-spacing: 0.09em; margin-top: 0.25rem; }

    /* ── VERDICT ── */
    .verdict { max-width: 860px; margin: 0 auto 1.5rem auto; padding: 1.4rem 2rem; border-radius: 10px; border-left: 3px solid; }
    .verdict.red   { background:#0f0505; border-color:#ef4444; }
    .verdict.amber { background:#0d0900; border-color:#f59e0b; }
    .verdict.green { background:#030f08; border-color:#22c55e; }
    .verdict-label { font-size: 0.7rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.12em; margin-bottom: 0.4rem; }
    .verdict.red   .verdict-label { color:#ef4444; }
    .verdict.amber .verdict-label { color:#f59e0b; }
    .verdict.green .verdict-label { color:#22c55e; }
    .verdict-text { font-size: 1rem; font-weight: 600; color: #f1f5f9; margin-bottom: 0.3rem; }
    .verdict-sub  { font-size: 0.875rem; color: #64748b; }

    /* ── SCORE EXPLANATION ── */
    .score-explanation {
        max-width: 860px; margin: 0 auto 1.5rem auto;
        font-size: 0.8rem; color: #475569; line-height: 1.6;
        padding: 0.8rem 1.2rem; background: #0a0a12;
        border: 1px solid #0f172a; border-radius: 8px;
    }

    /* ── TOP PRIORITIES ── */
    .priorities-wrap { max-width: 860px; margin: 0 auto 2rem auto; }
    .priority-card {
        display: flex; gap: 1rem; align-items: flex-start;
        padding: 1rem 1.4rem; background: #0c0c14;
        border: 1px solid #1e1b4b; border-radius: 10px;
        margin-bottom: 0.6rem;
    }
    .priority-num {
        font-size: 1.4rem; font-weight: 700; color: #6366f1;
        min-width: 2rem; line-height: 1.2;
    }
    .priority-body { flex: 1; }
    .priority-type { font-size: 0.88rem; font-weight: 600; color: #f1f5f9; margin-bottom: 0.3rem; }
    .priority-tip  { font-size: 0.82rem; color: #94a3b8; line-height: 1.6; }

    /* ── WARNING BANNER ── */
    .warn-banner {
        max-width: 860px; margin: 0 auto 1.5rem auto; padding: 1rem 1.5rem;
        border-radius: 10px; border-left: 3px solid #f59e0b;
        background:#0d0900; color:#fbbf24; font-size: 0.85rem; line-height: 1.6;
    }

    /* ── SECTION LABEL ── */
    .section-label {
        max-width: 860px; margin: 0 auto 1rem auto;
        font-size: 0.72rem; font-weight: 600; text-transform: uppercase;
        letter-spacing: 0.12em; color: #475569;
        padding-bottom: 0.6rem; border-bottom: 1px solid #0f172a;
    }

    /* ── CLAUSE CARD ── */
    .clause-card { max-width: 860px; margin: 0 auto 0.75rem auto; background: #0c0c14; border: 1px solid #1e293b; border-radius: 10px; padding: 1.4rem 1.6rem; }
    .clause-top { display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.9rem; }
    .clause-name { font-size: 0.92rem; font-weight: 600; color: #f1f5f9; }
    .badge { font-size: 0.68rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.08em; padding: 0.25rem 0.7rem; border-radius: 4px; }
    .badge-high   { background:#1a0505; color:#ef4444; border:1px solid #7f1d1d; }
    .badge-medium { background:#100900; color:#f59e0b; border:1px solid #78350f; }
    .badge-low    { background:#0d0700; color:#f97316; border:1px solid #7c2d12; }
    .badge-safe   { background:#030f06; color:#22c55e; border:1px solid #14532d; }
    .badge-unknown { background:#0a0a12; color:#94a3b8; border:1px solid #1e293b; }
    .clause-original { font-size: 0.82rem; color: #334155; font-style: italic; border-left: 2px solid #1e293b; padding-left: 0.9rem; margin-bottom: 0.9rem; line-height: 1.6; }
    .clause-explanation { font-size: 0.88rem; color: #94a3b8; line-height: 1.7; margin-bottom: 0.7rem; }
    .clause-tip {
        font-size: 0.82rem; color: #6366f1; background: #0f0f1a;
        border: 1px solid #1e1b4b; border-radius: 6px;
        padding: 0.6rem 0.9rem; margin-bottom: 0.7rem; line-height: 1.6;
    }
    .clause-tip-label { font-size: 0.68rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.1em; color: #4f46e5; margin-bottom: 0.3rem; }
    .clause-reason { font-size: 0.8rem; color: #475569; padding-top: 0.7rem; border-top: 1px solid #0f172a; }
    .conf-pill { font-size: 0.68rem; color: #475569; border: 1px solid #1e293b; padding: 0.2rem 0.6rem; border-radius: 999px; margin-left: 0.6rem; font-weight: 400; }

    /* ── SUGGESTED REPLACEMENT ── */
    .replacement-block {
        margin-top: 0.7rem; padding: 0.7rem 0.9rem;
        background: #030f08; border: 1px solid #14532d;
        border-radius: 6px; font-size: 0.78rem;
        color: #4ade80; line-height: 1.6; font-family: monospace;
    }
    .replacement-label {
        font-size: 0.65rem; font-weight: 600; text-transform: uppercase;
        letter-spacing: 0.1em; color: #22c55e; margin-bottom: 0.3rem;
        font-family: 'Inter', sans-serif;
    }

    /* ── FINANCIAL IMPACT ── */
    .financial-impact {
        font-size: 0.8rem; color: #f59e0b; background: #0d0900;
        border: 1px solid #78350f; border-radius: 6px;
        padding: 0.5rem 0.8rem; margin-bottom: 0.7rem; line-height: 1.5;
    }
    .financial-label { font-size: 0.65rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.1em; color: #d97706; margin-bottom: 0.2rem; }

    /* ── BUTTONS ── */
    .stDownloadButton > button, .stButton > button {
        background: #6366f1 !important; color: white !important; border: none !important;
        border-radius: 8px !important; font-size: 0.85rem !important;
        font-weight: 500 !important; padding: 0.6rem 1.5rem !important; letter-spacing: 0.02em !important;
    }

    /* ── HIDE DEFAULTS ── */
    #MainMenu, footer, .stDeployButton, header[data-testid="stHeader"] { display: none !important; }
    .block-container { padding-top: 0 !important; }
    hr { border-color: #0f172a; }
    [data-testid="stFileUploader"] { background: #07070d; border: 1px dashed #1e293b; border-radius: 8px; padding: 0.5rem; }
</style>
""", unsafe_allow_html=True)


# ── Helpers ───────────────────────────────────────────────────
def esc(text) -> str:
    if text is None:
        return ""
    return html.escape(str(text))


def _truncate_at_sentence(text: str, soft_limit: int) -> tuple[str, bool]:
    if not text or len(text) <= soft_limit:
        return text, False
    window = text[soft_limit:soft_limit + 200]
    match = re.search(r'[.!?]', window)
    if match:
        cut = soft_limit + match.end()
        return text[:cut].strip(), len(text) > cut
    return text, False


# ── Cache wrapper ─────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def run_pipeline_cached(text: str, file_hash: str) -> dict:
    return run_pipeline(text)


# ── NAVBAR ────────────────────────────────────────────────────
st.markdown("""
<div class="navbar">
    <div class="nav-logo">Lex<span>Guard</span></div>
    <div class="nav-badge">AI Legal Analyzer — Beta</div>
</div>
""", unsafe_allow_html=True)


# ── HERO ──────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
    <div class="hero-tag">Powered by LLaMA 3.3 · 70B</div>
    <h1>Know your risks<br>before you <span>sign</span></h1>
    <p>Upload any legal document — offer letter, rent agreement,
    NDA, or freelance contract. Get a plain-language risk report
    under minutes. Know exactly what you're signing.</p>
</div>
""", unsafe_allow_html=True)


# ── UPLOAD ────────────────────────────────────────────────────
_, col, _ = st.columns([1, 2, 1])
with col:
    uploaded_file = st.file_uploader(
        "Upload PDF",
        type=["pdf"],
        label_visibility="collapsed",
        help="Maximum file size: 10MB | Maximum 50 pages"
    )
    if uploaded_file:
        st.caption(f"Ready to analyze: **{uploaded_file.name}**")
        analyze = st.button("Run Analysis", use_container_width=True)
    else:
        st.markdown("""
        <style>
        [data-testid="stFileUploaderDropzoneInstructions"] div small { display: none; }
        </style>
        <div style='text-align:center;color:#334155;font-size:0.8rem;padding:0.5rem 0;'>
            PDF · Max 10MB · 50 Pages · Any Legal Document
        </div>""", unsafe_allow_html=True)
        analyze = False


# ── PIPELINE ─────────────────────────────────────────────────
if uploaded_file and analyze:

    text, error, file_hash, extraction_warning = extract_text_from_pdf(uploaded_file)
    if error:
        st.error(error)
        st.stop()

    if extraction_warning:
        st.markdown(
            f'<div class="warn-banner">⚠ {esc(extraction_warning)}</div>',
            unsafe_allow_html=True
        )

    steps = [
        "Extracting document text",
        "Detecting document type",
        "Extracting legal clauses",
        "Assessing clause risks",
        "Simplifying legal language",
        "Compiling report"
    ]

    pipe_placeholder = st.empty()

    def render_steps(done_count: int) -> str:
        step_html = '<div class="pipeline-wrap">'
        for i, s in enumerate(steps):
            cls = "step done" if i < done_count else "step"
            step_html += f'<div class="{cls}"><div class="step-dot"></div><span class="step-num">{i + 1:02d}</span><span>{esc(s)}</span></div>'
        step_html += '</div>'
        return step_html

    pipe_placeholder.markdown(render_steps(1), unsafe_allow_html=True)

    with st.spinner(""):
        final_state = run_pipeline_cached(text, file_hash or "no_hash")

    pipe_placeholder.markdown(render_steps(6), unsafe_allow_html=True)

    if final_state.get("error"):
        st.error(final_state["error"])
        st.stop()

    report  = final_state["report"]
    verdict = report["verdict"]
    score   = report["risk_score"]
    doc     = report["doc_type"]

    _color_map  = {"red": "#ef4444", "orange": "#f59e0b", "green": "#22c55e"}
    score_color = _color_map.get(verdict.get("color"), "#94a3b8")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── REPORT HEADER ─────────────────────────────────────────
    header_html = '<div class="report-header">'
    header_html += '<div>'
    header_html += '<div class="report-title">Document analyzed</div>'
    header_html += f'<div class="report-doctype">{esc(doc)}</div>'
    header_html += f'<div class="report-meta">{esc(report["analyzed_at"])}</div>'
    header_html += '</div>'
    header_html += '<div class="score-block">'
    header_html += f'<div class="score-number" style="color:{score_color}">{score}</div>'
    header_html += '<div class="score-label">Risk Score / 10</div>'
    header_html += '</div></div>'
    st.markdown(header_html, unsafe_allow_html=True)

    # ── STAT ROW ──────────────────────────────────────────────
    st.markdown(f"""
    <div class="stat-row">
        <div class="stat-box"><div class="stat-val" style="color:#ef4444">{len(report['high_risks'])}</div><div class="stat-lbl">High Risk</div></div>
        <div class="stat-box"><div class="stat-val" style="color:#f59e0b">{len(report['medium_risks'])}</div><div class="stat-lbl">Medium Risk</div></div>
        <div class="stat-box"><div class="stat-val" style="color:#f97316">{len(report['low_risks'])}</div><div class="stat-lbl">Low Risk</div></div>
        <div class="stat-box"><div class="stat-val" style="color:#22c55e">{len(report['safe_clauses'])}</div><div class="stat-lbl">Safe</div></div>
    </div>
    """, unsafe_allow_html=True)

    # ── VERDICT ───────────────────────────────────────────────
    vc_class = "red" if verdict["color"] == "red" else "amber" if verdict["color"] == "orange" else "green"
    verdict_html = f'<div class="verdict {vc_class}">'
    verdict_html += '<div class="verdict-label">Assessment</div>'
    verdict_html += f'<div class="verdict-text">{esc(verdict["verdict"])}</div>'
    verdict_html += f'<div class="verdict-sub">{esc(verdict["advice"])}</div>'
    verdict_html += '</div>'
    st.markdown(verdict_html, unsafe_allow_html=True)

    # ── SCORE EXPLANATION ─────────────────────────────────────
    # NEW: shows how the score was calculated — no more mystery number
    score_explanation = report.get("score_explanation", "")
    if score_explanation:
        st.markdown(
            f'<div class="score-explanation">ℹ {esc(score_explanation)}</div>',
            unsafe_allow_html=True
        )

    # ── TOP 3 PRIORITIES ──────────────────────────────────────
    # NEW: most actionable clauses surfaced before the full list
    top_priorities = report.get("top_priorities", [])
    if top_priorities:
        st.markdown(
            '<div class="section-label">Top Priorities — Negotiate These First</div>',
            unsafe_allow_html=True
        )
        priorities_html = '<div class="priorities-wrap">'
        for i, p in enumerate(top_priorities, 1):
            badge_cls = "badge-high" if p.get("risk_level") == "HIGH" else "badge-medium"
            priorities_html += '<div class="priority-card">'
            priorities_html += f'<div class="priority-num">{i}</div>'
            priorities_html += '<div class="priority-body">'
            priorities_html += (
                f'<div class="priority-type">'
                f'{esc(p.get("clause_type", ""))}'
                f'&nbsp;<span class="badge {badge_cls}" style="font-size:0.6rem;padding:0.15rem 0.5rem;">'
                f'{esc(p.get("risk_level", ""))}</span></div>'
            )
            priorities_html += f'<div class="priority-tip">{esc(p.get("negotiation_tip", ""))}</div>'
            priorities_html += '</div></div>'
        priorities_html += '</div>'
        st.markdown(priorities_html, unsafe_allow_html=True)

    # ── UNANALYZED / WARNING BANNER ───────────────────────────
    unanalyzed = report.get("unanalyzed_clauses", [])
    if unanalyzed or report.get("warning"):
        st.markdown(
            f'<div class="warn-banner">⚠ {esc(report.get("warning", f"{len(unanalyzed)} clause(s) could not be reliably analyzed."))} '
            f'{"These are listed below under &quot;Needs Manual Review&quot; — please read them yourself or consult a lawyer." if unanalyzed else ""}</div>',
            unsafe_allow_html=True
        )

    # ── COVERAGE ─────────────────────────────────────────────
    coverage = report.get("coverage", {})
    if coverage:
        cov_html = '<div class="stat-row">'
        cov_html += f'<div class="stat-box"><div class="stat-val">{coverage.get("total_clauses_found", 0)}</div><div class="stat-lbl">Clauses Found</div></div>'
        cov_html += f'<div class="stat-box"><div class="stat-val">{coverage.get("sections_analyzed", 0)}</div><div class="stat-lbl">Sections Analyzed</div></div>'
        cov_html += f'<div class="stat-box"><div class="stat-val">{coverage.get("avg_confidence", 0)}%</div><div class="stat-lbl">Avg Confidence</div></div>'
        cov_html += '</div>'
        st.markdown(cov_html, unsafe_allow_html=True)

    # ── CLAUSE RENDERER ───────────────────────────────────────
    def render_clauses(clauses: list, badge_class: str, badge_label: str):
        for c in clauses:
            raw_original = c.get("original_text", "")
            original     = esc(raw_original)
            shown, was_cut = _truncate_at_sentence(original, 300)
            original_html = (
                f'<div class="clause-original">{shown}{"..." if was_cut else ""}</div>'
                if original else ""
            )

            tip      = esc(c.get("negotiation_tip", ""))
            tip_html = ""
            if tip and tip.strip() and badge_label not in ("Safe", "Unknown"):
                tip_html = f'<div class="clause-tip"><div class="clause-tip-label">Negotiation Tip</div>{tip}</div>'

            # NEW: suggested replacement language for HIGH/MEDIUM clauses
            replacement      = esc(c.get("suggested_replacement", ""))
            replacement_html = ""
            if replacement and replacement.strip() and badge_label in ("High", "Medium"):
                replacement_html = (
                    f'<div class="replacement-block">'
                    f'<div class="replacement-label">✦ Suggested Replacement Language</div>'
                    f'{replacement}'
                    f'</div>'
                )

            # NEW: financial impact for HIGH/MEDIUM clauses
            financial      = esc(c.get("financial_impact", ""))
            financial_html = ""
            if financial and financial.strip() and badge_label in ("High", "Medium"):
                financial_html = (
                    f'<div class="financial-impact">'
                    f'<div class="financial-label">₹ Financial Impact</div>'
                    f'{financial}'
                    f'</div>'
                )

            reason_html = ""
            reason = esc(c.get("reason", ""))
            if reason and reason.strip():
                reason_html = f'<div class="clause-reason">{reason}</div>'

            conf = c.get("confidence")
            conf_display = f"{conf}%" if isinstance(conf, (int, float)) else "—"

            card  = '<div class="clause-card">'
            card += '<div class="clause-top">'
            card += f'<span class="clause-name">{esc(c.get("clause_type", "Unknown"))}<span class="conf-pill">{conf_display} confidence</span></span>'
            card += f'<span class="badge {badge_class}">{badge_label}</span>'
            card += '</div>'
            card += original_html
            card += f'<div class="clause-explanation">{esc(c.get("simple_explanation", ""))}</div>'
            card += financial_html
            card += tip_html
            card += replacement_html
            card += reason_html
            card += '</div>'
            st.markdown(card, unsafe_allow_html=True)

    if report["high_risks"]:
        st.markdown('<div class="section-label">High Risk</div>', unsafe_allow_html=True)
        render_clauses(report["high_risks"], "badge-high", "High")

    if report["medium_risks"]:
        st.markdown('<div class="section-label">Medium Risk</div>', unsafe_allow_html=True)
        render_clauses(report["medium_risks"], "badge-medium", "Medium")

    if report["low_risks"]:
        st.markdown('<div class="section-label">Low Risk</div>', unsafe_allow_html=True)
        render_clauses(report["low_risks"], "badge-low", "Low")

    if report["safe_clauses"]:
        st.markdown('<div class="section-label">Safe Clauses</div>', unsafe_allow_html=True)
        render_clauses(report["safe_clauses"], "badge-safe", "Safe")

    if unanalyzed:
        st.markdown('<div class="section-label">Needs Manual Review</div>', unsafe_allow_html=True)
        render_clauses(unanalyzed, "badge-unknown", "Unknown")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── DOWNLOAD REPORT ──────────────────────────────────────
    def _build_download_section(label: str, clauses: list) -> str:
        section = f"\n{label} ({len(clauses)} clauses)\n{'-' * 60}\n"
        for i, r in enumerate(clauses, 1):
            conf = r.get("confidence")
            conf_str = f"{conf}%" if isinstance(conf, (int, float)) else "unanalyzed"
            section += f"\n{i}. {r.get('clause_type', 'Unknown')} — {conf_str} confidence\n"
            original = r.get("original_text", "")
            if original:
                shown, was_cut = _truncate_at_sentence(original, 300)
                section += f"   Original : {shown}{'...' if was_cut else ''}\n"
            section += f"   Meaning  : {r.get('simple_explanation', '')}\n"
            if r.get("financial_impact"):
                section += f"   Financial: {r.get('financial_impact', '')}\n"
            tip = r.get("negotiation_tip", "")
            if tip and tip.strip():
                section += f"   Tip      : {tip}\n"
            replacement = r.get("suggested_replacement", "")
            if replacement and replacement.strip():
                section += f"   Replacement: {replacement}\n"
        return section

    report_text  = f"LEXGUARD RISK REPORT\n{'=' * 60}\n"
    report_text += f"Document  : {doc}\n"
    report_text += f"Score     : {score} / 10\n"
    report_text += f"Verdict   : {verdict['verdict']}\n"
    report_text += f"Analyzed  : {report['analyzed_at']}\n"
    report_text += f"{'=' * 60}\n"

    if report.get("score_explanation"):
        report_text += f"\nHow this score was calculated:\n{report['score_explanation']}\n"

    if top_priorities:
        report_text += f"\nTOP {len(top_priorities)} PRIORITIES — NEGOTIATE THESE FIRST\n{'-' * 60}\n"
        for i, p in enumerate(top_priorities, 1):
            report_text += f"{i}. [{p.get('risk_level')}] {p.get('clause_type', '')}\n"
            report_text += f"   → {p.get('negotiation_tip', '')}\n"

    if extraction_warning:
        report_text += f"\n⚠ NOTE: {extraction_warning}\n"
    if report.get("warning"):
        report_text += f"\n⚠ NOTE: {report['warning']}\n"

    report_text += _build_download_section("HIGH RISK", report["high_risks"])
    report_text += _build_download_section("MEDIUM RISK", report["medium_risks"])
    report_text += _build_download_section("LOW RISK", report["low_risks"])

    report_text += f"\nSAFE ({len(report['safe_clauses'])} clauses)\n{'-' * 60}\n"
    for r in report["safe_clauses"]:
        report_text += f"- {r.get('clause_type', 'Unknown')}\n"

    if unanalyzed:
        report_text += _build_download_section("NEEDS MANUAL REVIEW", unanalyzed)

    report_text += f"\n{'=' * 60}\nDisclaimer: Informational only. Not legal advice.\n{'=' * 60}\n"

    _, dc, _ = st.columns([1, 2, 1])
    with dc:
        st.download_button(
            "Download Report",
            data=report_text,
            file_name=f"lexguard_{doc.lower().replace(' ', '_')}.txt",
            mime="text/plain",
            use_container_width=True
        )

    st.markdown("""
    <div style='text-align:center;color:#1e293b;font-size:0.75rem;margin-top:3rem;padding-bottom:2rem;'>
        LexGuard — Informational use only. Not a substitute for legal advice.
    </div>
    """, unsafe_allow_html=True)