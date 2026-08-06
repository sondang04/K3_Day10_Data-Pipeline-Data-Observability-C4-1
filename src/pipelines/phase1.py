from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from core.config import Settings, load_settings
from core.utils import now_utc, read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import PaperRecord, fetch_source_records, load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.agent import build_agent, run_agent_question
from retrieval.index import LocalEmbeddingIndex

TOTAL_STEPS = 8
QUALITY_REPORT_NAME = "baseline_quality"
DEMO_QUESTION_COUNT = 2


def _log(step: int, message: str) -> None:
    print(f"[phase1] {step}/{TOTAL_STEPS} {message}", flush=True)


def _relative(settings: Settings, path: Path) -> str:
    try:
        return str(path.relative_to(settings.paths.project_dir))
    except ValueError:
        return str(path)


def _load_records(settings: Settings) -> tuple[list[PaperRecord], str]:
    snapshot = settings.paths.raw_records_json
    if settings.refresh_source or not snapshot.exists():
        return fetch_source_records(settings), "crossref-api"
    return load_raw_records(snapshot), "raw-snapshot"


def _load_test_set(settings: Settings, df: pd.DataFrame) -> tuple[list[dict[str, Any]], str]:
    path = settings.paths.eval_testset
    if settings.refresh_test_set or not path.exists():
        return build_test_set(df, path), "generated"
    return read_json(path), "cached"


def _source_summary(
    settings: Settings,
    records: list[PaperRecord],
    df: pd.DataFrame,
    records_source: str,
    test_set_source: str,
    test_set_size: int,
) -> dict[str, Any]:
    return {
        "source_api": settings.source_api,
        "source_query": settings.source_query,
        "source_filter": settings.source_filter,
        "records_source": records_source,
        "raw_records": len(records),
        "clean_rows": int(len(df)),
        "dropped_by_cleaning": len(records) - int(len(df)),
        "clean_columns": int(len(df.columns)),
        "published_range": f"{df['published'].min()} .. {df['published'].max()}" if not df.empty else "-",
        "embedding_model": settings.embedding_model,
        "collection_name": settings.baseline_collection_name,
        "top_k": settings.top_k,
        "test_set_source": test_set_source,
        "test_set_size": test_set_size,
        "raw_response_artifact": _relative(settings, settings.paths.raw_api_response),
        "raw_records_artifact": _relative(settings, settings.paths.raw_records_json),
        "clean_artifacts": f"{_relative(settings, settings.paths.clean_csv)}, {_relative(settings, settings.paths.clean_json)}",
        "embeddings_artifact": _relative(settings, settings.paths.embeddings_json),
        "test_set_artifact": _relative(settings, settings.paths.eval_testset),
        "metrics_artifact": _relative(settings, settings.paths.baseline_metrics),
    }


def _run_agent_demo(settings: Settings, index: LocalEmbeddingIndex, test_set: list[dict[str, Any]]) -> dict[str, Any]:
    questions = [item["question"] for item in test_set[:DEMO_QUESTION_COUNT]]
    payload: dict[str, Any] = {
        "provider": settings.llm_provider,
        "model": settings.model_name,
        "questions": questions,
    }
    try:
        agent = build_agent(settings=settings, index=index)
        payload["status"] = "ok"
        payload["answers"] = [
            {"question": question, "answer": run_agent_question(agent, question)} for question in questions
        ]
    except Exception as exc:
        # The baseline pipeline stays reproducible without LLM credentials; only the
        # agent demo needs a live provider.
        payload["status"] = "skipped"
        payload["reason"] = str(exc)
    write_json(settings.paths.demo_answers, payload)
    return payload


def main() -> None:
    settings = load_settings()
    run_date = now_utc()

    _log(1, "loading raw records")
    records, records_source = _load_records(settings)
    print(f"        {len(records)} raw records from {records_source}")

    _log(2, "cleaning records")
    df = build_clean_dataframe(records, run_date)
    if df.empty:
        raise RuntimeError("Cleaning produced an empty dataset; re-run with REFRESH_SOURCE=1.")
    write_csv(df, settings.paths.clean_csv)
    write_json(settings.paths.clean_json, df.to_dict(orient="records"))
    print(f"        {len(df)} clean rows -> {_relative(settings, settings.paths.clean_csv)}")

    _log(3, "building embedding index")
    index = LocalEmbeddingIndex.build(df, settings, settings.paths.embeddings_json)
    print(f"        collection '{index.collection_name}' with {len(index.documents)} documents")

    _log(4, "preparing evaluation set")
    test_set, test_set_source = _load_test_set(settings, df)
    print(f"        {len(test_set)} questions ({test_set_source})")

    _log(5, "evaluating baseline")
    evaluation = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.baseline_metrics,
        answers_output_path=settings.paths.baseline_answers,
    )
    print(f"        hit_rate={evaluation.summary['retrieval_hit_rate']:.3f} f1={evaluation.summary['mean_token_f1']:.3f}")

    _log(6, "running data quality checks")
    quality = run_data_quality_checks(df, settings, QUALITY_REPORT_NAME)
    print(f"        quality success={quality['success']} failed={quality['failed_checks'] or 'none'}")

    _log(7, "building freshness report")
    freshness = build_freshness_report(df, settings, settings.paths.freshness_report)
    print(f"        is_fresh={freshness['is_fresh']} stale_rows={freshness['stale_rows']}")

    _log(8, "writing markdown report")
    source_summary = _source_summary(settings, records, df, records_source, test_set_source, len(test_set))
    generate_phase1_report(
        report_path=settings.paths.baseline_report,
        source_summary=source_summary,
        metrics=evaluation.summary,
        quality=quality,
        freshness=freshness,
    )
    print(f"        {_relative(settings, settings.paths.baseline_report)}")

    demo = _run_agent_demo(settings, index, test_set)
    print(f"[phase1] agent demo: {demo['status']}")

    print("[phase1] baseline complete")
    for label, value in {
        "retrieval_hit_rate": evaluation.summary["retrieval_hit_rate"],
        "mean_token_f1": evaluation.summary["mean_token_f1"],
        "judge_accuracy": evaluation.summary["judge_accuracy"],
        "mean_judge_score": evaluation.summary["mean_judge_score"],
    }.items():
        print(f"        {label}: {value:.3f}")
