from __future__ import annotations

import pandas as pd

from core.config import load_settings
from core.utils import read_json
from evaluation.testset import build_test_set, validate_test_set
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_role4_cp0_cp1_report


def main() -> None:
    settings = load_settings()
    clean_path = settings.paths.clean_csv
    if not clean_path.exists():
        raise FileNotFoundError(
            f"Clean data is required for CP1 but was not found: {clean_path}. "
            "Wait for the cleaning owner to write papers_clean.csv."
        )

    df = pd.read_csv(clean_path)
    if settings.paths.eval_testset.exists():
        test_set = read_json(settings.paths.eval_testset)
    else:
        test_set = build_test_set(df, settings.paths.eval_testset)
    test_set_validation = validate_test_set(test_set, df)

    quality = run_data_quality_checks(df, settings, "baseline_quality")
    freshness = build_freshness_report(df, settings, settings.paths.freshness_report)

    report_path = settings.paths.project_dir / "data" / "reports" / "role4_cp0_cp1_report.md"
    generate_role4_cp0_cp1_report(
        report_path=report_path,
        clean_path=str(clean_path.relative_to(settings.paths.project_dir)),
        test_set_path=str(settings.paths.eval_testset.relative_to(settings.paths.project_dir)),
        test_set_validation=test_set_validation,
        quality=quality,
        freshness=freshness,
    )

    print("[role4] CP0-CP1 complete")
    print(f"        clean rows: {len(df)}")
    print(f"        test samples: {test_set_validation['sample_count']}")
    print(f"        quality: {'PASS' if quality['success'] else 'FAIL'}")
    print(f"        freshness: {'FRESH' if freshness['is_fresh'] else 'STALE/INVALID'}")
    print(f"        report: {report_path.relative_to(settings.paths.project_dir)}")


if __name__ == "__main__":
    main()
