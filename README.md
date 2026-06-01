<div align="center">

# ? CodeAid

### AI-Powered Static Code Analysis & Project Understanding System

[![Python](https://img.shields.io/badge/Python-3.10+-3776ab?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.32+-ff4b4b?style=flat-square&logo=streamlit&logoColor=white)](https://streamlit.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-f59e0b?style=flat-square)](LICENSE)
[![CI](https://github.com/praneeth725/CodeAid/actions/workflows/ci.yml/badge.svg)](https://github.com/praneeth725/CodeAid/actions)

**Drop any Python repository. Get a complete picture — issues, repairs, architecture, and AI-powered insights — in seconds.**

[View Demo](https://github.com/praneeth725/CodeAid) · [Report Bug](https://github.com/praneeth725/CodeAid/issues) · [Request Feature](https://github.com/praneeth725/CodeAid/issues)

</div>

---

## What is CodeAid?

CodeAid is a multi-agent AI system that ingests a Python repository and runs it through a coordinated pipeline of six specialized agents — delivering a complete code quality workflow through a single interactive dashboard. No code is ever executed. All analysis is static and safe.

Built as a Final Year Capstone Project at GITAM (Deemed to be University), Hyderabad.

---

## The Pipeline

| Agent | Responsibility |
|---|---|
| **Repository Loader** | Accepts GitHub URL or ZIP. Extracts all Python files. |
| **Scanner Agent** | AST-based detection of 5 issue categories. |
| **Repair Agent** | Safe unused import removal with automatic rollback. |
| **Verifier Agent** | Compile-checks every repair before accepting it. |
| **Explanation Agent** | Human-readable descriptions for every finding. |
| **Project Understanding** | Architecture classification, metrics, best-practice analysis. |
| **LLM Agent** | Optional OpenAI GPT-3.5 or HuggingFace CodeT5 layer. |

---

## Issues Detected

- **Syntax Errors** — files that fail to parse
- **Unused Imports** — with attribute-access fix (os.path.join correctly handled)
- **Long Functions** — exceeding configurable line threshold
- **Excess Parameters** — functions with too many arguments
- **TODO / FIXME Comments** — unresolved technical debt markers

---

## Quickstart

\\\ash
git clone https://github.com/praneeth725/CodeAid.git
cd CodeAid
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # macOS / Linux
pip install -r requirements.txt
streamlit run app.py
\\\

Open your browser at \http://localhost:8501\

---

## Project Structure

\\\
CodeAid/
+-- app.py                         # Streamlit dashboard — single scrollable page
+-- requirements.txt               # All dependencies
+-- core/
¦   +-- repo_loader.py             # GitHub URL + ZIP loader
+-- agents/
¦   +-- scanner.py                 # AST-based issue detection
¦   +-- repair.py                  # Safe auto-repair
¦   +-- verifier.py                # Compile-check + rollback
¦   +-- explain.py                 # Explanation generation
¦   +-- llm_agent.py               # OpenAI / HuggingFace backends
¦   +-- coordinator.py             # Pipeline orchestrator
¦   +-- project_understanding.py  # Repository-level analysis
+-- utils/
    +-- metrics.py                 # Precision, Recall, F1
    +-- codexglue_loader.py        # CodeXGLUE benchmark evaluation
\\\

---

## Evaluation — CodeXGLUE Benchmark

| Metric | Score |
|---|---|
| Precision | 0.920 |
| Recall | 0.880 |
| F1 Score | 0.899 |
| Accuracy | 0.900 |

---

## Tech Stack

- **Language:** Python 3.10+
- **UI:** Streamlit
- **Analysis:** Python \st\ module, Radon
- **AI:** OpenAI GPT-3.5-turbo, HuggingFace CodeT5-small
- **Evaluation:** CodeXGLUE (Devign dataset)
- **Visualization:** Plotly, Pandas

---

## Team

| Name | Registration |
|---|---|
| Kushwanth Reddy | HU22CSEN0101618 |
| Praneeth Salaka | HU22CSEN0100536 |
| Vallabh Rahul | HU22CSEN0100173 |

**Guide:** Dr. Sreedhar Jinka, Associate Professor, Dept. of CSE
**Institution:** GITAM (Deemed to be University), Hyderabad

---

## License

MIT © 2025 Kushwanth Reddy, Praneeth Salaka, Vallabh Rahul
