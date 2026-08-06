from __future__ import annotations

from typing import Any

from core.utils import now_utc, write_text

METRIC_LABELS = {
    "samples": "Evaluation samples",
    "retrieval_hit_rate": "Retrieval hit rate",
    "mean_token_f1": "Mean token F1",
    "judge_accuracy": "Judge accuracy",
    "mean_judge_score": "Mean judge score (1-5)",
}


def _format_value(value: Any) -> str:
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, float):
        return f"{value:.3f}"
    if isinstance(value, (list, tuple)):
        return ", ".join(str(item) for item in value) if value else "-"
    if value is None or value == "":
        return "-"
    return str(value)


def _kv_table(payload: dict[str, Any], key_header: str = "Field", value_header: str = "Value") -> list[str]:
    lines = [f"| {key_header} | {value_header} |", "| --- | --- |"]
    for key, value in payload.items():
        if isinstance(value, dict):
            continue
        lines.append(f"| {key} | {_format_value(value)} |")
    return lines


def _metrics_section(metrics: dict[str, Any]) -> list[str]:
    lines = ["| Metric | Value |", "| --- | --- |"]
    for key, label in METRIC_LABELS.items():
        if key in metrics:
            lines.append(f"| {label} | {_format_value(metrics[key])} |")

    ragas = metrics.get("ragas")
    if isinstance(ragas, dict) and ragas:
        lines.extend(["", "Ragas:", "", *_kv_table(ragas, key_header="Ragas metric")])
    return lines


def _quality_section(quality: dict[str, Any]) -> list[str]:
    statistics = quality.get("statistics", {})
    status = "PASS" if quality.get("success") else "FAIL"
    lines = [
        f"Overall status: **{status}** "
        f"({statistics.get('successful_expectations', 0)}/{statistics.get('evaluated_expectations', 0)} expectations passed)",
        "",
        f"Engine: {quality.get('engine', 'n/a')} | rows checked: {quality.get('row_count', 0)}",
        "",
        "| Expectation | Column | Result | Unexpected | Observed |",
        "| --- | --- | --- | --- | --- |",
    ]
    for check in quality.get("checks", []):
        lines.append(
            f"| {check.get('expectation')} "
            f"| {_format_value(check.get('column'))} "
            f"| {'pass' if check.get('success') else 'FAIL'} "
            f"| {_format_value(check.get('unexpected_count'))} "
            f"| {_format_value(check.get('observed_value'))} |"
        )

    failed = quality.get("failed_checks") or []
    if failed:
        lines.extend(["", f"Failed expectations: {', '.join(failed)}"])
    return lines


def generate_phase1_report(
    report_path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    freshness_status = "FRESH" if freshness.get("is_fresh") else "STALE"
    lines = [
        "# Phase 1 - Baseline Report",
        "",
        f"Generated at: {now_utc().isoformat()}",
        "",
        "Baseline run of the RAG data pipeline on clean Crossref data: ingestion -> cleaning -> "
        "embedding index -> evaluation -> data quality and freshness monitoring.",
        "",
        "## 1. Source and dataset",
        "",
        *_kv_table(source_summary),
        "",
        "## 2. Evaluation metrics",
        "",
        *_metrics_section(metrics),
        "",
        "## 3. Data quality",
        "",
        *_quality_section(quality),
        "",
        "## 4. Freshness",
        "",
        f"Status: **{freshness_status}** (threshold {freshness.get('threshold_days')} days)",
        "",
        *_kv_table(freshness),
        "",
        "## 5. Reproduce",
        "",
        "```bash",
        "uv run python script/run_phase1.py",
        "```",
        "",
        "Set `REFRESH_SOURCE=1` to re-fetch from Crossref and `REFRESH_TEST_SET=1` to rebuild the evaluation set.",
        "",
    ]
    write_text(report_path, "\n".join(lines))


def generate_corruption_report(
    report_path,
    baseline_metrics: dict[str, Any],
    corrupted_metrics: dict[str, Any],
    repaired_metrics: dict[str, Any],
    comparison: dict[str, Any],
    corruption_log_path=None,
) -> None:
    """Write markdown report comparing baseline/corrupted/repaired."""
    lines = [
        "# Corruption Flow - Comparison Report",
        "",
        f"Generated at: {now_utc().isoformat()}",
        "",
        "This report compares three pipeline states to demonstrate the impact of data corruption",
        "on RAG agent quality and the effectiveness of recovery from raw source data.",
        "",
        "## 1. Comparison Summary",
        "",
        "| Metric | Baseline | Corrupted | Repaired | Corrupted Δ | Repaired Δ |",
        "| --- | --- | --- | --- | --- | --- |",
    ]

    for metric_name in ["retrieval_hit_rate", "mean_token_f1", "judge_accuracy", "mean_judge_score"]:
        delta = comparison.get("delta", {}).get(metric_name, {})
        baseline_val = delta.get("baseline")
        corrupted_val = delta.get("corrupted")
        repaired_val = delta.get("repaired")
        corrupted_delta = delta.get("corrupted_delta", 0)
        repaired_delta = delta.get("repaired_delta", 0)

        def fmt(v):
            if v is None:
                return "-"
            if isinstance(v, float):
                return f"{v:.3f}"
            return str(v)

        lines.append(
            f"| {metric_name} | {fmt(baseline_val)} | {fmt(corrupted_val)} | "
            f"{fmt(repaired_val)} | {corrupted_delta:+.3f} | {repaired_delta:+.3f} |"
        )

    lines.extend([
        "",
        "## 2. Record Counts",
        "",
        f"- Baseline records: {comparison.get('record_counts', {}).get('baseline', 'N/A')}",
        f"- Corrupted records: {comparison.get('record_counts', {}).get('corrupted', 'N/A')}",
        f"- Repaired records: {comparison.get('record_counts', {}).get('repaired', 'N/A')}",
        "",
        "## 3. Quality Status",
        "",
        f"- Baseline: {comparison.get('quality_status', {}).get('baseline', 'N/A').upper()}",
        f"- Corrupted: {comparison.get('quality_status', {}).get('corrupted', 'N/A').upper()}",
        f"- Repaired: {comparison.get('quality_status', {}).get('repaired', 'N/A').upper()}",
        "",
        "## 4. Freshness Status",
        "",
        f"- Baseline: {comparison.get('freshness_status', {}).get('baseline', 'N/A').upper()}",
        f"- Corrupted: {comparison.get('freshness_status', {}).get('corrupted', 'N/A').upper()}",
        f"- Repaired: {comparison.get('freshness_status', {}).get('repaired', 'N/A').upper()}",
        "",
        "## 5. Corruption Applied",
        "",
    ])

    if corruption_log_path.exists():
        import json
        with open(corruption_log_path, "r", encoding="utf-8") as f:
            log = json.load(f)
        lines.append(f"- Initial records: {log.get('initial_count', 'N/A')}")
        lines.append(f"- Final records: {log.get('final_count', 'N/A')}")
        lines.append(f"- Corruption types applied: {', '.join(log.get('corruption_types', []))}")
        lines.append("")
        for entry in log.get("corruption_log", []):
            lines.append(f"  - {entry.get('description', entry.get('type', 'unknown'))}: {entry.get('count', 0)} records")
    else:
        lines.append("_Corruption log not available_")

    lines.extend([
        "",
        "## 6. Key Findings",
        "",
    ])

    hit_rate_delta = comparison.get("delta", {}).get("retrieval_hit_rate", {}).get("corrupted_delta", 0)
    if hit_rate_delta < -0.1:
        lines.append("- **Retrieval performance degraded** after corruption, demonstrating data quality impact.")
    elif hit_rate_delta > 0.1:
        lines.append("- **Retrieval performance improved** unexpectedly (possible lucky corruption).")
    else:
        lines.append("- Retrieval performance relatively stable despite corruption.")

    repair_delta = comparison.get("delta", {}).get("retrieval_hit_rate", {}).get("repaired_delta", 0)
    if abs(repair_delta) < 0.05:
        lines.append("- **Recovery successful**: Repaired metrics approximately match baseline.")
    elif repair_delta > hit_rate_delta:
        lines.append("- **Partial recovery**: Repaired metrics closer to baseline than corrupted state.")
    else:
        lines.append("- Recovery did not fully restore baseline performance.")

    lines.extend([
        "",
        "## 7. Reproduce",
        "",
        "```bash",
        "# First run baseline",
        "uv run python script/run_phase1.py",
        "",
        "# Then run corruption flow",
        "uv run python script/run_corruption_flow.py",
        "```",
        "",
    ])

    write_text(report_path, "\n".join(lines))
