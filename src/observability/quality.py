from __future__ import annotations

from pathlib import Path
import sqlite3
from typing import Any

import pandas as pd

try:  # Great Expectations is preferred, but the CP1 checks remain runnable without it.
    import great_expectations as gx
except ImportError:  # pragma: no cover - exercised only in lightweight environments.
    gx = None

from core.config import Settings
from core.utils import normalize_whitespace, now_utc, read_json, safe_slug, write_json
from ingestion.cleaning import MIN_SUMMARY_CHARS, MIN_TITLE_CHARS, PUBLISHED_PATTERN

MIN_EXPECTED_ROWS = 10
GX_DATASOURCE_NAME = "papers"
AGE_TOLERANCE_DAYS = 1


def _expectations(settings: Settings) -> list[Any]:
    if gx is None:
        return []
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


def _manual_check(
    expectation: str,
    column: str,
    success: bool,
    observed_value: Any,
    unexpected_count: int = 0,
    unexpected_examples: list[Any] | None = None,
) -> dict[str, Any]:
    return {
        "expectation": expectation,
        "column": column,
        "success": bool(success),
        "observed_value": observed_value,
        "element_count": None,
        "unexpected_count": int(unexpected_count),
        "unexpected_percent": None,
        "unexpected_examples": (unexpected_examples or [])[:5],
        "error": None,
    }


def _series_or_blank(df: pd.DataFrame, column: str) -> pd.Series:
    if column not in df.columns:
        return pd.Series([""] * len(df), index=df.index, dtype="object")
    return df[column].fillna("").astype(str).map(normalize_whitespace)


def _contract_checks(df: pd.DataFrame, settings: Settings) -> list[dict[str, Any]]:
    """Checks explicitly required by CP1, independent of the GX runtime."""

    checks: list[dict[str, Any]] = []
    checks.append(
        _manual_check(
            "cp1_table_row_count_minimum",
            "",
            len(df) >= MIN_EXPECTED_ROWS,
            int(len(df)),
            0 if len(df) >= MIN_EXPECTED_ROWS else MIN_EXPECTED_ROWS - len(df),
        )
    )

    required_columns = ["paper_id", "title", "summary", "text_for_embedding", "published", "age_days"]
    missing_columns = [column for column in required_columns if column not in df.columns]
    checks.append(
        _manual_check(
            "cp1_required_columns_present",
            "",
            not missing_columns,
            sorted(df.columns.tolist()),
            len(missing_columns),
            missing_columns,
        )
    )

    paper_ids = _series_or_blank(df, "paper_id").str.lower()
    blank_paper_ids = paper_ids.eq("")
    duplicate_paper_ids = paper_ids.ne("") & paper_ids.duplicated(keep=False)
    checks.extend(
        [
            _manual_check(
                "cp1_paper_id_not_blank",
                "paper_id",
                not blank_paper_ids.any(),
                int(blank_paper_ids.sum()),
                int(blank_paper_ids.sum()),
                df.index[blank_paper_ids].tolist(),
            ),
            _manual_check(
                "cp1_paper_id_unique_normalized",
                "paper_id",
                not duplicate_paper_ids.any(),
                int(duplicate_paper_ids.sum()),
                int(duplicate_paper_ids.sum()),
                paper_ids[duplicate_paper_ids].tolist(),
            ),
        ]
    )

    titles = _series_or_blank(df, "title")
    normalized_titles = titles.str.casefold()
    blank_titles = titles.eq("")
    short_titles = titles.str.len().lt(MIN_TITLE_CHARS)
    duplicate_titles = normalized_titles.ne("") & normalized_titles.duplicated(keep=False)
    checks.extend(
        [
            _manual_check(
                "cp1_title_not_blank",
                "title",
                not blank_titles.any(),
                int(blank_titles.sum()),
                int(blank_titles.sum()),
                df.index[blank_titles].tolist(),
            ),
            _manual_check(
                "cp1_title_min_length",
                "title",
                not short_titles.any(),
                int(short_titles.sum()),
                int(short_titles.sum()),
                titles[short_titles].tolist(),
            ),
            _manual_check(
                "cp1_title_unique_normalized",
                "title",
                not duplicate_titles.any(),
                int(duplicate_titles.sum()),
                int(duplicate_titles.sum()),
                titles[duplicate_titles].tolist(),
            ),
        ]
    )

    summaries = _series_or_blank(df, "summary")
    blank_summaries = summaries.eq("")
    short_summaries = summaries.str.len().lt(MIN_SUMMARY_CHARS)
    checks.extend(
        [
            _manual_check(
                "cp1_summary_not_blank",
                "summary",
                not blank_summaries.any(),
                int(blank_summaries.sum()),
                int(blank_summaries.sum()),
                df.index[blank_summaries].tolist(),
            ),
            _manual_check(
                "cp1_summary_min_length",
                "summary",
                not short_summaries.any(),
                int(short_summaries.sum()),
                int(short_summaries.sum()),
                summaries[short_summaries].tolist(),
            ),
        ]
    )

    embedding_text = _series_or_blank(df, "text_for_embedding")
    blank_embedding_text = embedding_text.eq("")
    checks.append(
        _manual_check(
            "cp1_text_for_embedding_not_blank",
            "text_for_embedding",
            not blank_embedding_text.any(),
            int(blank_embedding_text.sum()),
            int(blank_embedding_text.sum()),
            df.index[blank_embedding_text].tolist(),
        )
    )

    published_text = _series_or_blank(df, "published")
    published = pd.to_datetime(published_text, errors="coerce", utc=True)
    invalid_published = published.isna()
    age_days = pd.to_numeric(df["age_days"], errors="coerce") if "age_days" in df.columns else pd.Series(float("nan"), index=df.index)
    invalid_age = age_days.isna() | age_days.lt(0)
    stale_age = age_days.gt(settings.freshness_threshold_days)
    generated_at = now_utc()
    computed_age = (pd.Timestamp(generated_at).normalize() - published.dt.normalize()).dt.days
    age_mismatch = (~invalid_published & ~age_days.isna() & (computed_age.sub(age_days).abs() > AGE_TOLERANCE_DAYS))
    checks.extend(
        [
            _manual_check(
                "cp1_published_valid_date",
                "published",
                not invalid_published.any(),
                int(invalid_published.sum()),
                int(invalid_published.sum()),
                published_text[invalid_published].tolist(),
            ),
            _manual_check(
                "cp1_age_days_non_negative",
                "age_days",
                not invalid_age.any(),
                int(invalid_age.sum()),
                int(invalid_age.sum()),
                age_days[invalid_age].tolist(),
            ),
            _manual_check(
                "cp1_age_days_within_freshness_threshold",
                "age_days",
                not stale_age.any(),
                int(stale_age.sum()),
                int(stale_age.sum()),
                age_days[stale_age].tolist(),
            ),
            _manual_check(
                "cp1_age_days_matches_published",
                "age_days,published",
                not age_mismatch.any(),
                int(age_mismatch.sum()),
                int(age_mismatch.sum()),
                [
                    {
                        "published": published_text.loc[index],
                        "stored_age_days": None if pd.isna(age_days.loc[index]) else int(age_days.loc[index]),
                        "computed_age_days": None if pd.isna(computed_age.loc[index]) else int(computed_age.loc[index]),
                    }
                    for index in df.index[age_mismatch][:5]
                ],
            ),
        ]
    )

    source_timestamp_column = "ingested_at" if "ingested_at" in df.columns else "updated" if "updated" in df.columns else ""
    source_timestamp_text = _series_or_blank(df, source_timestamp_column) if source_timestamp_column else _series_or_blank(df, "ingested_at")
    source_timestamp = pd.to_datetime(source_timestamp_text, errors="coerce", utc=True)
    invalid_source_timestamp = source_timestamp.isna()
    checks.append(
        _manual_check(
            "cp1_source_timestamp_present",
            source_timestamp_column or "ingested_at|updated",
            bool(source_timestamp_column) and not invalid_source_timestamp.any(),
            {
                "column": source_timestamp_column or None,
                "invalid_rows": int(invalid_source_timestamp.sum()),
            },
            int(invalid_source_timestamp.sum()) if source_timestamp_column else len(df),
            source_timestamp_text[invalid_source_timestamp].tolist(),
        )
    )
    return checks


def _run_gx_checks(df: pd.DataFrame, settings: Settings, slug: str) -> tuple[list[dict[str, Any]], dict[str, Any], str]:
    if gx is None:
        return [], {}, "manual CP1 contract checks (great_expectations unavailable)"

    settings.paths.quality_dir.mkdir(parents=True, exist_ok=True)
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
    return (
        [_check_payload(item) for item in result.get("results", [])],
        result.get("statistics", {}),
        f"great_expectations {gx.__version__} + CP1 contract checks",
    )


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    slug = safe_slug(report_name)
    settings.paths.quality_dir.mkdir(parents=True, exist_ok=True)

    gx_checks, gx_statistics, engine = _run_gx_checks(df, settings, slug)
    contract_checks = _contract_checks(df, settings)
    checks = gx_checks + contract_checks
    successful = sum(1 for check in checks if check["success"])
    failed = len(checks) - successful
    report_path = settings.paths.quality_dir / f"{slug}.json"
    payload = {
        "report_name": report_name,
        "generated_at": now_utc().isoformat(),
        "engine": engine,
        "row_count": int(len(df)),
        "column_count": int(len(df.columns)),
        "success": failed == 0,
        "statistics": {
            "evaluated_expectations": len(checks),
            "successful_expectations": successful,
            "unsuccessful_expectations": failed,
            "success_percent": round(successful / len(checks) * 100, 2) if checks else 0.0,
            "great_expectations": gx_statistics,
        },
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
            "invalid_published_rows": 0,
            "invalid_age_days_rows": 0,
            "age_mismatch_rows": 0,
            "latest_published": None,
            "oldest_published": None,
            "days_since_latest_publication": None,
            "max_age_days": None,
            "mean_age_days": None,
            "latest_ingested_at": None,
            "source_lag_hours": None,
            "is_fresh": False,
            "notes": "Dataset is empty, freshness cannot be established.",
        }
        write_json(report_path, payload)
        return payload

    published = pd.to_datetime(_series_or_blank(df, "published"), errors="coerce", utc=True)
    age_days = pd.to_numeric(_series_or_blank(df, "age_days"), errors="coerce")
    source_timestamp_column = "ingested_at" if "ingested_at" in df.columns else "updated" if "updated" in df.columns else ""
    source_timestamp = pd.to_datetime(
        _series_or_blank(df, source_timestamp_column) if source_timestamp_column else _series_or_blank(df, "ingested_at"),
        errors="coerce",
        utc=True,
    )
    latest = published.max()
    oldest = published.min()
    latest_ingested_at = source_timestamp.max()

    computed_age_days = (pd.Timestamp(generated_at).normalize() - published.dt.normalize()).dt.days
    invalid_published = published.isna()
    invalid_age_days = age_days.isna() | age_days.lt(0)
    stale_by_stored_age = age_days.gt(threshold)
    stale_by_published_age = computed_age_days.gt(threshold)
    stale_mask = stale_by_stored_age | stale_by_published_age | invalid_published | invalid_age_days
    age_mismatch = (~invalid_published & ~age_days.isna() & (computed_age_days.sub(age_days).abs() > AGE_TOLERANCE_DAYS))

    days_since_latest = int((generated_at - latest).days) if pd.notna(latest) else None
    source_lag_hours = round((generated_at - latest_ingested_at).total_seconds() / 3600, 2) if pd.notna(latest_ingested_at) else None
    stale_rows = int(stale_mask.sum())

    payload = {
        "generated_at": generated_at.isoformat(),
        "threshold_days": threshold,
        "total_rows": int(len(df)),
        "stale_rows": stale_rows,
        "fresh_rows": int(len(df) - stale_rows),
        "invalid_published_rows": int(invalid_published.sum()),
        "invalid_age_days_rows": int(invalid_age_days.sum()),
        "age_mismatch_rows": int(age_mismatch.sum()),
        "latest_published": latest.date().isoformat() if pd.notna(latest) else None,
        "oldest_published": oldest.date().isoformat() if pd.notna(oldest) else None,
        "days_since_latest_publication": days_since_latest,
        "max_age_days": int(age_days.max()) if age_days.notna().any() else None,
        "mean_age_days": round(float(age_days.mean()), 2) if age_days.notna().any() else None,
        "source_timestamp_column": source_timestamp_column or None,
        "latest_ingested_at": latest_ingested_at.isoformat() if pd.notna(latest_ingested_at) else None,
        "source_lag_hours": source_lag_hours,
        "is_fresh": stale_rows == 0 and not age_mismatch.any() and days_since_latest is not None and days_since_latest <= threshold,
        "notes": (
            f"Fresh means published/age_days are valid, consistent within {AGE_TOLERANCE_DAYS} day, "
            f"and no row is older than {threshold} days."
        ),
    }
    write_json(report_path, payload)
    return payload


def _audit_check(name: str, success: bool, observed: Any, expected: Any = None) -> dict[str, Any]:
    return {
        "check": name,
        "success": bool(success),
        "observed": observed,
        "expected": expected,
    }


def _read_chroma_collection_snapshot(database_path: Path, collection_name: str) -> dict[str, Any]:
    """Read collection identity and metadata IDs from Chroma's SQLite catalog.

    Chroma stores document metadata in its SQLite metadata segment while HNSW vectors
    live in separate binary files.  Reading this catalog avoids loading the embedding
    model and makes the CP2 audit cheap and reproducible.
    """

    if not database_path.exists():
        return {
            "database_exists": False,
            "collection_exists": False,
            "collection_name": collection_name,
            "document_count": 0,
            "paper_ids": [],
            "dimension": None,
            "error": f"Missing Chroma database: {database_path}",
        }

    try:
        connection = sqlite3.connect(database_path)
        connection.row_factory = sqlite3.Row
        collection = connection.execute(
            "SELECT id, name, dimension FROM collections WHERE name = ? LIMIT 1",
            (collection_name,),
        ).fetchone()
        if collection is None:
            return {
                "database_exists": True,
                "collection_exists": False,
                "collection_name": collection_name,
                "document_count": 0,
                "paper_ids": [],
                "dimension": None,
                "error": f"Collection not found: {collection_name}",
            }

        metadata_segment = connection.execute(
            "SELECT id FROM segments WHERE collection = ? AND scope = 'METADATA' LIMIT 1",
            (collection["id"],),
        ).fetchone()
        if metadata_segment is None:
            return {
                "database_exists": True,
                "collection_exists": True,
                "collection_name": collection_name,
                "document_count": 0,
                "paper_ids": [],
                "dimension": collection["dimension"],
                "error": "Collection has no METADATA segment.",
            }

        paper_id_rows = connection.execute(
            """
            SELECT em.string_value AS paper_id
            FROM embeddings AS e
            JOIN embedding_metadata AS em ON em.id = e.id
            WHERE e.segment_id = ? AND em.key = 'paper_id'
            ORDER BY e.id
            """,
            (metadata_segment["id"],),
        ).fetchall()
        document_count = connection.execute(
            "SELECT COUNT(*) FROM embeddings WHERE segment_id = ?",
            (metadata_segment["id"],),
        ).fetchone()[0]
        paper_ids = [normalize_whitespace(str(row["paper_id"])).lower() for row in paper_id_rows]
        return {
            "database_exists": True,
            "collection_exists": True,
            "collection_name": collection_name,
            "document_count": int(document_count),
            "paper_ids": paper_ids,
            "dimension": collection["dimension"],
            "error": None,
        }
    except (sqlite3.DatabaseError, KeyError, TypeError) as exc:
        return {
            "database_exists": True,
            "collection_exists": False,
            "collection_name": collection_name,
            "document_count": 0,
            "paper_ids": [],
            "dimension": None,
            "error": str(exc),
        }
    finally:
        try:
            connection.close()
        except UnboundLocalError:
            pass


def audit_baseline_index(
    df: pd.DataFrame,
    settings: Settings,
    manifest_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    """Audit the CP2 clean -> manifest -> Chroma contract without rebuilding the index."""

    manifest = read_json(manifest_path) if manifest_path.exists() else {}
    documents = manifest.get("documents") if isinstance(manifest, dict) else None
    documents = documents if isinstance(documents, list) else []

    clean_ids = [value.lower() for value in _series_or_blank(df, "paper_id") if value]
    manifest_ids = [
        normalize_whitespace(str(document.get("paper_id", ""))).lower()
        for document in documents
        if isinstance(document, dict)
    ]
    clean_id_set = set(clean_ids)
    manifest_id_set = {value for value in manifest_ids if value}
    expected_collection_name = settings.baseline_collection_name
    actual_collection_name = manifest.get("collection_name") if isinstance(manifest, dict) else None
    chroma_database = settings.paths.chroma_dir / "chroma.sqlite3"
    collection = _read_chroma_collection_snapshot(chroma_database, str(actual_collection_name or expected_collection_name))
    index_ids = collection.get("paper_ids", [])
    index_id_set = set(index_ids)

    manifest_relative = str(manifest_path.relative_to(settings.paths.project_dir))
    chroma_relative = str(chroma_database.relative_to(settings.paths.project_dir))
    required_manifest_fields = {"backend", "embedding_model", "persist_path", "collection_name", "documents"}
    missing_manifest_fields = sorted(required_manifest_fields - set(manifest)) if isinstance(manifest, dict) else sorted(required_manifest_fields)
    duplicate_manifest_ids = sorted({value for value in manifest_ids if value and manifest_ids.count(value) > 1})
    duplicate_index_ids = sorted({value for value in index_ids if value and index_ids.count(value) > 1})

    checks = [
        _audit_check("manifest_exists", manifest_path.exists(), manifest_relative),
        _audit_check("manifest_required_fields", not missing_manifest_fields, missing_manifest_fields, []),
        _audit_check("backend_is_chroma", manifest.get("backend") == "chroma", manifest.get("backend"), "chroma"),
        _audit_check(
            "embedding_model_matches_settings",
            manifest.get("embedding_model") == settings.embedding_model,
            manifest.get("embedding_model"),
            settings.embedding_model,
        ),
        _audit_check(
            "collection_name_is_baseline",
            actual_collection_name == expected_collection_name,
            actual_collection_name,
            expected_collection_name,
        ),
        _audit_check("manifest_document_count_matches_clean", len(documents) == len(df), len(documents), int(len(df))),
        _audit_check("manifest_paper_ids_are_unique", not duplicate_manifest_ids, duplicate_manifest_ids, []),
        _audit_check("manifest_paper_ids_match_clean", manifest_id_set == clean_id_set, sorted(manifest_id_set ^ clean_id_set), []),
        _audit_check("chroma_database_exists", collection["database_exists"], chroma_relative),
        _audit_check("baseline_collection_exists", collection["collection_exists"], collection.get("error"), None),
        _audit_check(
            "collection_document_count_matches_clean",
            collection.get("document_count") == len(df),
            collection.get("document_count"),
            int(len(df)),
        ),
        _audit_check("collection_paper_ids_are_unique", not duplicate_index_ids, duplicate_index_ids, []),
        _audit_check("collection_paper_ids_match_clean", index_id_set == clean_id_set, sorted(index_id_set ^ clean_id_set), []),
        _audit_check("embedding_dimension_is_minilm", collection.get("dimension") == 384, collection.get("dimension"), 384),
    ]

    recorded_persist_path = str(manifest.get("persist_path", "")) if isinstance(manifest, dict) else ""
    runtime_persist_path = str(settings.paths.chroma_dir)
    warnings: list[str] = []
    if recorded_persist_path and Path(recorded_persist_path) != settings.paths.chroma_dir:
        warnings.append(
            "Manifest persist_path was created on another machine; runtime uses settings.paths.chroma_dir. "
            "This does not affect LocalEmbeddingIndex.load because it resolves the configured project path."
        )

    failed_checks = [check["check"] for check in checks if not check["success"]]
    payload = {
        "generated_at": now_utc().isoformat(),
        "success": not failed_checks,
        "manifest_path": manifest_relative,
        "recorded_persist_path": recorded_persist_path,
        "runtime_persist_path": str(settings.paths.chroma_dir.relative_to(settings.paths.project_dir)),
        "chroma_database": chroma_relative,
        "backend": manifest.get("backend"),
        "embedding_model": manifest.get("embedding_model"),
        "collection_name": actual_collection_name,
        "embedding_dimension": collection.get("dimension"),
        "clean_document_count": int(len(df)),
        "manifest_document_count": len(documents),
        "collection_document_count": collection.get("document_count", 0),
        "indexed_paper_ids": index_ids,
        "failed_checks": failed_checks,
        "warnings": warnings,
        "checks": checks,
    }
    write_json(output_path, payload)
    return payload
