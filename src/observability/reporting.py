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


def generate_role4_cp0_cp1_report(
    report_path,
    clean_path: str,
    test_set_path: str,
    test_set_validation: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    """Write the role-4 handoff evidence required at CP0 and CP1."""

    status = "PASS" if quality.get("success") and freshness.get("is_fresh") else "REVIEW"
    question_types = ", ".join(test_set_validation.get("question_types", [])) or "-"
    lines = [
        "# Vai trò 4 — Hoàn thành CP0–CP1",
        "",
        f"Generated at: {now_utc().isoformat()}",
        "",
        f"Trạng thái bàn giao: **{status}**",
        "",
        "## CP0 — Contract evaluation và observability",
        "",
        "### Evaluation contract",
        "",
        "- Input là cleaned dataframe; không tạo câu hỏi từ raw data chưa chuẩn hóa.",
        "- Mỗi sample gồm: `id`, `question_type`, `question`, `ground_truth`, `ground_truth_doc_ids`.",
        "- `ground_truth_doc_ids` chỉ lấy từ `paper_id` ổn định và duy nhất trong clean data.",
        "- Nhóm câu hỏi dự kiến: summary, authors, date, categories và semantic retrieval.",
        "- Cùng một test set sẽ được khóa để so sánh baseline, corrupted và repaired ở các checkpoint sau.",
        "",
        "### Observability contract",
        "",
        "| Signal | Ý nghĩa |",
        "| --- | --- |",
        "| Row count | Phát hiện dataset thiếu hoặc bị drop bất thường |",
        "| Missing/blank | Kiểm tra `paper_id`, title, summary và `text_for_embedding` |",
        "| Duplicate | Kiểm tra `paper_id` và title sau chuẩn hóa |",
        "| Freshness | Đối chiếu `published`, `age_days` và ngưỡng freshness |",
        "| Source timestamp | Kiểm tra `ingested_at` và độ trễ từ lần ingest gần nhất |",
        "",
        "Artifacts sẽ dùng xuyên pipeline: clean CSV/JSON, test set, answers/metrics, quality JSON, freshness JSON và Markdown reports.",
        "",
        "## CP1 — Kết quả trên cleaned data",
        "",
        f"- Clean artifact: `{clean_path}`",
        f"- Số dòng sạch: **{quality.get('row_count', 0)}**",
        f"- Quality status: **{'PASS' if quality.get('success') else 'FAIL'}**",
        f"- Quality checks đạt: **{quality.get('statistics', {}).get('successful_expectations', 0)}/"
        f"{quality.get('statistics', {}).get('evaluated_expectations', 0)}**",
        f"- Failed checks: **{', '.join(quality.get('failed_checks') or []) or 'none'}**",
        f"- Freshness status: **{'FRESH' if freshness.get('is_fresh') else 'STALE/INVALID'}**",
        f"- Fresh/stale rows: **{freshness.get('fresh_rows', 0)}/{freshness.get('stale_rows', 0)}**",
        f"- Latest/oldest publication: **{freshness.get('latest_published')} / {freshness.get('oldest_published')}**",
        f"- Age mismatch rows: **{freshness.get('age_mismatch_rows', 0)}**",
        f"- Latest source timestamp: **{freshness.get('latest_ingested_at')}**",
        "",
        "## Evaluation draft đã kiểm chứng",
        "",
        f"- Test set artifact: `{test_set_path}`",
        f"- Số sample: **{test_set_validation.get('sample_count', 0)}**",
        f"- Question types: **{question_types}**",
        f"- Clean document IDs có thể đối chiếu: **{test_set_validation.get('clean_document_count', 0)}**",
        f"- Validation: **{'PASS' if test_set_validation.get('success') else 'FAIL'}**",
        "",
        "## Handoff sang CP2",
        "",
        "Vai trò 3 có thể build baseline index từ clean artifact. Vai trò 4 chỉ chạy retrieval evaluation sau khi collection baseline tồn tại; không thay đổi test set giữa ba trạng thái.",
        "",
        "## Chạy lại",
        "",
        "```bash",
        "uv run python script/run_role4_cp0_cp1.py",
        "```",
        "",
    ]
    write_text(report_path, "\n".join(lines))


def generate_corruption_report(
    report_path,
    baseline_metrics: dict[str, Any],
    corrupted_metrics: dict[str, Any],
    repaired_metrics: dict[str, Any],
    corrupted_quality: dict[str, Any],
    repaired_quality: dict[str, Any],
    corrupted_freshness: dict[str, Any],
    repaired_freshness: dict[str, Any],
) -> None:
    """TODO(student): viet markdown report so sanh baseline/corrupted/repaired."""
    raise NotImplementedError("Student task: implement corruption comparison report.")
