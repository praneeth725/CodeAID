"""
agents/repair.py
----------------
Repair Agent: Applies safe, targeted fixes to issues found by the Scanner.

Repairs implemented:
  - UnusedImport: Removes unused import lines from source code
  - LongFunction:  No auto-repair — generates a refactoring suggestion comment
  - ManyParameters: No auto-repair — generates a suggestion comment
  - TodoComment:   No auto-repair — logged as-is (it's developer intent)
  - SyntaxError:   No auto-repair — flagged for manual fix

Design principle: Only perform repairs that are guaranteed to be semantically
safe. Anything that could alter program behavior is left for the developer.
"""

import ast
import textwrap
from agents.scanner import Issue, ScanResult


# ─────────────────────────────────────────────
# Repair result data structure
# ─────────────────────────────────────────────

class RepairResult:
    def __init__(self, filepath: str, original: str):
        self.file = filepath
        self.original_source = original
        self.repaired_source = original
        self.repairs_applied: list[str] = []
        self.repairs_skipped: list[str] = []
        self.was_modified = False

    @property
    def diff_summary(self) -> str:
        orig_lines = self.original_source.splitlines()
        new_lines = self.repaired_source.splitlines()
        removed = len(orig_lines) - len(new_lines)
        if removed > 0:
            return f"{removed} line(s) removed"
        elif removed < 0:
            return f"{abs(removed)} line(s) added"
        return "No line count change"


# ─────────────────────────────────────────────
# Repair Agent
# ─────────────────────────────────────────────

class RepairAgent:
    def repair_files(
        self,
        files: list[dict],
        scan_results: list[ScanResult],
    ) -> list[RepairResult]:
        """
        Apply repairs to all files.

        Args:
            files: Original file list [{"path": str, "source": str}]
            scan_results: Output from ScannerAgent

        Returns:
            List of RepairResult objects
        """
        # Build a lookup: filepath → source
        source_map = {f["path"]: f["source"] for f in files}

        # Build a lookup: filepath → list of issues
        issues_map: dict[str, list[Issue]] = {}
        for sr in scan_results:
            issues_map[sr.file] = sr.issues

        results = []
        for filepath, source in source_map.items():
            issues = issues_map.get(filepath, [])
            result = self._repair_single(filepath, source, issues)
            results.append(result)

        return results

    def _repair_single(
        self,
        filepath: str,
        source: str,
        issues: list[Issue],
    ) -> RepairResult:
        result = RepairResult(filepath, source)

        if not issues:
            return result

        # Group issues by type
        unused_imports = [i for i in issues if i.issue_type == "UnusedImport"]
        long_functions = [i for i in issues if i.issue_type == "LongFunction"]
        many_params = [i for i in issues if i.issue_type == "ManyParameters"]
        syntax_errors = [i for i in issues if i.issue_type == "SyntaxError"]

        # ── Cannot repair syntax errors ───────────────────────────
        for issue in syntax_errors:
            result.repairs_skipped.append(
                f"Line {issue.line}: Syntax error must be fixed manually — {issue.message}"
            )

        # ── Repair: Remove unused imports ─────────────────────────
        if unused_imports:
            repaired, removed_lines = _remove_unused_imports(source, unused_imports)
            if removed_lines:
                result.repaired_source = repaired
                result.was_modified = True
                for line_num, name in removed_lines:
                    result.repairs_applied.append(
                        f"Line {line_num}: Removed unused import '{name}'"
                    )

        # ── Suggest (no auto-repair): Long functions ───────────────
        for issue in long_functions:
            result.repairs_skipped.append(
                f"Line {issue.line}: '{issue.symbol}' is too long — "
                "manual refactoring required (cannot auto-split functions safely)"
            )

        # ── Suggest (no auto-repair): Too many parameters ──────────
        for issue in many_params:
            result.repairs_skipped.append(
                f"Line {issue.line}: '{issue.symbol}' has too many parameters — "
                "consider a dataclass or config object (cannot auto-refactor safely)"
            )

        return result


# ─────────────────────────────────────────────
# Internal repair functions
# ─────────────────────────────────────────────

def _remove_unused_imports(source: str, issues: list[Issue]) -> tuple[str, list[tuple[int, str]]]:
    """
    Remove lines containing unused imports.

    Strategy:
      1. Collect the line numbers of unused imports from issues
      2. Parse the AST to find the exact import nodes at those lines
      3. Rebuild source excluding those specific import lines

    This is line-based (not AST-unparse based) to preserve all formatting,
    comments, and encoding of the rest of the file.

    Returns:
        (new_source, [(line_number, import_name), ...])
    """
    # Map line number → symbol name from issues
    lines_to_remove: dict[int, str] = {}
    for issue in issues:
        if issue.line is not None:
            lines_to_remove[issue.line] = issue.symbol or "unknown"

    if not lines_to_remove:
        return source, []

    # Parse to find actual import node spans (some imports span multiple lines)
    try:
        tree = ast.parse(source)
    except SyntaxError:
        # If we can't parse, don't touch the file
        return source, []

    # Find line ranges for import nodes that match our flagged lines
    import_line_ranges: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            node_start = node.lineno
            node_end = getattr(node, "end_lineno", node.lineno)
            if node_start in lines_to_remove:
                for ln in range(node_start, node_end + 1):
                    import_line_ranges.add(ln)

    if not import_line_ranges:
        return source, []

    # Rebuild source without those lines
    original_lines = source.splitlines(keepends=True)
    new_lines = []
    for i, line in enumerate(original_lines, start=1):
        if i not in import_line_ranges:
            new_lines.append(line)

    new_source = "".join(new_lines)

    # Strip leading blank lines that may result from removal
    new_source = _clean_leading_blanks(new_source)

    removed = [(ln, name) for ln, name in lines_to_remove.items() if ln in import_line_ranges]
    removed.sort(key=lambda x: x[0])

    return new_source, removed


def _clean_leading_blanks(source: str) -> str:
    """Remove excessive consecutive blank lines (max 2 in a row)."""
    lines = source.splitlines(keepends=True)
    result = []
    blank_count = 0
    for line in lines:
        if line.strip() == "":
            blank_count += 1
            if blank_count <= 2:
                result.append(line)
        else:
            blank_count = 0
            result.append(line)
    return "".join(result)
