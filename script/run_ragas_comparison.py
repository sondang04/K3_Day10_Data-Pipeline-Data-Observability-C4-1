"""Run the clean -> corrupted -> repaired lifecycle once per RAGAS mode and trace it.

For every mode in RAGAS_MODES the script runs `phase1.main()` followed by
`corruption_flow.main()` in-process, snapshots the artifacts they produce, and then
derives a record-level trace of what corruption did to the dataset and what the repair
step restored.

    uv run python script/run_ragas_comparison.py          # modes 1 then 0
    uv run python script/run_ragas_comparison.py 0        # single mode

The corruption RNG is seeded per mode so both lanes corrupt exactly the same rows and
the only difference between them is the Ragas pass.
"""

from __future__ import annotations

import io
import json
import os
import random
import re
import shutil
import sys
from contextlib import redirect_stdout
from pathlib import Path
from typing import Any

import pandas as pd

from core.config import Settings, load_settings
from core.utils import now_utc, read_json, write_json, write_text
from pipelines import corruption_flow, phase1

CORRUPTION_SEED = 20260806
DEFAULT_MODES = ["1", "0"]
CORE_METRICS = ["samples", "retrieval_hit_rate", "mean_token_f1", "judge_accuracy", "mean_judge_score"]
NOISE_TOKENS = ["XXX", "ZZZ", "NOISE", "TEST", "[CORRUPTED]", "<<<>>>", "[UNVERIFIED]", "???", "***", "###", "[DUBIOUS]"]
DUP_SUFFIX = re.compile(r"_dup_\d+$")

STATES = ["baseline", "corrupted", "repaired"]


class _Tee(io.TextIOBase):
    """Forward pipeline stdout to the console and into the trace buffer."""

    def __init__(self, console, buffer):
        self.console = console
        self.buffer = buffer

    def write(self, data: str) -> int:
        self.console.write(data)
        self.buffer.write(data)
        return len(data)

    def flush(self) -> None:
        self.console.flush()


class Tracer:
    def __init__(self, path: Path):
        self.path = path
        self.events: list[dict[str, Any]] = []

    def emit(self, stage: str, event: str, payload: dict[str, Any]) -> None:
        self.events.append(
            {"timestamp": now_utc().isoformat(), "stage": stage, "event": event, **payload}
        )

    def flush(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as handle:
            for event in self.events:
                handle.write(json.dumps(event, ensure_ascii=True, default=str) + "\n")


def _text(value: Any) -> str:
    return "" if value is None or (isinstance(value, float) and pd.isna(value)) else str(value)


def _mode_dir(settings: Settings, mode: str) -> Path:
    return settings.paths.project_dir / "data" / "results" / "ragas_modes" / f"ragas{mode}"


def _snapshot_paths(settings: Settings) -> dict[str, Path]:
    paths = settings.paths
    return {
        "baseline_metrics.json": paths.baseline_metrics,
        "corrupted_metrics.json": paths.corrupted_metrics,
        "repaired_metrics.json": paths.repaired_metrics,
        "baseline_answers.json": paths.baseline_answers,
        "corrupted_answers.json": paths.corrupted_answers,
        "repaired_answers.json": paths.repaired_answers,
        "baseline-quality.json": paths.quality_dir / "baseline-quality.json",
        "corrupted-quality.json": paths.quality_dir / "corrupted-quality.json",
        "repaired-quality.json": paths.quality_dir / "repaired-quality.json",
        "freshness_report.json": paths.freshness_report,
        "corrupted_freshness.json": paths.quality_dir / "corrupted_freshness.json",
        "repaired_freshness.json": paths.quality_dir / "repaired_freshness.json",
        "corruption_log.json": paths.corruption_log,
        "papers_clean.csv": paths.clean_csv,
        "papers_clean_corrupted.csv": paths.corrupted_clean_csv,
        "papers_clean_repaired.csv": paths.repaired_clean_csv,
        "phase1_report.md": paths.baseline_report,
        "corruption_report.md": paths.comparison_report,
    }


def _run_stage(tracer: Tracer, mode: str, stage: str, runner) -> dict[str, Any]:
    buffer = io.StringIO()
    started = now_utc()
    print(f"\n=== [RUN_RAGAS={mode}] {stage} ===", flush=True)
    error = None
    try:
        with redirect_stdout(_Tee(sys.stdout, buffer)):
            runner()
    except Exception as exc:  # keep the other mode runnable and record the failure
        error = f"{type(exc).__name__}: {exc}"
        print(f"        STAGE FAILED: {error}", flush=True)

    payload = {
        "mode": mode,
        "duration_seconds": round((now_utc() - started).total_seconds(), 2),
        "error": error,
        "stdout": buffer.getvalue().splitlines(),
    }
    tracer.emit(stage, "stage_completed", payload)
    return payload


def run_mode(settings: Settings, tracer: Tracer, mode: str) -> dict[str, Any]:
    os.environ["RUN_RAGAS"] = mode
    tracer.emit("mode", "mode_started", {"mode": mode, "run_ragas": mode, "seed": CORRUPTION_SEED})

    stages = {"phase1": _run_stage(tracer, mode, "phase1", phase1.main)}
    random.seed(CORRUPTION_SEED)
    stages["corruption_flow"] = _run_stage(tracer, mode, "corruption_flow", corruption_flow.main)

    target = _mode_dir(settings, mode)
    target.mkdir(parents=True, exist_ok=True)
    copied = []
    for name, source in _snapshot_paths(settings).items():
        if source.exists():
            shutil.copy2(source, target / name)
            copied.append(name)

    metrics = {}
    for state in STATES:
        path = target / f"{state}_metrics.json"
        metrics[state] = read_json(path) if path.exists() else {}

    tracer.emit(
        "mode",
        "mode_completed",
        {
            "mode": mode,
            "snapshot_dir": str(target.relative_to(settings.paths.project_dir)),
            "artifacts_copied": len(copied),
            "ragas": {state: metrics[state].get("ragas") for state in STATES},
        },
    )
    return {"mode": mode, "stages": stages, "metrics": metrics, "snapshot_dir": target}


def _classify_row(base: pd.Series, corrupted: pd.Series | None) -> list[str]:
    if corrupted is None:
        return ["record_dropped"]

    tags: list[str] = []
    if _text(base["paper_id"]) != _text(corrupted["paper_id"]):
        tags.append("paper_id_mutated")

    base_summary, corrupt_summary = _text(base["summary"]), _text(corrupted["summary"])
    if base_summary and not corrupt_summary.strip():
        tags.append("summary_blanked")
    elif corrupt_summary != base_summary:
        marker = next((token for token in NOISE_TOKENS if token in corrupt_summary), None)
        tags.append(f"summary_noise_injected[{marker}]" if marker else "summary_modified")

    base_title, corrupt_title = _text(base["title"]), _text(corrupted["title"])
    if corrupt_title != base_title:
        tags.append("title_truncated" if corrupt_title.endswith("...") else "title_modified")

    if _text(base["published"]) != _text(corrupted["published"]):
        tags.append(f"published_backdated[{_text(base['published'])}->{_text(corrupted['published'])}]")

    if _text(base["text_for_embedding"]) != _text(corrupted["text_for_embedding"]):
        tags.append("embedding_text_rewritten")

    return tags or ["unchanged"]


def _dataset_trace(settings: Settings, tracer: Tracer, snapshot_dir: Path) -> dict[str, Any]:
    baseline = pd.read_csv(snapshot_dir / "papers_clean.csv")
    corrupted = pd.read_csv(snapshot_dir / "papers_clean_corrupted.csv")
    repaired = pd.read_csv(snapshot_dir / "papers_clean_repaired.csv")

    corrupted_by_id = {DUP_SUFFIX.sub("", _text(row["paper_id"])): row for _, row in corrupted.iterrows()}
    repaired_by_id = {_text(row["paper_id"]): row for _, row in repaired.iterrows()}

    records: list[dict[str, Any]] = []
    tag_counts: dict[str, int] = {}
    for _, base in baseline.iterrows():
        paper_id = _text(base["paper_id"])
        corrupt_row = corrupted_by_id.get(paper_id)
        tags = _classify_row(base, corrupt_row)
        repaired_row = repaired_by_id.get(paper_id)
        repair_state = (
            "missing_after_repair"
            if repaired_row is None
            else "restored"
            if all(_text(repaired_row[column]) == _text(base[column]) for column in ("title", "summary", "published", "text_for_embedding"))
            else "differs_from_baseline"
        )
        for tag in tags:
            key = tag.split("[")[0]
            tag_counts[key] = tag_counts.get(key, 0) + 1

        record = {
            "paper_id": paper_id,
            "corruption": tags,
            "repair": repair_state,
            "summary_chars": {
                "baseline": len(_text(base["summary"])),
                "corrupted": None if corrupt_row is None else len(_text(corrupt_row["summary"])),
                "repaired": None if repaired_row is None else len(_text(repaired_row["summary"])),
            },
        }
        records.append(record)
        if tags != ["unchanged"]:
            tracer.emit("dataset", "record_corrupted", record)

    trace = {
        "row_counts": {"baseline": len(baseline), "corrupted": len(corrupted), "repaired": len(repaired)},
        "corruption_tag_counts": dict(sorted(tag_counts.items())),
        "untouched_records": sum(1 for record in records if record["corruption"] == ["unchanged"]),
        "restored_records": sum(1 for record in records if record["repair"] == "restored"),
        "unrestored_records": [record["paper_id"] for record in records if record["repair"] != "restored"],
        "records": records,
    }
    tracer.emit("dataset", "dataset_trace", {k: v for k, v in trace.items() if k != "records"})
    return trace


def _quality_trace(tracer: Tracer, snapshot_dir: Path) -> dict[str, Any]:
    reports = {state: read_json(snapshot_dir / f"{state}-quality.json") for state in STATES}
    freshness_files = {
        "baseline": "freshness_report.json",
        "corrupted": "corrupted_freshness.json",
        "repaired": "repaired_freshness.json",
    }
    freshness = {state: read_json(snapshot_dir / name) for state, name in freshness_files.items()}

    by_check: dict[str, dict[str, Any]] = {}
    for state, report in reports.items():
        for check in report["checks"]:
            entry = by_check.setdefault(check["expectation"], {"column": check.get("column", "")})
            entry[state] = {"success": check["success"], "unexpected_count": check.get("unexpected_count")}

    regressions = {
        name: entry
        for name, entry in by_check.items()
        if entry.get("baseline", {}).get("success") and not entry.get("corrupted", {}).get("success", True)
    }
    for name, entry in regressions.items():
        tracer.emit("quality", "check_regressed", {"expectation": name, **entry})

    trace = {
        "status": {state: report["success"] for state, report in reports.items()},
        "statistics": {
            state: {
                "passed": report["statistics"]["successful_expectations"],
                "total": report["statistics"]["evaluated_expectations"],
            }
            for state, report in reports.items()
        },
        "failed_checks": {state: report["failed_checks"] for state, report in reports.items()},
        "regressed_on_corruption": regressions,
        "recovered_on_repair": [
            name
            for name, entry in regressions.items()
            if entry.get("repaired", {}).get("success")
        ],
        "freshness": {
            state: {
                key: payload.get(key)
                for key in (
                    "is_fresh",
                    "stale_rows",
                    "total_rows",
                    "oldest_published",
                    "latest_published",
                    "age_mismatch_rows",
                    "invalid_age_days_rows",
                )
            }
            for state, payload in freshness.items()
        },
    }
    tracer.emit("quality", "quality_trace", {k: v for k, v in trace.items() if k != "regressed_on_corruption"})
    return trace


def _answer_trace(tracer: Tracer, snapshot_dir: Path) -> dict[str, Any]:
    answers = {
        state: {item["id"]: item for item in read_json(snapshot_dir / f"{state}_answers.json")}
        for state in STATES
    }

    rows: list[dict[str, Any]] = []
    for question_id, baseline_item in answers["baseline"].items():
        corrupted_item = answers["corrupted"].get(question_id, {})
        repaired_item = answers["repaired"].get(question_id, {})
        row = {
            "id": question_id,
            "question_type": baseline_item["question_type"],
            "hit": {
                "baseline": baseline_item["retrieval_hit"],
                "corrupted": corrupted_item.get("retrieval_hit"),
                "repaired": repaired_item.get("retrieval_hit"),
            },
            "token_f1": {
                "baseline": round(baseline_item["token_f1"], 3),
                "corrupted": round(corrupted_item.get("token_f1", 0.0), 3),
                "repaired": round(repaired_item.get("token_f1", 0.0), 3),
            },
            "top_doc": {
                "baseline": (baseline_item["retrieved_doc_ids"] or [None])[0],
                "corrupted": (corrupted_item.get("retrieved_doc_ids") or [None])[0],
                "repaired": (repaired_item.get("retrieved_doc_ids") or [None])[0],
            },
        }
        row["regressed"] = bool(row["hit"]["baseline"] and not row["hit"]["corrupted"]) or (
            row["token_f1"]["corrupted"] < row["token_f1"]["baseline"] - 0.05
        )
        row["recovered"] = bool(row["regressed"]) and (
            row["hit"]["repaired"] and row["token_f1"]["repaired"] >= row["token_f1"]["baseline"] - 0.05
        )
        rows.append(row)
        if row["regressed"]:
            tracer.emit("evaluation", "question_regressed", row)

    by_type: dict[str, dict[str, Any]] = {}
    for row in rows:
        entry = by_type.setdefault(row["question_type"], {"n": 0, "regressed": 0, "recovered": 0})
        entry["n"] += 1
        entry["regressed"] += int(row["regressed"])
        entry["recovered"] += int(row["recovered"])

    trace = {
        "questions": rows,
        "regressed": [row["id"] for row in rows if row["regressed"]],
        "recovered": [row["id"] for row in rows if row["recovered"]],
        "by_question_type": by_type,
    }
    tracer.emit("evaluation", "answer_trace", {k: v for k, v in trace.items() if k != "questions"})
    return trace


def _mode_comparison(results: list[dict[str, Any]], tracer: Tracer) -> dict[str, Any]:
    modes = {result["mode"]: result for result in results}
    core = {
        mode: {state: {key: result["metrics"][state].get(key) for key in CORE_METRICS} for state in STATES}
        for mode, result in modes.items()
    }
    ragas = {
        mode: {state: result["metrics"][state].get("ragas") for state in STATES}
        for mode, result in modes.items()
    }
    reference = next(iter(core.values())) if core else {}
    identical = all(values == reference for values in core.values())

    comparison = {
        "modes": sorted(modes),
        "core_metrics": core,
        "core_metrics_identical_across_modes": identical,
        "ragas_payloads": ragas,
        "ragas_produced_scores": {
            mode: {
                state: bool(payload) and not {"skipped", "error"} & set(payload)
                for state, payload in states.items()
            }
            for mode, states in ragas.items()
        },
        "stage_durations": {
            mode: {stage: result["stages"][stage]["duration_seconds"] for stage in result["stages"]}
            for mode, result in modes.items()
        },
        "stage_errors": {
            mode: {stage: result["stages"][stage]["error"] for stage in result["stages"] if result["stages"][stage]["error"]}
            for mode, result in modes.items()
        },
    }
    tracer.emit("comparison", "mode_comparison", {k: v for k, v in comparison.items() if k != "core_metrics"})
    return comparison


def _markdown(settings: Settings, comparison: dict[str, Any], dataset: dict[str, Any], quality: dict[str, Any], answers: dict[str, Any]) -> str:
    modes = comparison["modes"]
    multi_mode = len(modes) > 1
    lines = [
        "# Baseline / corrupted / repaired comparison and trace"
        + (" (RUN_RAGAS=1 vs RUN_RAGAS=0)" if multi_mode else f" (RUN_RAGAS={modes[0]})"),
        "",
        f"Generated at: {now_utc().isoformat()}",
        "",
        f"Every mode runs `phase1.main()` then `corruption_flow.main()` in-process with the corruption RNG "
        f"seeded to `{CORRUPTION_SEED}`, so repeated runs corrupt identical rows.",
        "",
        "## 1. " + ("RUN_RAGAS=1 vs RUN_RAGAS=0" if multi_mode else "Metrics per pipeline state"),
        "",
        "| Metric | State | " + " | ".join(f"RUN_RAGAS={mode}" for mode in modes) + " |",
        "| --- | --- | " + " | ".join("---" for _ in modes) + " |",
    ]
    for metric in CORE_METRICS:
        for state in STATES:
            values = []
            for mode in modes:
                value = comparison["core_metrics"][mode][state].get(metric)
                values.append(f"{value:.3f}" if isinstance(value, float) else str(value))
            lines.append(f"| {metric} | {state} | " + " | ".join(values) + " |")

    lines.append("")
    if multi_mode:
        lines.append(
            f"Core metrics identical across modes: **{'yes' if comparison['core_metrics_identical_across_modes'] else 'no'}** "
            "- the flag only controls the extra Ragas pass, not retrieval or answering."
        )
    lines.extend(
        [
            "",
            "### Ragas payload per mode",
            "",
            "| Mode | State | Ragas result |",
            "| --- | --- | --- |",
        ]
    )
    for mode in modes:
        for state in STATES:
            payload = comparison["ragas_payloads"][mode][state]
            lines.append(f"| RUN_RAGAS={mode} | {state} | `{payload}` |")

    lines.extend(
        [
            "",
            "## 2. What corruption did to the dataset",
            "",
            f"Rows: baseline {dataset['row_counts']['baseline']} -> corrupted {dataset['row_counts']['corrupted']} "
            f"-> repaired {dataset['row_counts']['repaired']}",
            "",
            "| Corruption | Records |",
            "| --- | --- |",
        ]
    )
    for tag, count in dataset["corruption_tag_counts"].items():
        lines.append(f"| {tag} | {count} |")

    lines.extend(
        [
            "",
            f"Untouched records: {dataset['untouched_records']} | restored by repair: {dataset['restored_records']}"
            f" | not restored: {len(dataset['unrestored_records'])}",
            "",
            "## 3. How observability reacted",
            "",
            "| State | Quality | Checks passed | Freshness | Stale rows |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for state in STATES:
        statistics = quality["statistics"][state]
        freshness = quality["freshness"][state]
        lines.append(
            f"| {state} | {'PASS' if quality['status'][state] else 'FAIL'} "
            f"| {statistics['passed']}/{statistics['total']} "
            f"| {'FRESH' if freshness['is_fresh'] else 'STALE'} | {freshness['stale_rows']} |"
        )

    lines.extend(["", "Checks that flipped to FAIL on corrupted data:", ""])
    for name, entry in quality["regressed_on_corruption"].items():
        recovered = "recovered" if name in quality["recovered_on_repair"] else "still failing"
        lines.append(
            f"- `{name}` ({entry.get('column') or 'table'}): "
            f"{entry.get('corrupted', {}).get('unexpected_count')} unexpected rows -> {recovered} after repair"
        )
    if not quality["regressed_on_corruption"]:
        lines.append("- none")

    lines.extend(
        [
            "",
            "## 4. How the agent's answers moved",
            "",
            "| Question type | Samples | Regressed on corruption | Recovered after repair |",
            "| --- | --- | --- | --- |",
        ]
    )
    for question_type, entry in sorted(answers["by_question_type"].items()):
        lines.append(f"| {question_type} | {entry['n']} | {entry['regressed']} | {entry['recovered']} |")

    lines.extend(["", "Per-question regressions:", ""])
    for row in answers["questions"]:
        if not row["regressed"]:
            continue
        lines.append(
            f"- `{row['id']}` ({row['question_type']}): hit "
            f"{row['hit']['baseline']}->{row['hit']['corrupted']}->{row['hit']['repaired']}, "
            f"F1 {row['token_f1']['baseline']:.3f}->{row['token_f1']['corrupted']:.3f}->{row['token_f1']['repaired']:.3f}, "
            f"top doc corrupted=`{row['top_doc']['corrupted']}`"
        )
    if not answers["regressed"]:
        lines.append("- none")

    lines.extend(
        [
            "",
            "## 5. Reproduce",
            "",
            "```bash",
            "uv run python script/run_ragas_comparison.py",
            "```",
            "",
            "Per-mode artifact snapshots live in `data/results/ragas_modes/ragas<mode>/`, the structured event log in "
            f"`{_relative(settings, settings.paths.quality_dir / 'pipeline_trace.jsonl')}`.",
            "",
            "A Ragas pass needs a reachable LLM provider: `LLM_PROVIDER`/`LLM_MODEL` plus the matching API key in `.env`. "
            "Without credentials the pass is recorded as an error and the core metrics are unaffected.",
            "",
        ]
    )
    return "\n".join(lines)


def _relative(settings: Settings, path: Path) -> str:
    try:
        return str(path.relative_to(settings.paths.project_dir))
    except ValueError:
        return str(path)


def main() -> None:
    settings = load_settings()
    modes = sys.argv[1:] or DEFAULT_MODES
    tracer = Tracer(settings.paths.quality_dir / "pipeline_trace.jsonl")

    results = [run_mode(settings, tracer, mode) for mode in modes]

    print("\n=== deriving lifecycle trace ===", flush=True)
    snapshot_dir = results[-1]["snapshot_dir"]
    dataset = _dataset_trace(settings, tracer, snapshot_dir)
    quality = _quality_trace(tracer, snapshot_dir)
    answers = _answer_trace(tracer, snapshot_dir)
    comparison = _mode_comparison(results, tracer)

    output_dir = settings.paths.project_dir / "data" / "results" / "ragas_modes"
    write_json(
        output_dir / "comparison.json",
        {
            "generated_at": now_utc().isoformat(),
            "corruption_seed": CORRUPTION_SEED,
            "trace_source_mode": results[-1]["mode"],
            "mode_comparison": comparison,
            "dataset_trace": dataset,
            "quality_trace": quality,
            "answer_trace": answers,
        },
    )
    report_path = settings.paths.project_dir / "data" / "reports" / "ragas_mode_comparison.md"
    write_text(report_path, _markdown(settings, comparison, dataset, quality, answers))
    tracer.flush()

    print(f"\ntrace events : {_relative(settings, tracer.path)} ({len(tracer.events)} events)")
    print(f"comparison   : {_relative(settings, output_dir / 'comparison.json')}")
    print(f"report       : {_relative(settings, report_path)}")


if __name__ == "__main__":
    main()
