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

**Upload any legal document. Get a structured risk report in 30 seconds.**

[![Python](https://img.shields.io/badge/Python-3.10+-3B82F6?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![LangGraph](https://img.shields.io/badge/LangGraph-Multi--Agent-7C3AED?style=flat-square)](https://github.com/langchain-ai/langgraph)
[![Groq](https://img.shields.io/badge/Groq-LLaMA_3.3_70B-F59E0B?style=flat-square)](https://groq.com)
[![Streamlit](https://img.shields.io/badge/Streamlit-UI-EF4444?style=flat-square)](https://streamlit.io)
[![Pytest](https://img.shields.io/badge/Pytest-Tested-22C55E?style=flat-square)](https://pytest.org)
[![License](https://img.shields.io/badge/License-MIT-6366F1?style=flat-square)](LICENSE)

</div>

---

## The Problem

Every year, professionals sign offer letters, rent agreements, and freelance contracts they don't fully understand. A lawyer charges ₹2,000–5,000 per consultation. Generic AI tools give vague answers. Most people just sign and hope for the best.

LexGuard fixes this. Upload a PDF — get clause-level risk analysis, plain-language explanations, and specific negotiation tips in under 30 seconds.

---

## How It Works

LexGuard runs a **5-node LangGraph pipeline**. Each node has one job. Failure in any node terminates cleanly — no crashes, no partial output.

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
│  LLM classifies document type (offer letter, NDA, etc.)     │
│  Uses beginning + middle + end of document — not just first  │
│  1500 characters                                             │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  Node 3 — Risk Analyzer                                      │
│  LLM extracts risky clauses with risk level + confidence     │
│  Checks are tailored per document type                       │
│  Samples 12,000 chars across full document length            │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  Node 4 — Simplifier                                         │
│  Batch-converts all legal clauses to plain English           │
│  Single API call — no per-clause round trips                 │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  Node 5 — Reporter                                           │
│  Weighted risk score (0–10), verdict, downloadable report    │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
              Risk Report (UI + .txt download)
```

State flows through a `DocumentState` TypedDict. Every node either advances the state or sets an error — nothing is swallowed silently.

---

## Features

**Analysis**
- Automatic document type detection — no manual selection needed
- Clause-level risk tagging: `HIGH` / `MEDIUM` / `LOW` / `SAFE`
- Confidence score per clause (50–99%)
- Per-clause negotiation tips — specific, not generic
- Weighted composite risk score with verdict

**Engineering**
- LangGraph state machine with conditional error routing
- Retry with exponential backoff on all LLM calls
- Batch simplification — all clauses in one API call
- File validation: size limit, PDF header check, encryption detection
- OCR fallback for scanned PDFs (requires Tesseract)
- Result caching by file hash — same file never analyzed twice
- Daily rotating log files

---

## Supported Document Types

| Document | Key Checks |
|----------|-----------|
| **Offer Letter** | Notice period, IP ownership, salary revision discretion, non-compete, bond period, moonlighting restrictions |
| **Employment Contract** | Termination clauses, garden leave, indemnity, jurisdiction, medical fitness |
| **Rent Agreement** | Security deposit refund, rent escalation, lock-in penalties, subletting rights |
| **Internship Contract** | IP assignment, stipend conditions, NDA scope, conversion terms |
| **NDA** | Confidentiality duration, definition scope, residuals clause, permitted disclosures |
| **Service Agreement** | Payment terms, liability cap, scope creep handling, termination for convenience |

---

## Risk Scoring

```
Score = Σ (base_score × weight × confidence) ÷ Σ weights

Base scores:   HIGH → 9    MEDIUM → 5    LOW → 2    SAFE → 0
Weights:       HIGH → 3    MEDIUM → 2    LOW → 1    SAFE → 0

  Score ≥ 7.0  →  🔴  Do Not Sign — Negotiate First
  Score ≥ 4.0  →  🟡  Review Carefully Before Signing
  Score < 4.0  →  🟢  Relatively Safe to Sign
```

Confidence is factored into the score — a HIGH risk clause at 55% confidence weighs less than one at 95%.

---

## Getting Started

### Prerequisites

- Python 3.10+
- Free Groq API key → [console.groq.com](https://console.groq.com)

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
GROQ_API_KEY=your_groq_api_key_here
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
│   ├── orchestrator.py       # Document type classification
│   ├── parser.py             # Text validation layer
│   ├── pipeline.py           # LangGraph state machine
│   ├── reporter.py           # Weighted risk scoring + report
│   ├── risk_analyzer.py      # Clause extraction + risk labeling
│   └── simplifier.py         # Batch legal-to-plain translation
├── utils/
│   ├── logger.py             # Structured daily-rotating logs
│   └── pdf_reader.py         # PDF extraction + OCR fallback
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

20 tests across three modules — validator, scorer, pipeline integration.

---

## Limitations

- Maximum document size: 10MB, 50 pages
- Analysis samples up to 12,000 characters across document length — very long contracts may have mid-section clauses missed
- OCR for scanned PDFs requires Tesseract and Poppler installed separately
- Output accuracy depends on LLM — not a substitute for qualified legal advice

---

## Roadmap

- [ ] Full-document chunked analysis for 50+ page contracts
- [ ] FastAPI backend with REST endpoints
- [ ] Clause highlighting directly on PDF viewer
- [ ] Side-by-side comparison of two contract versions
- [ ] Multi-language output (Hindi, Tamil, Telugu)
- [ ] Confidence calibration via human feedback

---

## Disclaimer

LexGuard is an informational tool only. It does not constitute legal advice. Always consult a qualified legal professional before making decisions based on any contract analysis.

---

<div align="center">
<sub>Built with LangGraph · LLaMA 3.3 70B · Groq · Streamlit · Python</sub>
</div>
