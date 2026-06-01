"""
agents/coordinator.py
---------------------
Coordinator Agent: Orchestrates the full CodeAid analysis pipeline.

Pipeline order:
  1. Scanner      — detect issues in all files
  2. Repair       — apply safe fixes (unused imports)
  3. Verifier     — confirm repaired files still compile
  4. Explain      — generate human-readable explanations
  5. Project      — analyze repository-level structure

The coordinator collects all outputs into a single structured result dict
that the Streamlit UI consumes.

Error isolation: if any agent raises an unexpected exception, the coordinator
catches it, logs it, and continues with the remaining agents.
"""

from __future__ import annotations
from typing import Callable, Optional

from agents.scanner import ScannerAgent, summarize_results
from agents.repair import RepairAgent
from agents.verifier import VerifierAgent
from agents.explain import ExplainAgent, group_explanations_by_file
from agents.project_understanding import ProjectUnderstandingAgent
from agents.llm_agent import LLMAgent


# ─────────────────────────────────────────────
# Coordinator
# ─────────────────────────────────────────────

class Coordinator:
    def __init__(
        self,
        llm_backend: str = "none",
        openai_key: str = "",
        scanner_config: dict = None,
        progress_callback: Optional[Callable[[str, float], None]] = None,
    ):
        """
        Args:
            llm_backend:       "openai" | "huggingface" | "none"
            openai_key:        API key string (only used for openai backend)
            scanner_config:    Optional thresholds for scanner (max lines, params, etc.)
            progress_callback: Optional fn(message, fraction) for UI progress bar
        """
        self.scanner_config = scanner_config or {}
        self.progress_cb = progress_callback or (lambda msg, pct: None)

        # Initialize agents
        self.llm = LLMAgent(backend=llm_backend, api_key=openai_key)
        self.scanner = ScannerAgent(config=self.scanner_config)
        self.repair = RepairAgent()
        self.verifier = VerifierAgent()
        self.explainer = ExplainAgent(llm_agent=self.llm)
        self.project = ProjectUnderstandingAgent()

    def run(self, files: list[dict], extra_files: dict[str, str] = None) -> dict:
        """
        Run the full analysis pipeline.

        Args:
            files:       [{"path": str, "source": str}] — Python source files
            extra_files: {filename: content} — non-Python files (README, requirements, etc.)

        Returns:
            A structured dict containing all results for the UI.
        """
        extra_files = extra_files or {}
        errors = []

        # ── Stage 1: Scan ─────────────────────────────────────────
        self.progress_cb("🔍 Scanning files for issues...", 0.1)
        try:
            scan_results = self.scanner.scan_files(files)
            scan_summary = summarize_results(scan_results)
        except Exception as e:
            errors.append(f"Scanner failed: {str(e)}")
            scan_results = []
            scan_summary = {}

        # ── Stage 2: Repair ───────────────────────────────────────
        self.progress_cb("🔧 Applying safe repairs...", 0.35)
        try:
            repair_results = self.repair.repair_files(files, scan_results)
        except Exception as e:
            errors.append(f"Repair agent failed: {str(e)}")
            repair_results = []

        # ── Stage 3: Verify ───────────────────────────────────────
        self.progress_cb("✅ Verifying repaired code...", 0.55)
        try:
            verification_results = self.verifier.verify_repairs(repair_results)
        except Exception as e:
            errors.append(f"Verifier failed: {str(e)}")
            verification_results = []

        # ── Stage 4: Explain ──────────────────────────────────────
        self.progress_cb("💬 Generating explanations...", 0.70)
        try:
            explanations = self.explainer.explain_all(scan_results)
            explanations_by_file = group_explanations_by_file(explanations)
        except Exception as e:
            errors.append(f"Explain agent failed: {str(e)}")
            explanations = []
            explanations_by_file = {}

        # ── Stage 5: Project Understanding ────────────────────────
        self.progress_cb("📊 Analyzing project structure...", 0.85)
        try:
            project_report = self.project.analyze(
                files=files,
                extra_files=extra_files,
                llm_agent=self.llm,
            )
        except Exception as e:
            errors.append(f"Project understanding agent failed: {str(e)}")
            project_report = None

        self.progress_cb("✨ Analysis complete!", 1.0)

        # ── Build final result ────────────────────────────────────
        return {
            "files": files,
            "scan_results": scan_results,
            "scan_summary": scan_summary,
            "repair_results": repair_results,
            "verification_results": verification_results,
            "explanations": explanations,
            "explanations_by_file": explanations_by_file,
            "project_report": project_report,
            "llm_status": self.llm.status,
            "llm_available": self.llm.is_available(),
            "pipeline_errors": errors,
        }
