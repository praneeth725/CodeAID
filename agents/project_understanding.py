"""
agents/project_understanding.py
--------------------------------
Project Understanding Agent: Analyzes the repository as a whole.

Performs heuristic analysis to determine:
  - Project type (web API, ML, data science, CLI tool, library, script)
  - Architecture style (monolithic, modular, flat)
  - Dependency health (reads requirements.txt / pyproject.toml)
  - Missing best practices (tests/, README, docs, CI config)
  - Code metrics (average function length, complexity, docstring coverage)
  - Architectural suggestions

No code is executed. All analysis is file-name, import-pattern, and
directory-structure based.
"""

import ast
import re
from dataclasses import dataclass, field
from collections import defaultdict


# ─────────────────────────────────────────────
# Project type signatures
# ─────────────────────────────────────────────

_PROJECT_SIGNATURES = {
    "Web API / Backend": ["flask", "django", "fastapi", "aiohttp", "tornado", "starlette", "bottle", "sanic"],
    "Machine Learning": ["torch", "tensorflow", "keras", "sklearn", "scikit_learn", "xgboost", "lightgbm", "catboost", "transformers", "huggingface_hub"],
    "Data Science / Analysis": ["pandas", "numpy", "matplotlib", "seaborn", "plotly", "scipy", "statsmodels", "jupyter"],
    "CLI Tool": ["argparse", "click", "typer", "docopt", "fire"],
    "Testing Suite": ["pytest", "unittest", "nose", "hypothesis"],
    "Automation / Scripting": ["subprocess", "shutil", "pathlib", "glob", "schedule", "celery"],
    "Database Application": ["sqlalchemy", "pymongo", "psycopg2", "sqlite3", "peewee", "tortoise"],
}

_ARCHITECTURE_KEYWORDS = {
    "REST API": ["@app.route", "@router.", "Blueprint", "APIRouter", "endpoint"],
    "ORM Models": ["db.Model", "Base", "Column", "ForeignKey", "relationship"],
    "Async": ["async def", "await ", "asyncio"],
    "Design Patterns": ["__init__", "singleton", "factory", "observer", "decorator"],
}


# ─────────────────────────────────────────────
# Result data structure
# ─────────────────────────────────────────────

@dataclass
class ProjectReport:
    project_type: str = "General Python Project"
    architecture: str = "Unknown"
    dependencies: list[str] = field(default_factory=list)
    missing_practices: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    metrics: dict = field(default_factory=dict)
    dependency_file_found: bool = False
    has_tests: bool = False
    has_readme: bool = False
    has_docs: bool = False
    has_ci: bool = False
    file_count: int = 0
    top_imports: list[str] = field(default_factory=list)
    architecture_patterns: list[str] = field(default_factory=list)
    llm_summary: str = ""


# ─────────────────────────────────────────────
# Project Understanding Agent
# ─────────────────────────────────────────────

class ProjectUnderstandingAgent:
    def analyze(
        self,
        files: list[dict],
        extra_files: dict[str, str] = None,
        llm_agent=None,
    ) -> ProjectReport:
        """
        Analyze the full repository.

        Args:
            files: Python source files [{"path": str, "source": str}]
            extra_files: Dict of non-Python files {filename: content}
                         (e.g., requirements.txt, README.md)
            llm_agent: Optional LLMAgent for enhanced summary

        Returns:
            ProjectReport
        """
        extra_files = extra_files or {}
        report = ProjectReport()
        report.file_count = len(files)

        # Collect all imports across files
        all_imports = _collect_all_imports(files)
        report.top_imports = _top_n(all_imports, 10)

        # ── Detect project type ───────────────────────────────────
        report.project_type = _detect_project_type(all_imports)

        # ── Detect architecture ───────────────────────────────────
        report.architecture = _detect_architecture(files)
        report.architecture_patterns = _detect_patterns(files)

        # ── Analyze dependencies ──────────────────────────────────
        report.dependencies, report.dependency_file_found = _parse_dependencies(extra_files)

        # ── Detect file/folder structure ──────────────────────────
        all_paths = [f["path"] for f in files]
        report.has_tests = _has_directory(all_paths, ["tests", "test", "testing"])
        report.has_readme = _has_file(extra_files, ["readme.md", "readme.rst", "readme.txt"])
        report.has_docs = _has_directory(all_paths, ["docs", "doc", "documentation"])
        report.has_ci = _has_file(
            extra_files,
            [".github/workflows", ".travis.yml", "circle.yml", "Jenkinsfile", ".gitlab-ci.yml"]
        )

        # ── Compute code metrics ──────────────────────────────────
        report.metrics = _compute_metrics(files)

        # ── Generate suggestions ──────────────────────────────────
        report.missing_practices, report.suggestions = _generate_suggestions(report, files)

        # ── Optional LLM summary ──────────────────────────────────
        if llm_agent and llm_agent.is_available():
            try:
                report.llm_summary = llm_agent.summarize_project({
                    "type": report.project_type,
                    "architecture": report.architecture,
                    "suggestions": report.suggestions,
                })
            except Exception:
                report.llm_summary = ""

        return report


# ─────────────────────────────────────────────
# Analysis helpers
# ─────────────────────────────────────────────

def _collect_all_imports(files: list[dict]) -> dict[str, int]:
    """Count how many times each top-level package is imported across all files."""
    counts = defaultdict(int)
    for f in files:
        try:
            tree = ast.parse(f["source"])
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    pkg = alias.name.split(".")[0]
                    counts[pkg] += 1
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    pkg = node.module.split(".")[0]
                    counts[pkg] += 1
    return dict(counts)


def _detect_project_type(imports: dict[str, int]) -> str:
    """Match imported packages to known project-type signatures."""
    scores = defaultdict(int)
    for pkg in imports:
        for project_type, keywords in _PROJECT_SIGNATURES.items():
            if pkg.lower() in keywords or pkg.lower().replace("-", "_") in keywords:
                scores[project_type] += imports[pkg]

    if not scores:
        return "General Python Script"

    return max(scores, key=scores.get)


def _detect_architecture(files: list[dict]) -> str:
    """Determine if the project is monolithic, modular, or flat."""
    paths = [f["path"] for f in files]
    dirs = set()
    for p in paths:
        parts = p.replace("\\", "/").split("/")
        if len(parts) > 1:
            dirs.add(parts[0])

    unique_top_dirs = len(dirs)
    file_count = len(files)

    if file_count == 1:
        return "Single-file script"
    elif unique_top_dirs <= 1 and file_count <= 5:
        return "Flat / Monolithic (all files in root)"
    elif unique_top_dirs >= 3:
        return "Modular (organized into packages/directories)"
    else:
        return "Semi-modular (partially organized)"


def _detect_patterns(files: list[dict]) -> list[str]:
    """Detect architectural and language patterns used in the codebase."""
    found = []
    combined_source = "\n".join(f["source"] for f in files)

    for pattern_name, keywords in _ARCHITECTURE_KEYWORDS.items():
        if any(kw in combined_source for kw in keywords):
            found.append(pattern_name)

    return found


def _parse_dependencies(extra_files: dict[str, str]) -> tuple[list[str], bool]:
    """Parse requirements.txt or pyproject.toml for dependencies."""
    # Try requirements.txt first
    for key, content in extra_files.items():
        if "requirements" in key.lower() and key.endswith(".txt"):
            deps = _parse_requirements_txt(content)
            return deps, True

    # Try pyproject.toml
    for key, content in extra_files.items():
        if "pyproject.toml" in key.lower():
            deps = _parse_pyproject_toml(content)
            return deps, True

    return [], False


def _parse_requirements_txt(content: str) -> list[str]:
    """Extract package names from requirements.txt content."""
    deps = []
    for line in content.splitlines():
        line = line.strip()
        if line and not line.startswith("#") and not line.startswith("-"):
            # Strip version specifiers: package>=1.0 → package
            pkg = re.split(r"[>=<!~\[]", line)[0].strip()
            if pkg:
                deps.append(pkg)
    return deps


def _parse_pyproject_toml(content: str) -> list[str]:
    """Basic dependency extraction from pyproject.toml (without toml parser)."""
    deps = []
    in_deps = False
    for line in content.splitlines():
        if "dependencies" in line.lower():
            in_deps = True
        if in_deps:
            match = re.search(r'"([a-zA-Z0-9_-]+)', line)
            if match:
                deps.append(match.group(1))
            if line.strip() == "]":
                in_deps = False
    return deps


def _has_directory(paths: list[str], names: list[str]) -> bool:
    """Check if any of the given directory names appear in file paths."""
    normalized = [p.replace("\\", "/").lower() for p in paths]
    for name in names:
        if any(f"/{name}/" in p or p.startswith(f"{name}/") for p in normalized):
            return True
    return False


def _has_file(extra_files: dict, names: list[str]) -> bool:
    """Check if any of the given file names exist in extra_files."""
    keys_lower = [k.lower() for k in extra_files]
    for name in names:
        if any(name.lower() in k for k in keys_lower):
            return True
    return False


def _compute_metrics(files: list[dict]) -> dict:
    """Compute codebase-wide metrics."""
    total_functions = 0
    total_classes = 0
    total_lines = 0
    function_lengths = []
    param_counts = []
    docstring_count = 0
    function_count_for_doc = 0

    for f in files:
        source = f["source"]
        lines = source.splitlines()
        total_lines += len(lines)

        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                total_functions += 1
                function_count_for_doc += 1
                length = getattr(node, "end_lineno", node.lineno) - node.lineno + 1
                function_lengths.append(length)

                args = node.args
                params = len(args.args) + len(args.posonlyargs) + len(args.kwonlyargs)
                param_counts.append(params)

                # Check for docstring
                if (
                    node.body
                    and isinstance(node.body[0], ast.Expr)
                    and isinstance(node.body[0].value, ast.Constant)
                    and isinstance(node.body[0].value.value, str)
                ):
                    docstring_count += 1

            elif isinstance(node, ast.ClassDef):
                total_classes += 1

    avg_fn_length = round(sum(function_lengths) / len(function_lengths), 1) if function_lengths else 0
    avg_params = round(sum(param_counts) / len(param_counts), 1) if param_counts else 0
    docstring_pct = round(100 * docstring_count / function_count_for_doc, 1) if function_count_for_doc else 0

    return {
        "total_lines": total_lines,
        "total_functions": total_functions,
        "total_classes": total_classes,
        "avg_function_length": avg_fn_length,
        "avg_parameters": avg_params,
        "docstring_coverage_pct": docstring_pct,
        "max_function_length": max(function_lengths) if function_lengths else 0,
        "max_parameters": max(param_counts) if param_counts else 0,
    }


def _generate_suggestions(report: ProjectReport, files: list[dict]) -> tuple[list[str], list[str]]:
    """Generate missing practice warnings and improvement suggestions."""
    missing = []
    suggestions = []

    if not report.has_tests:
        missing.append("No test suite found (no tests/ directory)")
        suggestions.append(
            "📋 Add a `tests/` directory with unit tests using pytest. "
            "Untested code is hard to refactor safely."
        )

    if not report.has_readme:
        missing.append("No README file found")
        suggestions.append(
            "📖 Add a `README.md` explaining what the project does, how to install it, "
            "and how to run it."
        )

    if not report.dependency_file_found:
        missing.append("No requirements.txt or pyproject.toml found")
        suggestions.append(
            "📦 Add a `requirements.txt` (run `pip freeze > requirements.txt`) "
            "so others can reproduce your environment."
        )

    if not report.has_docs:
        missing.append("No docs/ directory found")
        suggestions.append(
            "📚 Consider adding a `docs/` folder with architecture documentation "
            "or using docstrings + Sphinx for auto-generated docs."
        )

    if not report.has_ci:
        missing.append("No CI/CD configuration found")
        suggestions.append(
            "⚙️ Add a GitHub Actions workflow (`.github/workflows/ci.yml`) "
            "to automatically run tests on every push."
        )

    metrics = report.metrics
    if metrics.get("docstring_coverage_pct", 100) < 50:
        pct = metrics["docstring_coverage_pct"]
        missing.append(f"Low docstring coverage ({pct}% of functions documented)")
        suggestions.append(
            f"✍️ Only {pct}% of functions have docstrings. "
            "Add docstrings to explain what each function does, its parameters, and return values."
        )

    if metrics.get("avg_function_length", 0) > 40:
        avg = metrics["avg_function_length"]
        suggestions.append(
            f"⚡ Average function length is {avg} lines — quite high. "
            "Aim for functions under 30 lines for readability."
        )

    if report.architecture == "Flat / Monolithic (all files in root)":
        suggestions.append(
            "🗂️ Consider organizing code into a `src/` package directory "
            "with submodules by feature/responsibility."
        )

    if report.file_count == 1:
        suggestions.append(
            "📁 The entire project is in one file. "
            "As it grows, split it into modules (e.g., models.py, utils.py, config.py)."
        )

    if not suggestions:
        suggestions.append("✅ No major structural issues found. Keep up the good practices!")

    return missing, suggestions


def _top_n(counts: dict[str, int], n: int) -> list[str]:
    """Return top-N keys by count."""
    return sorted(counts, key=counts.get, reverse=True)[:n]
