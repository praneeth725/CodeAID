"""
agents/scanner.py
-----------------
Scanner Agent: Performs AST-based static analysis on Python source files.

Detects:
  1. Syntax Errors          — file fails to parse
  2. Unused Imports         — imported names never referenced (fixed: handles
                              attribute access like os.path, json.dumps, etc.)
  3. Long Functions         — functions exceeding line threshold
  4. Too Many Parameters    — functions with too many arguments
  5. TODO / FIXME Comments  — technical debt markers in comments

BUG FIXED (from original design):
  The original approach only checked ast.Name nodes for import usage,
  missing cases like `import os; os.path.join(...)` where `os` appears
  as ast.Attribute, not ast.Name. This version collects ALL name roots
  from the full AST including attribute chains.
"""

import ast
import re
from dataclasses import dataclass, field
from typing import Optional


# ─────────────────────────────────────────────
# Data structures
# ─────────────────────────────────────────────

@dataclass
class Issue:
    file: str
    line: Optional[int]
    issue_type: str          # "SyntaxError" | "UnusedImport" | "LongFunction" | "ManyParameters" | "TodoComment"
    message: str
    severity: str            # "error" | "warning" | "info"
    symbol: Optional[str] = None   # function name, import name, etc.


@dataclass
class ScanResult:
    file: str
    issues: list[Issue] = field(default_factory=list)
    parsed_ok: bool = True
    line_count: int = 0
    function_count: int = 0
    class_count: int = 0


# ─────────────────────────────────────────────
# Configuration (tunable thresholds)
# ─────────────────────────────────────────────

DEFAULT_CONFIG = {
    "max_function_lines": 60,
    "max_parameters": 7,
    "todo_patterns": ["TODO", "FIXME", "HACK", "XXX", "BUG"],
}


# ─────────────────────────────────────────────
# Scanner Agent
# ─────────────────────────────────────────────

class ScannerAgent:
    def __init__(self, config: dict = None):
        self.config = {**DEFAULT_CONFIG, **(config or {})}

    def scan_files(self, files: list[dict]) -> list[ScanResult]:
        """
        Scan a list of file dicts (each has 'path' and 'source').
        Returns a list of ScanResult objects.
        """
        results = []
        for f in files:
            result = self._scan_single(f["path"], f["source"])
            results.append(result)
        return results

    def _scan_single(self, filepath: str, source: str) -> ScanResult:
        result = ScanResult(file=filepath)
        lines = source.splitlines()
        result.line_count = len(lines)

        # ── Step 1: Parse into AST ──────────────────────────────
        try:
            tree = ast.parse(source, filename=filepath)
        except SyntaxError as e:
            result.parsed_ok = False
            result.issues.append(Issue(
                file=filepath,
                line=e.lineno,
                issue_type="SyntaxError",
                message=f"Syntax error: {e.msg}",
                severity="error",
            ))
            # Still scan TODO comments even if syntax is broken
            result.issues.extend(self._detect_todos(filepath, lines))
            return result

        # ── Step 2: Collect all referenced name roots ────────────
        # This fixes the original bug: we collect names from Name nodes AND
        # the root of attribute chains (e.g. os.path.join → root is 'os')
        used_names = _collect_all_used_names(tree)

        # ── Step 3: Collect imported names ───────────────────────
        imported = _collect_imports(tree)

        # ── Step 4: Detect unused imports ────────────────────────
        for alias, (import_line, original) in imported.items():
            if alias not in used_names:
                result.issues.append(Issue(
                    file=filepath,
                    line=import_line,
                    issue_type="UnusedImport",
                    message=f"Import '{original}' is imported but never used.",
                    severity="warning",
                    symbol=alias,
                ))

        # ── Step 5: Detect long functions & too many parameters ──
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                result.function_count += 1
                self._check_function(filepath, node, result)
            elif isinstance(node, ast.ClassDef):
                result.class_count += 1

        # ── Step 6: Detect TODO/FIXME comments ───────────────────
        result.issues.extend(self._detect_todos(filepath, lines))

        return result

    def _check_function(self, filepath: str, node: ast.FunctionDef, result: ScanResult):
        """Check a single function for length and parameter count issues."""
        func_name = node.name
        start = node.lineno
        end = getattr(node, "end_lineno", start)
        length = end - start + 1

        if length > self.config["max_function_lines"]:
            result.issues.append(Issue(
                file=filepath,
                line=start,
                issue_type="LongFunction",
                message=(
                    f"Function '{func_name}' is {length} lines long "
                    f"(threshold: {self.config['max_function_lines']} lines). "
                    "Consider splitting into smaller functions."
                ),
                severity="warning",
                symbol=func_name,
            ))

        # Count all parameter types: regular, pos-only, kw-only (exclude self/cls)
        args = node.args
        all_params = (
            args.posonlyargs
            + args.args
            + args.kwonlyargs
            + ([args.vararg] if args.vararg else [])
            + ([args.kwarg] if args.kwarg else [])
        )
        # Drop 'self' and 'cls' from instance/class methods
        filtered = [a for a in all_params if a.arg not in ("self", "cls")]
        param_count = len(filtered)

        if param_count > self.config["max_parameters"]:
            result.issues.append(Issue(
                file=filepath,
                line=start,
                issue_type="ManyParameters",
                message=(
                    f"Function '{func_name}' has {param_count} parameters "
                    f"(threshold: {self.config['max_parameters']}). "
                    "Consider using a dataclass or config object."
                ),
                severity="warning",
                symbol=func_name,
            ))

    def _detect_todos(self, filepath: str, lines: list[str]) -> list[Issue]:
        """Scan source lines for TODO/FIXME style comments."""
        issues = []
        pattern = re.compile(
            r"#.*\b(" + "|".join(self.config["todo_patterns"]) + r")\b",
            re.IGNORECASE,
        )
        for i, line in enumerate(lines, start=1):
            match = pattern.search(line)
            if match:
                tag = match.group(1).upper()
                comment_text = line.strip().lstrip("#").strip()
                issues.append(Issue(
                    file=filepath,
                    line=i,
                    issue_type="TodoComment",
                    message=f"{tag} comment found: \"{comment_text}\"",
                    severity="info",
                    symbol=tag,
                ))
        return issues


# ─────────────────────────────────────────────
# AST helper functions
# ─────────────────────────────────────────────

def _collect_all_used_names(tree: ast.AST) -> set[str]:
    """
    Collect every name that is actually *used* in the code — not just declared.

    FIXED BUG: The original design only looked at ast.Name nodes.
    This misses attribute access patterns:
        import os
        os.path.join(...)   → os is ast.Attribute value, not ast.Name at top level

    We fix this by also walking ast.Attribute nodes and collecting the
    root name of any attribute chain.

    We also exclude:
      - Names that appear only on the left side of an import alias definition
      - Names in Import/ImportFrom nodes (those are definitions, not uses)
    """
    used = set()

    for node in ast.walk(tree):
        # Direct name reference: x, foo, etc.
        if isinstance(node, ast.Name):
            used.add(node.id)

        # Attribute access root: os.path.join → 'os'
        elif isinstance(node, ast.Attribute):
            root = _get_attribute_root(node)
            if root:
                used.add(root)

    return used


def _get_attribute_root(node: ast.Attribute) -> Optional[str]:
    """
    Walk down an attribute chain to find the root Name.
    e.g.  os.path.join  →  root is 'os'
          self.x.y      →  root is 'self'
    """
    current = node
    while isinstance(current, ast.Attribute):
        current = current.value
    if isinstance(current, ast.Name):
        return current.id
    return None


def _collect_imports(tree: ast.AST) -> dict[str, tuple[int, str]]:
    """
    Collect all imported names from the AST.
    Returns: {alias_name: (line_number, original_name_string)}

    Handles:
      import os                    → {'os': (1, 'os')}
      import os.path               → {'os': (1, 'os.path')}   (root is 'os')
      import numpy as np           → {'np': (1, 'numpy')}
      from os import path          → {'path': (1, 'os.path')}
      from os import path as p     → {'p': (1, 'os.path')}
      from os.path import join     → {'join': (1, 'os.path.join')}
      from __future__ import ...   → skipped
    """
    imports = {}

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                # 'import os.path' → the usable name in code is 'os' (the root)
                # 'import numpy as np' → usable name is 'np'
                if alias.asname:
                    key = alias.asname
                else:
                    key = alias.name.split(".")[0]
                imports[key] = (node.lineno, alias.name)

        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module == "__future__":
                continue
            for alias in node.names:
                if alias.name == "*":
                    # Wildcard import — we can't track usage, skip
                    continue
                key = alias.asname if alias.asname else alias.name
                full = f"{module}.{alias.name}" if module else alias.name
                imports[key] = (node.lineno, full)

    return imports


# ─────────────────────────────────────────────
# Convenience summary builder
# ─────────────────────────────────────────────

def summarize_results(results: list[ScanResult]) -> dict:
    """Build a summary dict from all scan results for display."""
    total_issues = sum(len(r.issues) for r in results)
    by_type = {}
    for r in results:
        for issue in r.issues:
            by_type[issue.issue_type] = by_type.get(issue.issue_type, 0) + 1

    files_with_issues = sum(1 for r in results if r.issues)
    total_lines = sum(r.line_count for r in results)
    total_functions = sum(r.function_count for r in results)
    total_classes = sum(r.class_count for r in results)
    syntax_errors = sum(1 for r in results if not r.parsed_ok)

    return {
        "total_files": len(results),
        "files_with_issues": files_with_issues,
        "total_issues": total_issues,
        "total_lines": total_lines,
        "total_functions": total_functions,
        "total_classes": total_classes,
        "syntax_errors": syntax_errors,
        "by_type": by_type,
    }
