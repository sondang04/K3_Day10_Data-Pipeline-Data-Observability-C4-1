from __future__ import annotations

from hashlib import sha256
from pathlib import Path

import pandas as pd

from core.config import load_settings
from core.utils import read_json
from evaluation.testset import (
    build_test_set,
    validate_test_set,
    validate_test_set_against_index,
)
from observability.quality import (
    audit_baseline_index,
    build_freshness_report,
    run_data_quality_checks,
)
from observability.reporting import (
    generate_phase1_cp2_template,
    generate_role4_cp2_report,
)


PREVIEW_SAMPLE_COUNT = 5


def _relative(project_dir: Path, path: Path) -> str:
    try:
        return str(path.relative_to(project_dir))
    except ValueError:
        return str(path)


def _file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    settings = load_settings()
    clean_path = settings.paths.clean_csv
    manifest_path = settings.paths.embeddings_json
    test_set_path = settings.paths.eval_testset

    if not clean_path.exists():
        raise FileNotFoundError(f"CP2 requires clean data: {clean_path}")
    if not manifest_path.exists():
        raise FileNotFoundError(
            f"CP2 requires the baseline embedding manifest from role 3: {manifest_path}"
        )

    df = pd.read_csv(clean_path)
    if test_set_path.exists():
        test_set = read_json(test_set_path)
        test_set_source = "locked-existing"
    else:
        test_set = build_test_set(df, test_set_path)
        test_set_source = "generated-once"

    clean_validation = validate_test_set(test_set, df)
    test_set_hash = _file_sha256(test_set_path)

    audit_path = settings.paths.quality_dir / "role4_cp2_index_audit.json"
    index_audit = audit_baseline_index(df, settings, manifest_path, audit_path)
    index_validation = validate_test_set_against_index(
        test_set,
        index_audit.get("indexed_paper_ids", []),
    )

    quality = run_data_quality_checks(df, settings, "role4_cp2_baseline_quality")
    freshness_path = settings.paths.quality_dir / "role4_cp2_freshness_snapshot.json"
    freshness = build_freshness_report(df, settings, freshness_path)

    report_path = settings.paths.project_dir / "data" / "reports" / "role4_cp2_report.md"
    template_path = settings.paths.project_dir / "data" / "reports" / "phase1_report_cp2_template.md"
    generate_role4_cp2_report(
        report_path=report_path,
        test_set_path=_relative(settings.paths.project_dir, test_set_path),
        test_set_hash=test_set_hash,
        test_set_validation=clean_validation,
        index_validation=index_validation,
        index_audit=index_audit,
        quality=quality,
        freshness=freshness,
        preview_samples=test_set[:PREVIEW_SAMPLE_COUNT],
    )
    generate_phase1_cp2_template(
        report_path=template_path,
        test_set_hash=test_set_hash,
        test_set_validation=clean_validation,
        index_audit=index_audit,
        quality=quality,
        freshness=freshness,
    )

    success = all(
        [
            clean_validation["success"],
            index_validation["success"],
            index_audit["success"],
            quality["success"],
            freshness["is_fresh"],
        ]
    )
    print("[role4] CP2 complete" if success else "[role4] CP2 requires review")
    print(f"        test set: {len(test_set)} samples ({test_set_source})")
    print(f"        test set sha256: {test_set_hash}")
    print(
        f"        index: {index_audit.get('collection_name')} "
        f"({index_audit.get('collection_document_count')} documents)"
    )
    print(f"        test IDs in index: {'PASS' if index_validation['success'] else 'FAIL'}")
    print(f"        quality: {'PASS' if quality['success'] else 'FAIL'}")
    print(f"        freshness: {'FRESH' if freshness['is_fresh'] else 'STALE/INVALID'}")
    print(f"        report: {_relative(settings.paths.project_dir, report_path)}")
    print(f"        CP3 template: {_relative(settings.paths.project_dir, template_path)}")

    if not success:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
