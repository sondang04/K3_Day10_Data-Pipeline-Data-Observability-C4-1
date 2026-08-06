from __future__ import annotations

from typing import Any

import great_expectations as gx
import pandas as pd

from core.config import Settings
from core.utils import now_utc, safe_slug, write_json
from ingestion.cleaning import MIN_SUMMARY_CHARS, MIN_TITLE_CHARS, PUBLISHED_PATTERN

MIN_EXPECTED_ROWS = 10
GX_DATASOURCE_NAME = "papers"


def _expectations(settings: Settings) -> list[Any]:
    return [
        gx.expectations.ExpectTableRowCountToBeBetween(min_value=MIN_EXPECTED_ROWS),
        gx.expectations.ExpectColumnValuesToNotBeNull(column="paper_id"),
        gx.expectations.ExpectColumnValuesToBeUnique(column="paper_id"),
        gx.expectations.ExpectColumnValuesToNotBeNull(column="title"),
        gx.expectations.ExpectColumnValueLengthsToBeBetween(column="title", min_value=MIN_TITLE_CHARS),
        gx.expectations.ExpectColumnValuesToNotBeNull(column="summary"),
        gx.expectations.ExpectColumnValueLengthsToBeBetween(column="summary", min_value=MIN_SUMMARY_CHARS),
        gx.expectations.ExpectColumnValuesToNotBeNull(column="text_for_embedding"),
        gx.expectations.ExpectColumnValuesToMatchRegex(column="published", regex=PUBLISHED_PATTERN),
        gx.expectations.ExpectColumnValuesToBeBetween(
            column="age_days",
            min_value=0,
            max_value=settings.freshness_threshold_days,
        ),
    ]


def _check_payload(result: dict[str, Any]) -> dict[str, Any]:
    config = result.get("expectation_config", {})
    details = result.get("result", {})
    exception_info = result.get("exception_info") or {}
    return {
        "expectation": config.get("type", "unknown"),
        "column": config.get("kwargs", {}).get("column", ""),
        "success": bool(result.get("success")),
        "observed_value": details.get("observed_value"),
        "element_count": details.get("element_count"),
        "unexpected_count": details.get("unexpected_count"),
        "unexpected_percent": details.get("unexpected_percent"),
        "unexpected_examples": details.get("partial_unexpected_list", [])[:5],
        "error": exception_info.get("exception_message"),
    }


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    slug = safe_slug(report_name)
    settings.paths.quality_dir.mkdir(parents=True, exist_ok=True)

    # A file context materialises its project under `<project_root_dir>/gx`, i.e. `paths.gx_dir`.
    context = gx.get_context(mode="file", project_root_dir=str(settings.paths.quality_dir))
    data_source = context.data_sources.add_or_update_pandas(GX_DATASOURCE_NAME)
    batch_definition = data_source.add_dataframe_asset(slug).add_batch_definition_whole_dataframe("batch")

    suite = context.suites.add_or_update(gx.ExpectationSuite(name=f"{slug}-suite"))
    for expectation in _expectations(settings):
        suite.add_expectation(expectation)

    validation_definition = context.validation_definitions.add_or_update(
        gx.ValidationDefinition(data=batch_definition, suite=suite, name=f"{slug}-validation")
    )
    result = validation_definition.run(batch_parameters={"dataframe": df}).to_json_dict()

    checks = [_check_payload(item) for item in result.get("results", [])]
    report_path = settings.paths.quality_dir / f"{slug}.json"
    payload = {
        "report_name": report_name,
        "generated_at": now_utc().isoformat(),
        "engine": f"great_expectations {gx.__version__}",
        "row_count": int(len(df)),
        "column_count": int(len(df.columns)),
        "success": bool(result.get("success")),
        "statistics": result.get("statistics", {}),
        "failed_checks": [check["expectation"] for check in checks if not check["success"]],
        "checks": checks,
        "report_path": str(report_path.relative_to(settings.paths.project_dir)),
    }
    write_json(report_path, payload)
    return payload


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path) -> dict[str, Any]:
    threshold = settings.freshness_threshold_days
    generated_at = now_utc()

    if df.empty:
        payload = {
            "generated_at": generated_at.isoformat(),
            "threshold_days": threshold,
            "total_rows": 0,
            "stale_rows": 0,
            "fresh_rows": 0,
            "latest_published": None,
            "oldest_published": None,
            "days_since_latest_publication": None,
            "max_age_days": None,
            "mean_age_days": None,
            "is_fresh": False,
            "notes": "Dataset is empty, freshness cannot be established.",
        }
        write_json(report_path, payload)
        return payload

    published = pd.to_datetime(df["published"], errors="coerce", utc=True)
    age_days = pd.to_numeric(df["age_days"], errors="coerce")
    latest = published.max()
    oldest = published.min()
    # Recompute from `published` as well: corruption can backdate publications while
    # leaving the stored `age_days` untouched.
    days_since_latest = int((generated_at - latest).days) if pd.notna(latest) else None
    stale_rows = int((age_days > threshold).sum())

    payload = {
        "generated_at": generated_at.isoformat(),
        "threshold_days": threshold,
        "total_rows": int(len(df)),
        "stale_rows": stale_rows,
        "fresh_rows": int(len(df) - stale_rows),
        "latest_published": latest.date().isoformat() if pd.notna(latest) else None,
        "oldest_published": oldest.date().isoformat() if pd.notna(oldest) else None,
        "days_since_latest_publication": days_since_latest,
        "max_age_days": int(age_days.max()) if age_days.notna().any() else None,
        "mean_age_days": round(float(age_days.mean()), 2) if age_days.notna().any() else None,
        "is_fresh": stale_rows == 0 and days_since_latest is not None and days_since_latest <= threshold,
        "notes": f"Fresh means every row is younger than {threshold} days.",
    }
    write_json(report_path, payload)
    return payload
