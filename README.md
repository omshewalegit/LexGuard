<div align="center">

<br/>

```
  ██╗     ███████╗██╗  ██╗ ██████╗ ██╗   ██╗ █████╗ ██████╗ ██████╗
  ██║     ██╔════╝╚██╗██╔╝██╔════╝ ██║   ██║██╔══██╗██╔══██╗██╔══██╗
  ██║     █████╗   ╚███╔╝ ██║  ███╗██║   ██║███████║██████╔╝██║  ██║
  ██║     ██╔══╝   ██╔██╗ ██║   ██║██║   ██║██╔══██║██╔══██╗██║  ██║
  ███████╗███████╗██╔╝ ██╗╚██████╔╝╚██████╔╝██║  ██║██║  ██║██████╔╝
  ╚══════╝╚══════╝╚═╝  ╚═╝ ╚═════╝  ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═════╝
```

**Upload any legal document. Get a plain-language risk report in under a minute.**

[![Python](https://img.shields.io/badge/Python-3.10+-3B82F6?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![LangGraph](https://img.shields.io/badge/LangGraph-Multi--Agent-7C3AED?style=flat-square)](https://github.com/langchain-ai/langgraph)
[![Groq](https://img.shields.io/badge/Groq-LLaMA_3.3_70B-F59E0B?style=flat-square)](https://groq.com)
[![Streamlit](https://img.shields.io/badge/Streamlit-UI-EF4444?style=flat-square)](https://streamlit.io)
[![Pytest](https://img.shields.io/badge/Pytest-Tested-22C55E?style=flat-square)](https://pytest.org)
[![License](https://img.shields.io/badge/License-MIT-6366F1?style=flat-square)](LICENSE)

</div>

---

## The Problem

Every year, millions of people sign offer letters, rent agreements, NDAs, and freelance contracts without fully understanding what they're agreeing to. Hidden clauses can lead to financial losses, unfair obligations, restricted rights, or costly legal disputes. Professional legal review is expensive, and generic AI tools often provide vague, unreliable advice.

**LexGuard changes that**. Upload a PDF and receive a clause-by-clause risk assessment, plain-language explanations, financial impact estimates, confidence-backed risk scores, and negotiation-ready recommendations — all in under 60 seconds.

Know exactly what you're signing before it costs you.

---

## How It Works

LexGuard runs a **6-node LangGraph pipeline**. Each node has one job. Failure in any node terminates cleanly — no crashes, no partial output presented as complete.

```
PDF Upload
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│  Node 1 — Validator                                          │
│  Checks text length and quality before any LLM call         │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  Node 2 — Orchestrator                                       │
│  Detects document type AND governing jurisdiction            │
│  Both run concurrently — single wall-clock cost             │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  Node 3 — Clause Extractor (Pass 1)                          │
│  Splits document into structural chunks                      │
│  Extracts every legal clause, obligation, and condition      │
│  Deduplicates across all batches before passing forward      │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  Node 4 — Risk Analyzer (Pass 2)                             │
│  LLaMA 3.3 70B assesses each clause for risk level           │
│  Generates financial impact, negotiation tips,               │
│  and suggested replacement contract language                 │
│  Failed batches get a single-clause rescue pass              │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  Node 5 — Simplifier                                         │
│  Converts every clause to plain English                      │
│  Locale-aware — uses jurisdiction detected in Node 2         │
│  Falls back to technical reason text if timeout occurs       │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  Node 6 — Reporter                                           │
│  Weighted risk score (0–10) with transparent explanation     │
│  Top 3 priorities surfaced before the full clause list       │
│  Downloadable .txt report                                    │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
              Risk Report (UI + .txt download)
```

State flows through a `DocumentState` TypedDict. Every node either advances the state or sets an error — nothing is swallowed silently. Per-node timing is logged so slow steps are immediately visible.

---

## What You Get Per Clause

LexGuard goes beyond "this clause is risky." For every flagged clause, it produces:

| Field | What it tells you |
|---|---|
| **Risk Level** | `HIGH` / `MEDIUM` / `LOW` / `SAFE` with confidence % |
| **Plain English** | What this clause actually means for you |
| **Financial Impact** | Quantified exposure — e.g. *"Potential loss of ₹1,68,000 if vacated early"* |
| **Negotiation Tip** | Specific ask — e.g. *"Request 30-day notice period, cite MRC Act Section 16"* |
| **Replacement Language** | Ready-to-use contract text you can paste into a counter-proposal |

Plus a **Top 3 Priorities** section at the top — the most urgent clauses to negotiate before signing, ranked by severity and confidence.

---

## Features

**Analysis**
- Automatic document type and jurisdiction detection — no manual selection
- Two-pass architecture: clause extraction then risk assessment (cleaner separation, better accuracy)
- Clause deduplication — identical clauses are assessed once, never double-counted
- Clause-level risk tagging: `HIGH` / `MEDIUM` / `LOW` / `SAFE`
- Confidence score per clause (50–99%), factored into the composite score
- Financial impact quantification with actual figures from the clause
- Per-clause negotiation tips — specific to the clause, not boilerplate
- Ready-to-use suggested replacement language for HIGH and MEDIUM clauses
- Weighted composite risk score with transparent calculation breakdown
- Top 3 priorities surfaced before the full clause list

**Reliability**
- Concurrent batch processing with staggered start (no sequential bottleneck)
- 3 attempts per batch with exponential backoff before failing gracefully
- Single-clause rescue pass for any clauses that time out in bulk assessment
- Mathematically sound deadlines — every timeout is achievable, not aspirational
- Round-robin API key rotation (true per-call rotation, not cached)
- Rate-limited key cooldown — hot keys are skipped automatically for 30s
- Locale-aware analysis — jurisdiction detected from document, never assumed

**Engineering**
- LangGraph state machine with conditional error routing
- File validation: 10MB limit, PDF header check, encryption detection, page count
- OCR fallback for scanned PDFs (requires Tesseract + Poppler)
- Result caching by file hash — same file never analyzed twice in a session
- Daily rotating structured log files with per-node elapsed timing
- `pypdf` (actively maintained) with `PyPDF2` fallback

---

## Supported Document Types

| Document | Key Checks |
|---|---|
| **Offer Letter** | Notice period, IP ownership, salary revision discretion, non-compete scope, bond/training recovery, moonlighting restrictions |
| **Employment Contract** | Termination clauses, garden leave, gross misconduct definition, indemnity cap, jurisdiction, probation process |
| **Rent Agreement** | Deposit amount and refund conditions, rent escalation cap, lock-in penalties, immediate termination without notice, 48-hour vacate clauses |
| **Internship Contract** | IP assignment, stipend payment timeline, working hours, NDA scope, non-compete for interns |
| **NDA** | Confidentiality duration, definition breadth, residuals clause, standard exceptions, mutual vs one-sided |
| **Service Agreement** | Payment terms, scope creep handling, IP ownership, termination for convenience, liability cap, auto-renewal |
| **Loan Agreement** | Interest rate variability, prepayment penalties, default triggers, acceleration clause, collateral scope |
| **SaaS Contract** | SLA and uptime guarantees, data portability, auto-renewal opt-out, price escalation, data deletion timeline |
| **Freelancer Agreement** | Payment timelines, IP transfer on payment, revision scope, liability cap, non-compete enforceability |
| **Other** | General termination, notice period, liability, jurisdiction, payment terms |

---

## Risk Scoring

```
Score = Σ (base_score × weight × confidence) ÷ Σ weights

Base scores:   HIGH → 9    MEDIUM → 5    LOW → 2    SAFE → 0
Weights:       HIGH → 3    MEDIUM → 2    LOW → 1    SAFE → 0

SAFE clauses have zero weight — they don't dilute the score.
A document with 50 safe clauses and 1 HIGH clause still scores high.
Confidence is factored in — a HIGH clause at 55% confidence weighs
less than the same clause at 95% confidence.
```

| Score | Verdict |
|---|---|
| ≥ 8.0 | 🔴 Do Not Sign — Serious Issues Found |
| ≥ 6.0 | 🔴 High Risk — Negotiate Before Signing |
| ≥ 4.0 | 🟡 Moderate Risk — Review Carefully |
| ≥ 2.0 | 🟢 Low Risk — Generally Fair |
| < 2.0 | 🟢 Safe to Sign — Well Balanced |

Every report includes a plain-English explanation of how the score was calculated — no mystery numbers.

---

## Getting Started

### Prerequisites

- Python 3.10+
- Free Groq API key → [console.groq.com](https://console.groq.com)
- *(Optional)* Tesseract + Poppler for scanned PDF support

### Installation

```bash
# Clone
git clone https://github.com/your-username/LexGuard.git
cd LexGuard

# Create virtual environment
python -m venv venv

# Activate — Windows
venv\Scripts\Activate.ps1

# Activate — macOS / Linux
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Configure

Create `.env` in the project root:

```env
GROQ_API_KEY_1=your_first_groq_key_here
GROQ_API_KEY_2=your_second_groq_key_here   # optional but recommended
GROQ_API_KEY_3=your_third_groq_key_here    # optional but recommended
```

> Multiple keys are recommended. LexGuard rotates across them per-call to distribute rate-limit headroom. Free Groq accounts are easy to create — three keys gives ~3× the throughput of one.

### Streamlit config (recommended)

Create `.streamlit/config.toml`:

```toml
[server]
maxUploadSize = 10

[browser]
gatherUsageStats = false
```

### Run

```bash
streamlit run app.py
```

Open `http://localhost:8501`

---

## Project Structure

```
LexGuard/
├── agents/
│   ├── orchestrator.py       # Concurrent doc type + jurisdiction detection
│   ├── parser.py             # PDF parsing wrapper
│   ├── pipeline.py           # LangGraph state machine (6 nodes)
│   ├── reporter.py           # Weighted scoring, top priorities, score explanation
│   ├── risk_analyzer.py      # Two-pass: extraction → assessment (70B model)
│   └── simplifier.py         # Batch legal-to-plain translation (8B model)
├── utils/
│   ├── llm.py                # Round-robin key rotation, rate-limit cooldown
│   ├── logger.py             # Structured daily-rotating logs
│   ├── pdf_reader.py         # PDF extraction + OCR fallback
│   └── text_chunker.py       # Structural document chunking with overlap
├── tests/
│   ├── test_pdf_reader.py    # File validation edge cases
│   ├── test_reporter.py      # Scoring and verdict logic
│   └── test_pipeline.py      # Pipeline integration tests
├── logs/                     # Auto-generated, gitignored
├── .env                      # API keys — never committed
├── .gitignore
├── requirements.txt
└── app.py                    # Streamlit entry point
```

---

## Running Tests

```bash
pytest tests/ -v
```

---

## Limitations

- Maximum document size: 10MB, 50 pages
- English-language documents only (other languages may work but are untested)
- OCR for scanned PDFs requires Tesseract and Poppler installed separately
- Analysis accuracy depends on the LLM — not a substitute for qualified legal advice
- Very dense documents (30+ pages) may have some sections analyzed with reduced coverage

---

## Roadmap

- [ ] Clause highlighting directly on PDF viewer
- [ ] Side-by-side comparison of two contract versions
- [ ] FastAPI backend with REST endpoints
- [ ] Multi-language output (Hindi, Tamil, Telugu)
- [ ] Support for DOCX files
- [ ] Confidence calibration via human feedback loop

---

## Disclaimer

LexGuard is an informational tool only. It does not constitute legal advice. Always consult a qualified legal professional before making decisions based on any contract analysis.

---

<div align="center">
<sub>Built with LangGraph · LLaMA 3.3 70B · Groq · Streamlit · Python</sub>
</div>
