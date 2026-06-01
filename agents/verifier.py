"""
agents/verifier.py
------------------
Verifier Agent: Confirms that repaired source code is still syntactically valid.

Uses Python's built-in compile() to check for syntax errors without executing
any code. If verification fails for a file, the repair is marked as unsafe.

Safety guarantee: No user code is ever executed — only parsed/compiled.
"""

import ast
from dataclasses import dataclass, field
from agents.repair import RepairResult


# ─────────────────────────────────────────────
# Data structure
# ─────────────────────────────────────────────

@dataclass
class VerificationResult:
    file: str
    passed: bool
    error_message: str = ""
    error_line: int = None


# ─────────────────────────────────────────────
# Verifier Agent
# ─────────────────────────────────────────────

class VerifierAgent:
    def verify_repairs(self, repair_results: list[RepairResult]) -> list[VerificationResult]:
        """
        Verify all repaired files.
        For unmodified files, verification is skipped (marked as passed).

        Returns a list of VerificationResult objects.
        """
        results = []
        for repair in repair_results:
            if not repair.was_modified:
                # File wasn't changed — no need to verify
                results.append(VerificationResult(
                    file=repair.file,
                    passed=True,
                    error_message="No repairs applied — verification skipped.",
                ))
                continue

            vr = self._verify_source(repair.file, repair.repaired_source)

            if not vr.passed:
                # Safety: roll back the repair if verification fails
                repair.repaired_source = repair.original_source
                repair.was_modified = False
                repair.repairs_applied.clear()
                repair.repairs_skipped.insert(
                    0,
                    f"⚠ Repair rolled back: verification failed — {vr.error_message}"
                )

            results.append(vr)

        return results

    def _verify_source(self, filepath: str, source: str) -> VerificationResult:
        """
        Attempt to compile source code. Returns a VerificationResult.
        Uses ast.parse (equivalent to compile with PyCF_ONLY_AST) — safe, no execution.
        """
        try:
            compile(source, filepath, "exec", ast.PyCF_ONLY_AST)
            return VerificationResult(file=filepath, passed=True)
        except SyntaxError as e:
            return VerificationResult(
                file=filepath,
                passed=False,
                error_message=f"Syntax error after repair: {e.msg}",
                error_line=e.lineno,
            )
        except Exception as e:
            return VerificationResult(
                file=filepath,
                passed=False,
                error_message=f"Unexpected error during verification: {str(e)}",
            )
