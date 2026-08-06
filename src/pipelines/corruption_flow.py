from __future__ import annotations

from typing import Any

import pandas as pd

from core.config import Settings, load_settings
from core.utils import now_utc, read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe, save_corrupted_data
from ingestion.crossref import load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_corruption_report
from retrieval.index import LocalEmbeddingIndex

TOTAL_STEPS = 9


def _log(step: int, message: str) -> None:
    print(f"[corruption_flow] {step}/{TOTAL_STEPS} {message}", flush=True)


def _relative(settings: Settings, path) -> str:
    try:
        return str(path.relative_to(settings.paths.project_dir))
    except ValueError:
        return str(path)


def main() -> None:
    settings = load_settings()
    run_date = now_utc()

    _log(1, "loading baseline clean data")
    clean_csv = settings.paths.clean_csv
    if not clean_csv.exists():
        raise FileNotFoundError(
            f"Baseline clean CSV not found at {clean_csv}. "
            "Run phase1 baseline first."
        )
    baseline_df = pd.read_csv(clean_csv)
    baseline_records = len(baseline_df)
    print(f"        loaded {baseline_records} baseline records")

    _log(2, "loading baseline metrics")
    baseline_metrics = read_json(settings.paths.baseline_metrics)
    print(f"        baseline hit_rate={baseline_metrics.get('retrieval_hit_rate', 'N/A')}")

    _log(3, "creating corrupted dataset")
    corrupted_df = corrupt_clean_dataframe(baseline_df, settings.paths.corruption_log)
    corrupted_records = len(corrupted_df)
    print(f"        corrupted: {baseline_records} -> {corrupted_records} records")

    _log(4, "saving corrupted artifacts")
    save_corrupted_data(
        corrupted_df,
        settings.paths.corrupted_clean_csv,
        settings.paths.corrupted_clean_json
    )
    print(f"        saved to {_relative(settings, settings.paths.corrupted_clean_csv)}")

    _log(5, "building corrupted embedding index")
    corrupted_index = LocalEmbeddingIndex.build(
        corrupted_df, settings, settings.paths.corrupted_embeddings_json
    )
    print(f"        collection '{corrupted_index.collection_name}' with {len(corrupted_index.documents)} documents")

    _log(6, "evaluating corrupted dataset")
    corrupted_evaluation = evaluate_pipeline(
        settings=settings,
        index=corrupted_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.corrupted_metrics,
        answers_output_path=settings.paths.corrupted_answers,
    )
    print(f"        corrupted hit_rate={corrupted_evaluation.summary['retrieval_hit_rate']:.3f}")

    _log(7, "running quality/freshness checks on corrupted data")
    corrupted_quality = run_data_quality_checks(corrupted_df, settings, "corrupted_quality")
    print(f"        corrupted quality success={corrupted_quality['success']}")
    corrupted_freshness = build_freshness_report(corrupted_df, settings, settings.paths.quality_dir / "corrupted_freshness.json")
    print(f"        corrupted is_fresh={corrupted_freshness['is_fresh']}")

    _log(8, "repairing from raw source")
    raw_records = load_raw_records(settings.paths.raw_records_json)
    repaired_df = build_clean_dataframe(raw_records, run_date)
    repaired_records = len(repaired_df)
    print(f"        repaired from raw: {repaired_records} records")

    write_csv(repaired_df, settings.paths.repaired_clean_csv)
    write_json(settings.paths.repaired_clean_json, repaired_df.to_dict(orient="records"))
    print(f"        saved to {_relative(settings, settings.paths.repaired_clean_csv)}")

    _log(9, "evaluating repaired dataset and generating comparison report")
    repaired_index = LocalEmbeddingIndex.build(
        repaired_df, settings, settings.paths.repaired_embeddings_json
    )
    print(f"        collection '{repaired_index.collection_name}' with {len(repaired_index.documents)} documents")

    repaired_evaluation = evaluate_pipeline(
        settings=settings,
        index=repaired_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.repaired_metrics,
        answers_output_path=settings.paths.repaired_answers,
    )
    print(f"        repaired hit_rate={repaired_evaluation.summary['retrieval_hit_rate']:.3f}")

    repaired_quality = run_data_quality_checks(repaired_df, settings, "repaired_quality")
    repaired_freshness = build_freshness_report(repaired_df, settings, settings.paths.quality_dir / "repaired_freshness.json")

    comparison = {
        "baseline_metrics": baseline_metrics,
        "corrupted_metrics": corrupted_evaluation.summary,
        "repaired_metrics": repaired_evaluation.summary,
        "delta": {
            "retrieval_hit_rate": {
                "baseline": baseline_metrics.get("retrieval_hit_rate"),
                "corrupted": corrupted_evaluation.summary["retrieval_hit_rate"],
                "repaired": repaired_evaluation.summary["retrieval_hit_rate"],
                "corrupted_delta": (
                    corrupted_evaluation.summary["retrieval_hit_rate"] - baseline_metrics.get("retrieval_hit_rate", 0)
                ),
                "repaired_delta": (
                    repaired_evaluation.summary["retrieval_hit_rate"] - baseline_metrics.get("retrieval_hit_rate", 0)
                ),
            },
            "mean_token_f1": {
                "baseline": baseline_metrics.get("mean_token_f1"),
                "corrupted": corrupted_evaluation.summary["mean_token_f1"],
                "repaired": repaired_evaluation.summary["mean_token_f1"],
                "corrupted_delta": (
                    corrupted_evaluation.summary["mean_token_f1"] - baseline_metrics.get("mean_token_f1", 0)
                ),
                "repaired_delta": (
                    repaired_evaluation.summary["mean_token_f1"] - baseline_metrics.get("mean_token_f1", 0)
                ),
            },
            "judge_accuracy": {
                "baseline": baseline_metrics.get("judge_accuracy"),
                "corrupted": corrupted_evaluation.summary["judge_accuracy"],
                "repaired": repaired_evaluation.summary["judge_accuracy"],
                "corrupted_delta": (
                    corrupted_evaluation.summary["judge_accuracy"] - baseline_metrics.get("judge_accuracy", 0)
                ),
                "repaired_delta": (
                    repaired_evaluation.summary["judge_accuracy"] - baseline_metrics.get("judge_accuracy", 0)
                ),
            },
            "mean_judge_score": {
                "baseline": baseline_metrics.get("mean_judge_score"),
                "corrupted": corrupted_evaluation.summary["mean_judge_score"],
                "repaired": repaired_evaluation.summary["mean_judge_score"],
                "corrupted_delta": (
                    corrupted_evaluation.summary["mean_judge_score"] - baseline_metrics.get("mean_judge_score", 0)
                ),
                "repaired_delta": (
                    repaired_evaluation.summary["mean_judge_score"] - baseline_metrics.get("mean_judge_score", 0)
                ),
            },
        },
        "record_counts": {
            "baseline": baseline_records,
            "corrupted": corrupted_records,
            "repaired": repaired_records,
        },
        "quality_status": {
            "baseline": "passed" if baseline_metrics.get("success", True) else "failed",
            "corrupted": "passed" if corrupted_quality["success"] else "failed",
            "repaired": "passed" if repaired_quality["success"] else "failed",
        },
        "freshness_status": {
            "baseline": "fresh" if read_json(settings.paths.freshness_report).get("is_fresh") else "stale",
            "corrupted": "stale" if not corrupted_freshness.get("is_fresh") else "fresh",
            "repaired": "stale" if not repaired_freshness.get("is_fresh") else "fresh",
        },
    }

    write_json(settings.paths.quality_dir / "comparison_metrics.json", comparison)

    generate_corruption_report(
        report_path=settings.paths.comparison_report,
        baseline_metrics=baseline_metrics,
        corrupted_metrics=corrupted_evaluation.summary,
        repaired_metrics=repaired_evaluation.summary,
        comparison=comparison,
        corruption_log_path=settings.paths.corruption_log,
    )
    print(f"        report: {_relative(settings, settings.paths.comparison_report)}")

    print("[corruption_flow] complete")
    print("        Comparison summary:")
    for metric_name, delta_data in comparison["delta"].items():
        print(f"          {metric_name}:")
        baseline_val = delta_data['baseline']
        corrupted_val = delta_data['corrupted']
        repaired_val = delta_data['repaired']
        corrupted_delta = delta_data['corrupted_delta']
        repaired_delta = delta_data['repaired_delta']

        def fmt(v):
            if v is None:
                return "-"
            if isinstance(v, float):
                return f"{v:.3f}"
            return str(v)

        print(f"            baseline: {fmt(baseline_val)}")
        print(f"            corrupted: {fmt(corrupted_val)} (delta: {corrupted_delta:+.3f})")
        print(f"            repaired: {fmt(repaired_val)} (delta: {repaired_delta:+.3f})")
