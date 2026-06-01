# CodeAid — Technical Documentation
## Codebase Reference · Architecture · Workflows · Implementation

---

## 1. Project Overview

**CodeAid** is an AI-powered static code analysis system for Python repositories. It ingests a codebase via GitHub URL or ZIP upload, runs a multi-agent analysis pipeline, and presents results through an interactive Streamlit web dashboard.

### Core Capabilities
| Capability | Description |
|---|---|
| Static analysis | AST-based detection of syntax errors, unused imports, long functions, excess parameters, TODO comments |
| Auto-repair | Safe removal of unused imports with rollback on failure |
| Verification | Compile-check all repaired files using Python's built-in compiler |
| Explanation | Human-readable issue descriptions with fix guidance |
| Project understanding | Repository-level architecture analysis and best-practice suggestions |
| LLM integration | Optional OpenAI or HuggingFace CodeT5 reasoning layer |
| Benchmark evaluation | CodeXGLUE Devign defect detection evaluation |

---

## 2. Repository Structure

```
CodeAid/
│
├── app.py                          ← Streamlit UI entry point
├── requirements.txt                ← All Python dependencies
├── SETUP.md                        ← Installation guide
│
├── core/
│   ├── __init__.py
│   └── repo_loader.py              ← GitHub URL + ZIP file loader
│
├── agents/
│   ├── __init__.py
│   ├── scanner.py                  ← AST-based issue detector
│   ├── repair.py                   ← Safe auto-repair agent
│   ├── verifier.py                 ← Post-repair compilation verifier
│   ├── explain.py                  ← Human-readable explanation generator
│   ├── llm_agent.py                ← OpenAI/HuggingFace LLM interface
│   ├── coordinator.py              ← Pipeline orchestrator
│   └── project_understanding.py   ← Repository-level analysis
│
└── utils/
    ├── __init__.py
    ├── metrics.py                  ← Precision/recall/F1 metrics
    └── codexglue_loader.py         ← CodeXGLUE benchmark integration
```

---

## 3. Architecture Overview

CodeAid follows a **multi-agent pipeline architecture** orchestrated by a central Coordinator.

```
User Input (GitHub URL / ZIP)
        │
        ▼
  ┌─────────────┐
  │ Repo Loader │  Fetches and extracts .py files
  └──────┬──────┘
         │ files: [{"path": str, "source": str}]
         ▼
  ┌─────────────┐
  │ Coordinator │  Orchestrates all agents sequentially
  └──────┬──────┘
         │
    ┌────┴────────────────────────────────────────────┐
    │                                                 │
    ▼                                                 ▼
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌────────────┐
│ Scanner  │ →  │  Repair  │ →  │ Verifier │    │  Project   │
│  Agent   │    │  Agent   │    │  Agent   │    │ Understanding│
└──────────┘    └──────────┘    └──────────┘    └────────────┘
    │                                                 │
    ▼                                                 │
┌──────────┐    ┌──────────┐                         │
│ Explain  │    │   LLM    │ (optional)               │
│  Agent   │    │  Agent   │                         │
└──────────┘    └──────────┘                         │
    │                 │                               │
    └─────────────────┴───────────────────────────────┘
                      │
                      ▼
              ┌──────────────┐
              │  Streamlit   │
              │  Dashboard   │
              └──────────────┘
```

### Design Principles
- **Single Responsibility**: Each agent handles exactly one concern
- **No code execution**: All analysis uses AST parsing only — `exec()` and `eval()` are never called
- **Fail-safe repairs**: Any repair that breaks compilation is automatically rolled back
- **Optional LLM**: The entire pipeline works without any API key
- **Error isolation**: Agent failures are caught by the Coordinator and do not crash the pipeline

---

## 4. Component Documentation

---

### 4.1 `core/repo_loader.py`

**Purpose:** Loads Python source files from external sources.

**Functions:**

#### `load_from_github(url: str) → (files, repo_name)`
Downloads a public GitHub repository as a ZIP archive via the GitHub API.

- Accepts URLs in formats:
  - `https://github.com/owner/repo`
  - `https://github.com/owner/repo/tree/branch`
  - `https://github.com/owner/repo.git`
- Automatically tries `main` → falls back to `master` branch if 404
- Returns: `([{"path": str, "source": str}], "owner/repo")`

**Error handling:**
| Error | Message |
|---|---|
| Invalid URL format | Clear format hint shown |
| HTTP 404 | "Repository not found or not public" |
| Network timeout | "Request timed out" |
| No .py files | "No Python files found" |

#### `load_from_zip(zip_bytes: bytes) → (files, "uploaded_project")`
Extracts Python files from a user-uploaded ZIP archive.

**Filtering rules** (files skipped):
- Files in `__pycache__`, `.git`, `venv`, `env`, `.tox`, `node_modules`
- Hidden files (starting with `.`)
- Empty files
- Non-UTF-8 encoded files

#### Internal helpers:
- `_parse_github_url()` — robust URL parser using regex
- `_extract_python_files_from_zip()` — ZIP extractor with filtering
- `_detect_zip_prefix()` — strips GitHub's `repo-branch/` prefix

---

### 4.2 `agents/scanner.py`

**Purpose:** Core static analysis engine. Parses each file into an AST and detects issues.

#### Key classes:

**`Issue` (dataclass)**
```
file:       str         — relative file path
line:       int|None    — line number where issue occurs
issue_type: str         — one of: SyntaxError, UnusedImport, LongFunction,
                          ManyParameters, TodoComment
message:    str         — human-readable description
severity:   str         — "error" | "warning" | "info"
symbol:     str|None    — function name or import name (if applicable)
```

**`ScanResult` (dataclass)**
```
file:           str           — file path
issues:         list[Issue]   — all issues found in this file
parsed_ok:      bool          — False if the file had a syntax error
line_count:     int           — total lines in file
function_count: int           — number of functions detected
class_count:    int           — number of classes detected
```

**`ScannerAgent`**

Main class. Configured with:
```python
DEFAULT_CONFIG = {
    "max_function_lines": 60,   # configurable via sidebar
    "max_parameters": 7,         # configurable via sidebar
    "todo_patterns": ["TODO", "FIXME", "HACK", "XXX", "BUG"],
}
```

**Detection rules:**

| Issue Type | Detection Method | Threshold |
|---|---|---|
| SyntaxError | `ast.parse()` raises `SyntaxError` | Any |
| UnusedImport | Imports not found in used-name set | Any |
| LongFunction | `end_lineno - lineno + 1 > threshold` | Default: 60 lines |
| ManyParameters | `len(args.args + posonlyargs + kwonlyargs) > threshold` | Default: 7 |
| TodoComment | Regex on raw source lines | Any match |

#### Critical bug fixed — Unused Import Detection

**Original design flaw:** The original document's approach only checked `ast.Name` nodes for import usage. This misses attribute access:
```python
import os
os.path.join("a", "b")   # ← 'os' appears as ast.Attribute.value, not ast.Name
```

**Fix implemented in `_collect_all_used_names()`:**
```python
# For every ast.Attribute node, we walk to the root Name
def _get_attribute_root(node):
    current = node
    while isinstance(current, ast.Attribute):
        current = current.value
    if isinstance(current, ast.Name):
        return current.id
```

This correctly identifies `os`, `json`, `numpy`, etc. as "used" even when accessed through attribute chains.

**Additional parameter counting fix:** The original design only counted `args.args`. Fixed to include:
- `args.posonlyargs` — positional-only params (Python 3.8+)
- `args.kwonlyargs` — keyword-only params
- `args.vararg` — `*args`
- `args.kwarg` — `**kwargs`
- Excludes `self` and `cls` automatically

---

### 4.3 `agents/repair.py`

**Purpose:** Applies safe, targeted auto-fixes to detected issues.

#### What gets repaired automatically:
| Issue | Action |
|---|---|
| UnusedImport | Import line(s) removed from source |

#### What does NOT get auto-repaired:
| Issue | Reason |
|---|---|
| SyntaxError | Cannot be safely inferred — must be manual |
| LongFunction | Splitting functions requires semantic understanding |
| ManyParameters | Parameter grouping requires design intent |
| TodoComment | Developer intent — removing could hide context |

#### Repair strategy for unused imports:
1. Collect line numbers from `UnusedImport` issues
2. Parse the file's AST to find exact import node line spans (handles multi-line imports)
3. Rebuild source excluding those line ranges
4. Clean up consecutive blank lines
5. Return `RepairResult` with `was_modified=True`

**`RepairResult`** fields:
```
file:               str         — file path
original_source:    str         — source before repair
repaired_source:    str         — source after repair (or same as original if no fix)
repairs_applied:    list[str]   — human-readable list of applied fixes
repairs_skipped:    list[str]   — human-readable list of skipped fixes with reasons
was_modified:       bool        — True if any repair was applied
```

---

### 4.4 `agents/verifier.py`

**Purpose:** Ensures repaired code is still syntactically valid.

#### Verification method:
```python
compile(source, filepath, "exec", ast.PyCF_ONLY_AST)
```

- Uses `ast.PyCF_ONLY_AST` flag — parses into AST without executing bytecode
- This is equivalent to `py_compile` but faster and produces no `.pyc` files
- Completely safe — no user code ever runs

#### Rollback logic:
If verification fails after a repair:
1. `repaired_source` is reset to `original_source`
2. `was_modified` is set to `False`
3. `repairs_applied` is cleared
4. A rollback warning is prepended to `repairs_skipped`

Unmodified files are marked `passed=True` without running verification (skip-check optimization).

---

### 4.5 `agents/explain.py`

**Purpose:** Generates human-readable explanations for each detected issue.

#### Two-tier explanation system:
1. **Template mode** (always active): Pre-written explanations per issue type, formatted as Markdown with context-specific details inserted
2. **LLM-enhanced mode** (optional): For `LongFunction` and `ManyParameters` issues, calls the LLM agent to append an AI-generated refactoring suggestion

#### Explanation template structure:
Each template includes:
- Severity emoji indicator (🔴🟡🟠🔵)
- Issue type label
- File and line location
- Full issue message
- "Why it matters" explanation
- "Fix" guidance

#### Output types:
- **`Explanation.full_text`** — Markdown string for the detailed view
- **`Explanation.short_text`** — one-liner for table display
- **`group_explanations_by_file()`** — groups explanations by file path for the UI

---

### 4.6 `agents/llm_agent.py`

**Purpose:** Optional AI reasoning layer supporting two backends.

#### Backends:

**OpenAI (GPT-3.5-turbo)**
- Requires: API key from https://platform.openai.com
- Model: `gpt-3.5-turbo`
- Temperature: 0.3 (focused, consistent responses)
- Falls back gracefully if API call fails

**HuggingFace (CodeT5-small)**
- Model: `Salesforce/codet5-small`
- Task: `text2text-generation`
- Device: CPU (`device=-1`)
- Downloads ~300MB on first use, then cached
- No API key required

#### Methods:
| Method | Purpose |
|---|---|
| `analyze_issue(issue, context)` | Suggest a fix for a specific issue |
| `enhance_explanation(issue)` | Add an AI tip to an explanation |
| `summarize_project(project_report)` | Generate a project health summary |

#### Availability:
- `is_available()` — returns `True` only if the backend initialized successfully
- All callers check `is_available()` before calling LLM methods
- LLM failure never crashes the pipeline

---

### 4.7 `agents/project_understanding.py`

**Purpose:** Analyzes the repository as a whole to provide architectural insights.

#### Analysis components:

**Project type detection**
Matches imported package names against signature dictionaries:
```python
"Web API / Backend": ["flask", "django", "fastapi", ...]
"Machine Learning":  ["torch", "tensorflow", "sklearn", ...]
"Data Science":      ["pandas", "numpy", "matplotlib", ...]
"CLI Tool":          ["argparse", "click", "typer", ...]
```

**Architecture classification**
Based on directory structure:
- Single file → `"Single-file script"`
- All files in root, ≤5 files → `"Flat / Monolithic"`
- 3+ top-level directories → `"Modular"`
- Otherwise → `"Semi-modular"`

**Best practice detection**
Checks for presence/absence of:
- `tests/` or `test/` directory
- `README.md` / `README.rst`
- `docs/` directory
- CI config (`.github/workflows`, `.travis.yml`, etc.)
- `requirements.txt` or `pyproject.toml`

**Code metrics computed:**
| Metric | Description |
|---|---|
| total_lines | Total lines of code |
| total_functions | Count of all function definitions |
| total_classes | Count of all class definitions |
| avg_function_length | Mean lines per function |
| avg_parameters | Mean parameter count per function |
| docstring_coverage_pct | % of functions with a docstring |
| max_function_length | Longest function in lines |

**`ProjectReport`** fields:
```
project_type:          str        — e.g. "Machine Learning"
architecture:          str        — e.g. "Modular"
dependencies:          list[str]  — from requirements.txt
missing_practices:     list[str]  — what's absent
suggestions:           list[str]  — improvement recommendations
metrics:               dict       — code quality metrics
has_tests:             bool
has_readme:            bool
has_docs:              bool
has_ci:                bool
dependency_file_found: bool
top_imports:           list[str]  — most-imported packages
architecture_patterns: list[str]  — detected patterns (REST, ORM, async, etc.)
llm_summary:           str        — AI-generated project summary (optional)
```

---

### 4.8 `agents/coordinator.py`

**Purpose:** Central orchestrator. Runs all agents in sequence and aggregates results.

#### Pipeline execution order:
```
Stage 1 (10%) → Scanner
Stage 2 (35%) → Repair
Stage 3 (55%) → Verifier
Stage 4 (70%) → Explain
Stage 5 (85%) → Project Understanding
Done   (100%) → Results returned
```

#### Error handling:
Each stage is wrapped in a try/except. If any agent raises an unexpected error:
- The error is appended to `pipeline_errors`
- The pipeline continues to the next stage
- The UI displays warnings for any pipeline errors

#### Output dict structure:
```python
{
    "files":                  list[dict],           # original files
    "scan_results":           list[ScanResult],
    "scan_summary":           dict,                 # aggregate stats
    "repair_results":         list[RepairResult],
    "verification_results":   list[VerificationResult],
    "explanations":           list[Explanation],
    "explanations_by_file":   dict[str, list],
    "project_report":         ProjectReport | None,
    "llm_status":             str,
    "llm_available":          bool,
    "pipeline_errors":        list[str],
}
```

---

### 4.9 `utils/metrics.py`

**Purpose:** Evaluation metric computations.

#### Functions:

| Function | Purpose |
|---|---|
| `precision(tp, fp)` | TP / (TP + FP) |
| `recall(tp, fn)` | TP / (TP + FN) |
| `f1_score(prec, rec)` | Harmonic mean of precision and recall |
| `compute_classification_metrics(predicted, truth)` | Full metrics dict with TP/FP/FN |
| `compute_per_type_metrics(predicted, truth)` | Breakdown by issue type |
| `exact_match_accuracy(predictions, references)` | Repair quality: exact match % |
| `token_overlap_score(prediction, reference)` | Unigram F1 for code similarity |
| `compute_repair_metrics(predictions, references)` | Combined repair quality dict |
| `build_metrics_display(scan, repair, verify)` | Dashboard-ready metrics dict |

---

### 4.10 `utils/codexglue_loader.py`

**Purpose:** CodeXGLUE benchmark integration for academic evaluation.

#### Evaluation methodology:
1. Load N samples from the Devign defect detection dataset (via HuggingFace)
2. For each sample, run CodeAid's scanner on the code
3. If any issue detected → predicted label = 1 (defective)
4. If no issues → predicted label = 0 (clean)
5. Compare to ground truth labels
6. Compute binary classification metrics

**Fallback:** If the `datasets` library or Devign dataset is unavailable, generates synthetic Python samples (50% clean, 50% with intentional issues) to demonstrate the evaluation pipeline.

#### `evaluate_on_devign(n_samples, scanner_config)` returns:
```python
{
    "precision":       float,
    "recall":          float,
    "f1":              float,
    "accuracy":        float,
    "true_positives":  int,
    "false_positives": int,
    "false_negatives": int,
    "true_negatives":  int,
    "total_samples":   int,
    "dataset_source":  str,   # "HuggingFace Devign" or "Synthetic"
}
```

---

## 5. The Streamlit UI (`app.py`)

### Layout
```
┌──────────────────────────────────────────────────┐
│  Sidebar                │  Main area              │
│  ─────────────          │  ─────────────────────  │
│  LLM Agent selector     │  Header                 │
│  OpenAI key input       │  Repository input       │
│  Scanner thresholds     │  ─────────────────────  │
│  Evaluation toggle      │  [After analysis:]      │
│                         │  Summary metric cards   │
│                         │  ┌──────────────────┐  │
│                         │  │  Tab navigation  │  │
│                         │  ├──────────────────┤  │
│                         │  │ Issues | Repairs  │  │
│                         │  │ Project | Files   │  │
│                         │  │ Metrics | Eval    │  │
│                         │  └──────────────────┘  │
└──────────────────────────────────────────────────┘
```

### Tabs:

| Tab | Content |
|---|---|
| 🐛 Issues | Bar chart of issue types, sortable issues table, per-file explanation expanders |
| 🔧 Repairs | Files repaired (with before/after code), skipped repairs with reasons, verification table |
| 🏗️ Project Insights | Project type, architecture, best-practice checklist, metrics, dependencies, suggestions |
| 📁 Files | File browser with issue indicators, syntax-highlighted code view, side-by-side diff for repaired files |
| 📊 Metrics | Scanner/Repair/Verifier stats, issue distribution pie chart |
| 🧪 Evaluation | CodeXGLUE benchmark runner with confusion matrix display |

### Design choices:
- **Dark theme** (`#0f1117` background) with `#90cdf4` blue accents
- **IBM Plex Sans** for body text, **IBM Plex Mono** for code and labels
- **Plotly charts** with matching dark backgrounds
- Fully responsive — works at any screen width
- Session state used to persist results across sidebar interactions

---

## 6. Data Flow Diagram

```
GitHub URL/ZIP
     │
     ▼
repo_loader.py
     │ list[{"path": str, "source": str}]
     ▼
coordinator.py
     │
     ├──► scanner.py ──────────────────────► list[ScanResult]
     │         │                                    │
     │         └── Issue(type, line, msg, severity) │
     │                                              │
     ├──► repair.py ◄── list[ScanResult] ─────────┘
     │         │
     │         └──► list[RepairResult]
     │                    │ {original_source, repaired_source}
     │                    ▼
     ├──► verifier.py ────────────────────► list[VerificationResult]
     │         │ (rollback if failed)
     │         │
     ├──► explain.py ◄── list[ScanResult]
     │         │
     │         └──► list[Explanation]
     │                    │ {full_text, short_text}
     │                    │
     ├──► project_understanding.py ───────► ProjectReport
     │         │ {type, architecture, suggestions, metrics}
     │         │
     └──► [all results] ──────────────────► app.py (Streamlit UI)
```

---

## 7. Statistics & Benchmarks

### Scanner detection rules:

| Issue Type | Default Threshold | Configurable |
|---|---|---|
| SyntaxError | Any parse failure | No |
| UnusedImport | Any unreferenced import | No |
| LongFunction | > 60 lines | Yes (20–150) |
| ManyParameters | > 7 params | Yes (3–15) |
| TodoComment | Any TODO/FIXME/HACK/XXX/BUG | No |

### Performance characteristics (CPU, Windows 10):
| Files | Approx. scan time |
|---|---|
| 1–10 | < 1 second |
| 10–50 | 1–3 seconds |
| 50–200 | 3–10 seconds |
| 200+ | 10–30 seconds |

(LLM agent adds 1–5 seconds per file when enabled)

### Package sizes:
| Package | Approx. size |
|---|---|
| streamlit | ~20 MB |
| torch (CPU) | ~180 MB |
| transformers | ~50 MB |
| plotly | ~10 MB |
| Total (no LLM) | ~80 MB |
| Total (with HF) | ~350 MB |

---

## 8. Known Limitations

| Limitation | Detail |
|---|---|
| Python only | Only `.py` files are analyzed. Other languages are ignored. |
| No semantic repair | Logical bugs (wrong algorithm, off-by-one errors) cannot be auto-fixed. |
| LLM quality varies | HuggingFace CodeT5-small produces lower quality suggestions than GPT-3.5. |
| Large repos | Repos with 500+ files may be slow (~1 min). |
| Private repos | Not supported — GitHub authentication not implemented. |
| C/C++ Devign mismatch | CodeXGLUE Devign contains C code; evaluation is a proxy metric only. |

---

## 9. Extension Points

The modular design makes CodeAid easy to extend:

| Extension | Where to add it |
|---|---|
| New issue type | Add detection in `scanner.py`, template in `explain.py` |
| New repair type | Add handler in `repair.py` |
| New LLM backend | Add `_init_*` and `_call_*` methods in `llm_agent.py` |
| New project type | Add entry to `_PROJECT_SIGNATURES` in `project_understanding.py` |
| New metric | Add function to `metrics.py` |
| New UI tab | Add `st.tab()` entry in `app.py` |

---

*CodeAid v1.0 · Documentation generated alongside source code*
