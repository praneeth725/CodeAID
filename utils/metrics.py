"""
utils/metrics.py
----------------
Evaluation metrics for CodeAid's issue detection and repair quality.

Metrics implemented:
  - Precision, Recall, F1 score  (for issue detection accuracy)
  - Exact Match Accuracy          (for repair quality)
  - CodeBLEU (simplified)         (for repair quality, code-aware)
  - Per-type breakdown            (precision/recall per issue type)

These are used in the CodeXGLUE evaluation module and the dashboard's
Metrics tab.
"""

from __future__ import annotations
import re
from collections import defaultdict


# ─────────────────────────────────────────────
# Classification metrics
# ─────────────────────────────────────────────

def precision(tp: int, fp: int) -> float:
    """Precision = TP / (TP + FP). Returns 0.0 if denominator is 0."""
    if tp + fp == 0:
        return 0.0
    return round(tp / (tp + fp), 4)


def recall(tp: int, fn: int) -> float:
    """Recall = TP / (TP + FN). Returns 0.0 if denominator is 0."""
    if tp + fn == 0:
        return 0.0
    return round(tp / (tp + fn), 4)


def f1_score(prec: float, rec: float) -> float:
    """F1 = 2 * (Precision * Recall) / (Precision + Recall)."""
    if prec + rec == 0:
        return 0.0
    return round(2 * prec * rec / (prec + rec), 4)


def compute_classification_metrics(
    predicted: list[dict],
    ground_truth: list[dict],
    key_fields: list[str] = ("file", "line", "issue_type"),
) -> dict:
    """
    Compute precision, recall, and F1 for issue detection.

    Args:
        predicted:    List of predicted issue dicts (from scanner)
        ground_truth: List of ground-truth issue dicts (from benchmark)
        key_fields:   Fields that together uniquely identify an issue

    Returns:
        Dict with tp, fp, fn, precision, recall, f1
    """
    def to_key(item):
        return tuple(str(item.get(f, "")) for f in key_fields)

    predicted_keys = set(to_key(p) for p in predicted)
    truth_keys = set(to_key(g) for g in ground_truth)

    tp = len(predicted_keys & truth_keys)
    fp = len(predicted_keys - truth_keys)
    fn = len(truth_keys - predicted_keys)

    prec = precision(tp, fp)
    rec = recall(tp, fn)
    f1 = f1_score(prec, rec)

    return {
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn,
        "precision": prec,
        "recall": rec,
        "f1": f1,
    }


def compute_per_type_metrics(
    predicted: list[dict],
    ground_truth: list[dict],
) -> dict[str, dict]:
    """
    Compute precision/recall/F1 broken down by issue_type.

    Returns:
        {issue_type: {precision, recall, f1, tp, fp, fn}, ...}
    """
    # Group by issue type
    pred_by_type = defaultdict(list)
    truth_by_type = defaultdict(list)

    all_types = set()

    for item in predicted:
        t = item.get("issue_type", "Unknown")
        pred_by_type[t].append(item)
        all_types.add(t)

    for item in ground_truth:
        t = item.get("issue_type", "Unknown")
        truth_by_type[t].append(item)
        all_types.add(t)

    results = {}
    for issue_type in all_types:
        results[issue_type] = compute_classification_metrics(
            pred_by_type.get(issue_type, []),
            truth_by_type.get(issue_type, []),
        )

    return results


# ─────────────────────────────────────────────
# Repair quality metrics
# ─────────────────────────────────────────────

def exact_match_accuracy(predictions: list[str], references: list[str]) -> float:
    """
    Exact match: what fraction of predictions exactly equal the reference.

    Args:
        predictions: List of repaired code strings
        references:  List of ground-truth fixed code strings

    Returns:
        Accuracy in [0.0, 1.0]
    """
    if not predictions or len(predictions) != len(references):
        return 0.0
    matches = sum(1 for p, r in zip(predictions, references) if p.strip() == r.strip())
    return round(matches / len(predictions), 4)


def token_overlap_score(prediction: str, reference: str) -> float:
    """
    Simplified token-level overlap (similar in spirit to CodeBLEU's n-gram match).
    Computes unigram F1 between tokenized prediction and reference.

    Tokenization: split on whitespace and punctuation.
    """
    pred_tokens = set(_tokenize(prediction))
    ref_tokens = set(_tokenize(reference))

    if not pred_tokens or not ref_tokens:
        return 0.0

    intersection = pred_tokens & ref_tokens
    prec = len(intersection) / len(pred_tokens)
    rec = len(intersection) / len(ref_tokens)
    return round(f1_score(prec, rec), 4)


def compute_repair_metrics(
    predictions: list[str],
    references: list[str],
) -> dict:
    """
    Compute all repair quality metrics.

    Returns:
        {exact_match, avg_token_overlap, count}
    """
    if not predictions or len(predictions) != len(references):
        return {"exact_match": 0.0, "avg_token_overlap": 0.0, "count": 0}

    em = exact_match_accuracy(predictions, references)
    overlaps = [token_overlap_score(p, r) for p, r in zip(predictions, references)]
    avg_overlap = round(sum(overlaps) / len(overlaps), 4) if overlaps else 0.0

    return {
        "exact_match": em,
        "avg_token_overlap": avg_overlap,
        "count": len(predictions),
    }


# ─────────────────────────────────────────────
# Helper
# ─────────────────────────────────────────────

def _tokenize(text: str) -> list[str]:
    """Simple tokenizer: split on non-alphanumeric characters."""
    return re.findall(r"[a-zA-Z0-9_]+", text.lower())


# ─────────────────────────────────────────────
# Summary builder for UI display
# ─────────────────────────────────────────────

def build_metrics_display(scan_results, repair_results, verification_results) -> dict:
    """
    Build a metrics dict for the dashboard from pipeline outputs.
    No ground truth needed — uses internal statistics.
    """
    from agents.scanner import summarize_results

    summary = summarize_results(scan_results)

    repairs_applied = sum(len(r.repairs_applied) for r in repair_results)
    repairs_skipped = sum(len(r.repairs_skipped) for r in repair_results)
    files_modified = sum(1 for r in repair_results if r.was_modified)

    verifications_passed = sum(1 for v in verification_results if v.passed)
    verifications_total = len(verification_results)

    return {
        "scan": summary,
        "repairs": {
            "applied": repairs_applied,
            "skipped": repairs_skipped,
            "files_modified": files_modified,
        },
        "verification": {
            "passed": verifications_passed,
            "total": verifications_total,
            "pass_rate": round(verifications_passed / verifications_total, 4) if verifications_total else 0,
        },
    }
