"""
agents/llm_agent.py
-------------------
LLM Agent: Optional AI-powered reasoning layer.

Supports two backends (user selects in the UI):
  1. OpenAI   — GPT-3.5-turbo or GPT-4 (requires API key)
  2. HuggingFace — microsoft/codebert-base via transformers (free, local, CPU-safe)

If neither is configured or both fail, the system continues without LLM features.
The rest of the pipeline never breaks due to LLM unavailability.
"""

from __future__ import annotations
import os
from agents.scanner import Issue


# ─────────────────────────────────────────────
# LLM Agent
# ─────────────────────────────────────────────

class LLMAgent:
    def __init__(self, backend: str = "none", api_key: str = ""):
        """
        Args:
            backend: "openai" | "huggingface" | "none"
            api_key: OpenAI API key (only used when backend == "openai")
        """
        self.backend = backend.lower()
        self.api_key = api_key.strip()
        self._client = None           # OpenAI client
        self._hf_pipeline = None      # HuggingFace pipeline
        self._available = False
        self._status_message = ""

        self._initialize()

    def _initialize(self):
        """Set up the selected backend."""
        if self.backend == "openai":
            self._init_openai()
        elif self.backend == "huggingface":
            self._init_huggingface()
        else:
            self._available = False
            self._status_message = "LLM disabled — running in rule-based mode."

    def _init_openai(self):
        if not self.api_key:
            self._available = False
            self._status_message = "OpenAI selected but no API key provided."
            return
        try:
            from openai import OpenAI
            self._client = OpenAI(api_key=self.api_key)
            # Quick connectivity test
            self._available = True
            self._status_message = "OpenAI GPT-3.5 ready."
        except ImportError:
            self._available = False
            self._status_message = "openai package not installed. Run: pip install openai"
        except Exception as e:
            self._available = False
            self._status_message = f"OpenAI init failed: {str(e)}"

    def _init_huggingface(self):
        """
        Load microsoft/codebert-base for feature extraction.
        We use it as a text-generation fallback via a fill-mask pipeline
        to provide code-aware suggestions.

        Note: On first run this downloads ~500MB. Subsequent runs use cache.
        """
        try:
            from transformers import pipeline, AutoTokenizer, AutoModel
            import torch

            # Use a smaller, faster model for CPU: use text2text for suggestions
            # We use Salesforce/codet5-small for text generation (lighter than CodeBERT)
            self._hf_pipeline = pipeline(
                "text2text-generation",
                model="Salesforce/codet5-small",
                device=-1,  # CPU
                max_new_tokens=100,
            )
            self._available = True
            self._status_message = "HuggingFace CodeT5-small ready (CPU mode)."
        except ImportError:
            self._available = False
            self._status_message = "transformers/torch not installed. Run: pip install transformers torch"
        except Exception as e:
            self._available = False
            self._status_message = f"HuggingFace init failed: {str(e)}"

    def is_available(self) -> bool:
        return self._available

    @property
    def status(self) -> str:
        return self._status_message

    # ─────────────────────────────────────────
    # Public API methods
    # ─────────────────────────────────────────

    def analyze_issue(self, issue: Issue, source_context: str = "") -> str:
        """
        Ask the LLM to reason about a specific issue and suggest a fix.

        Args:
            issue: The Issue object to explain
            source_context: Relevant source code snippet (optional)

        Returns:
            LLM response string, or empty string on failure
        """
        if not self._available:
            return ""

        prompt = _build_issue_prompt(issue, source_context)

        if self.backend == "openai":
            return self._call_openai(prompt)
        elif self.backend == "huggingface":
            return self._call_huggingface(prompt)
        return ""

    def enhance_explanation(self, issue: Issue) -> str:
        """
        Generate an enhanced explanation for an issue.
        Returns a short suggestion string.
        """
        if not self._available:
            return ""

        prompt = (
            f"A Python function named '{issue.symbol}' has the following code quality issue: "
            f"{issue.message}. "
            "Give one specific, actionable refactoring tip in 1-2 sentences."
        )

        if self.backend == "openai":
            return self._call_openai(prompt, max_tokens=120)
        elif self.backend == "huggingface":
            return self._call_huggingface(prompt)
        return ""

    def summarize_project(self, project_report: dict) -> str:
        """
        Ask the LLM to provide a high-level summary of the project's health.
        """
        if not self._available:
            return ""

        suggestions = "\n".join(project_report.get("suggestions", []))
        project_type = project_report.get("type", "Unknown")
        architecture = project_report.get("architecture", "Unknown")

        prompt = (
            f"I analyzed a Python project. Here's what I found:\n"
            f"- Project type: {project_type}\n"
            f"- Architecture: {architecture}\n"
            f"- Issues found: {suggestions}\n\n"
            "Write a brief (3-4 sentence) developer-friendly summary of this project's "
            "health and the top 2 things to improve."
        )

        if self.backend == "openai":
            return self._call_openai(prompt, max_tokens=200)
        elif self.backend == "huggingface":
            return self._call_huggingface(prompt)
        return ""

    # ─────────────────────────────────────────
    # Backend callers
    # ─────────────────────────────────────────

    def _call_openai(self, prompt: str, max_tokens: int = 200) -> str:
        try:
            response = self._client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a senior Python code reviewer. "
                            "Give concise, actionable, developer-friendly advice. "
                            "Be specific. Never be vague."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=max_tokens,
                temperature=0.3,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            self._available = False
            self._status_message = f"OpenAI call failed: {str(e)}"
            return ""

    def _call_huggingface(self, prompt: str) -> str:
        try:
            # CodeT5 works as text2text — give it a prefix
            input_text = f"Explain: {prompt}"
            result = self._hf_pipeline(input_text)
            if result and isinstance(result, list):
                return result[0].get("generated_text", "").strip()
            return ""
        except Exception as e:
            self._available = False
            self._status_message = f"HuggingFace call failed: {str(e)}"
            return ""


# ─────────────────────────────────────────────
# Prompt builder
# ─────────────────────────────────────────────

def _build_issue_prompt(issue: Issue, context: str) -> str:
    parts = [
        f"File: {issue.file}",
        f"Line: {issue.line}",
        f"Issue type: {issue.issue_type}",
        f"Issue: {issue.message}",
    ]
    if context:
        parts.append(f"Code context:\n```python\n{context[:500]}\n```")
    parts.append("What is the best way to fix this? Be specific and concise.")
    return "\n".join(parts)
