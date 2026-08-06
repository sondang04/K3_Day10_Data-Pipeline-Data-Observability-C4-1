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


def generate_role4_cp2_report(
    report_path,
    test_set_path: str,
    test_set_hash: str,
    test_set_validation: dict[str, Any],
    index_validation: dict[str, Any],
    index_audit: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
    preview_samples: list[dict[str, Any]],
) -> None:
    """Write auditable CP2 evidence for the evaluation/observability owner."""

    overall_success = all(
        [
            test_set_validation.get("success"),
            index_validation.get("success"),
            index_audit.get("success"),
            quality.get("success"),
            freshness.get("is_fresh"),
        ]
    )
    lines = [
        "# Vai trò 4 — Checkpoint 2",
        "",
        f"Generated at: {now_utc().isoformat()}",
        "",
        f"Trạng thái: **{'PASS' if overall_success else 'REVIEW'}**",
        "",
        "## 1. Test set đã khóa",
        "",
        f"- Artifact: `{test_set_path}`",
        f"- SHA-256: `{test_set_hash}`",
        f"- Samples: **{test_set_validation.get('sample_count', 0)}**",
        f"- Question types: **{', '.join(test_set_validation.get('question_types', [])) or '-'}**",
        f"- Validation với clean data: **{'PASS' if test_set_validation.get('success') else 'FAIL'}**",
        f"- Validation với baseline index: **{'PASS' if index_validation.get('success') else 'FAIL'}**",
        f"- Document IDs được tham chiếu: **{index_validation.get('referenced_document_count', 0)}**",
        "",
        "### Preview",
        "",
        "| ID | Type | Question | Ground-truth document |",
        "| --- | --- | --- | --- |",
    ]
    for sample in preview_samples:
        question = str(sample.get("question", "")).replace("|", "\\|")
        doc_ids = ", ".join(sample.get("ground_truth_doc_ids", []))
        lines.append(
            f"| {sample.get('id')} | {sample.get('question_type')} | {question} | {doc_ids} |"
        )

    lines.extend(
        [
            "",
            "## 2. Baseline embedding/index audit",
            "",
            f"- Audit status: **{'PASS' if index_audit.get('success') else 'FAIL'}**",
            f"- Backend/model: **{index_audit.get('backend')} / {index_audit.get('embedding_model')}**",
            f"- Collection: **{index_audit.get('collection_name')}**",
            f"- Embedding dimension: **{index_audit.get('embedding_dimension')}**",
            f"- Clean / manifest / collection counts: **{index_audit.get('clean_document_count')} / "
            f"{index_audit.get('manifest_document_count')} / {index_audit.get('collection_document_count')}**",
            f"- Runtime persist path: `{index_audit.get('runtime_persist_path')}`",
            f"- Chroma database: `{index_audit.get('chroma_database')}`",
            f"- Failed checks: **{', '.join(index_audit.get('failed_checks') or []) or 'none'}**",
            "",
            "### Audit checks",
            "",
            "| Check | Result | Observed | Expected |",
            "| --- | --- | --- | --- |",
        ]
    )
    for check in index_audit.get("checks", []):
        lines.append(
            f"| {check.get('check')} | {'pass' if check.get('success') else 'FAIL'} | "
            f"{_format_value(check.get('observed'))} | {_format_value(check.get('expected'))} |"
        )
    warnings = index_audit.get("warnings") or []
    if warnings:
        lines.extend(["", "Warnings:", "", *[f"- {warning}" for warning in warnings]])

    lines.extend(
        [
            "",
            "## 3. Baseline observability snapshot",
            "",
            f"- Quality: **{'PASS' if quality.get('success') else 'FAIL'}**, "
            f"{quality.get('statistics', {}).get('successful_expectations', 0)}/"
            f"{quality.get('statistics', {}).get('evaluated_expectations', 0)} checks passed.",
            f"- Freshness: **{'FRESH' if freshness.get('is_fresh') else 'STALE/INVALID'}**, "
            f"fresh/stale rows = {freshness.get('fresh_rows', 0)}/{freshness.get('stale_rows', 0)}.",
            f"- Latest/oldest publication: **{freshness.get('latest_published')} / {freshness.get('oldest_published')}**.",
            f"- Source timestamp column: **{freshness.get('source_timestamp_column') or 'missing'}**; "
            f"latest timestamp: **{freshness.get('latest_ingested_at')}**.",
            "",
            "## 4. Handoff sang CP3",
            "",
            "- Không tạo lại test set; SHA-256 ở trên là mốc đối chiếu cho baseline, corrupted và repaired.",
            "- Role 3 có thể chạy semantic search, exact lookup và agent smoke test trên `papers-baseline`.",
            "- Role 4 chỉ điền metric thật vào phase1 report sau khi baseline evaluation hoàn tất.",
            "",
            "## Chạy lại",
            "",
            "```bash",
            "uv run python script/run_role4_cp2.py",
            "```",
            "",
        ]
    )
    write_text(report_path, "\n".join(lines))


def generate_phase1_cp2_template(
    report_path,
    test_set_hash: str,
    test_set_validation: dict[str, Any],
    index_audit: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    """Prepare the CP3 report shell while leaving evaluation metrics explicitly pending."""

    lines = [
        "# Phase 1 — Baseline Report (CP2 template)",
        "",
        f"Prepared at: {now_utc().isoformat()}",
        "",
        "This template contains only verified CP2 facts. Evaluation metrics remain pending until CP3; no values are fabricated.",
        "",
        "## 1. Locked evaluation set",
        "",
        f"- Samples: {test_set_validation.get('sample_count', 0)}",
        f"- Types: {', '.join(test_set_validation.get('question_types', []))}",
        f"- SHA-256: `{test_set_hash}`",
        "",
        "## 2. Baseline index",
        "",
        f"- Backend: {index_audit.get('backend')}",
        f"- Embedding model: {index_audit.get('embedding_model')}",
        f"- Collection: {index_audit.get('collection_name')}",
        f"- Documents: {index_audit.get('collection_document_count')}",
        f"- Dimension: {index_audit.get('embedding_dimension')}",
        "",
        "## 3. Evaluation metrics — fill at CP3",
        "",
        "| Metric | Value |",
        "| --- | --- |",
        "| Evaluation samples | PENDING_CP3 |",
        "| Retrieval hit rate | PENDING_CP3 |",
        "| Mean token F1 | PENDING_CP3 |",
        "| Judge accuracy | PENDING_CP3 |",
        "| Mean judge score (1–5) | PENDING_CP3 |",
        "| Ragas | PENDING_CP3 |",
        "",
        "## 4. Data quality",
        "",
        f"- Status: {'PASS' if quality.get('success') else 'FAIL'}",
        f"- Rows: {quality.get('row_count', 0)}",
        f"- Checks passed: {quality.get('statistics', {}).get('successful_expectations', 0)}/"
        f"{quality.get('statistics', {}).get('evaluated_expectations', 0)}",
        "",
        "## 5. Freshness",
        "",
        f"- Status: {'FRESH' if freshness.get('is_fresh') else 'STALE/INVALID'}",
        f"- Fresh/stale rows: {freshness.get('fresh_rows', 0)}/{freshness.get('stale_rows', 0)}",
        f"- Threshold: {freshness.get('threshold_days')} days",
        f"- Latest publication: {freshness.get('latest_published')}",
        f"- Source timestamp: {freshness.get('source_timestamp_column') or 'missing'} = {freshness.get('latest_ingested_at')}",
        "",
        "## 6. CP3 evidence to attach",
        "",
        "- `data/results/baseline_answers.json`",
        "- `data/results/baseline_metrics.json`",
        "- Agent smoke-test output with cited sources",
        "",
    ]
    write_text(report_path, "\n".join(lines))
