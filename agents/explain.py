"""
agents/explain.py
-----------------
Explanation Agent: Generates human-readable explanations for each detected issue.

Two modes:
  1. Template mode (always available, no API required)
     → Pre-written, informative explanations per issue type
  2. LLM-enhanced mode (optional, if LLM agent is configured)
     → Richer, context-aware explanations via LLM

The agent always falls back to template mode if LLM is unavailable.
"""

from agents.scanner import Issue, ScanResult


# ─────────────────────────────────────────────
# Explanation templates
# ─────────────────────────────────────────────

_TEMPLATES = {
    "SyntaxError": (
        "🔴 **Syntax Error** in `{file}` at line {line}.\n\n"
        "{message}\n\n"
        "**Why it matters:** Python cannot parse or run this file until the syntax error is resolved. "
        "This must be fixed manually — it's likely a missing colon, bracket, or indentation issue."
    ),
    "UnusedImport": (
        "🟡 **Unused Import** in `{file}` at line {line}.\n\n"
        "{message}\n\n"
        "**Why it matters:** Unused imports increase load time, clutter the namespace, "
        "and confuse readers into thinking the module is actually used. "
        "**Fix:** Remove this import, or use it somewhere in the file."
    ),
    "LongFunction": (
        "🟠 **Long Function** in `{file}` at line {line}.\n\n"
        "{message}\n\n"
        "**Why it matters:** Long functions are harder to read, test, and maintain. "
        "They tend to violate the Single Responsibility Principle. "
        "**Fix:** Break the function into smaller, well-named helper functions, "
        "each handling one specific task."
    ),
    "ManyParameters": (
        "🟠 **Too Many Parameters** in `{file}` at line {line}.\n\n"
        "{message}\n\n"
        "**Why it matters:** Functions with many parameters are hard to call correctly "
        "and easy to misuse (wrong argument order, etc.). "
        "**Fix:** Group related parameters into a dataclass or dictionary, "
        "or split the function into smaller ones with fewer responsibilities."
    ),
    "TodoComment": (
        "🔵 **Technical Debt Marker** in `{file}` at line {line}.\n\n"
        "{message}\n\n"
        "**Why it matters:** TODO/FIXME comments indicate incomplete work or known issues "
        "that have been deferred. Over time, these accumulate into significant technical debt. "
        "**Fix:** Track this in your issue tracker and resolve it before shipping."
    ),
}

_SHORT_DESCRIPTIONS = {
    "SyntaxError":    "File cannot be parsed — fix the syntax error before anything else.",
    "UnusedImport":   "This import is never referenced anywhere in the file.",
    "LongFunction":   "This function is too long — consider splitting it.",
    "ManyParameters": "This function has too many parameters — consider grouping them.",
    "TodoComment":    "Unresolved technical debt marker found in a comment.",
}


# ─────────────────────────────────────────────
# Explanation data structure
# ─────────────────────────────────────────────

class Explanation:
    def __init__(self, issue: Issue, text: str, short: str):
        self.issue = issue
        self.full_text = text        # Markdown-formatted full explanation
        self.short_text = short      # One-liner for tables


# ─────────────────────────────────────────────
# Explanation Agent
# ─────────────────────────────────────────────

class ExplainAgent:
    def __init__(self, llm_agent=None):
        """
        Args:
            llm_agent: Optional LLMAgent instance. If provided and available,
                       used to generate enhanced explanations for complex issues.
        """
        self.llm = llm_agent

    def explain_all(self, scan_results: list[ScanResult]) -> list[Explanation]:
        """Generate explanations for all issues across all scanned files."""
        explanations = []
        for sr in scan_results:
            for issue in sr.issues:
                explanation = self._explain_issue(issue)
                explanations.append(explanation)
        return explanations

    def _explain_issue(self, issue: Issue) -> Explanation:
        """Generate an explanation for a single issue."""
        template = _TEMPLATES.get(issue.issue_type, "Issue detected: {message}")
        short = _SHORT_DESCRIPTIONS.get(issue.issue_type, issue.message)

        full_text = template.format(
            file=issue.file,
            line=issue.line or "N/A",
            message=issue.message,
            symbol=issue.symbol or "",
        )

        # Optional: enhance with LLM for complex issues
        if self.llm and self.llm.is_available() and issue.issue_type in ("LongFunction", "ManyParameters"):
            try:
                enhanced = self.llm.enhance_explanation(issue)
                if enhanced:
                    full_text += f"\n\n**AI Suggestion:** {enhanced}"
            except Exception:
                pass  # Silently fall back to template

        return Explanation(issue=issue, text=full_text, short=short)


def group_explanations_by_file(explanations: list[Explanation]) -> dict[str, list[Explanation]]:
    """Group a flat list of explanations by file path."""
    grouped = {}
    for exp in explanations:
        key = exp.issue.file
        grouped.setdefault(key, []).append(exp)
    return grouped
