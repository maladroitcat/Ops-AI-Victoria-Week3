"""Week 3 data quality validation."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

import pandas as pd


REQUIRED_COLUMNS = {
    "PULocationID",
    "time_bucket",
    "trip_count",
    "is_holiday",
    "lag_1h",
}

CRITICAL_NONNULL_COLUMNS = {
    "PULocationID",
    "time_bucket",
    "trip_count",
}


@dataclass
class ValidationThresholds:
    max_duplicate_pct: float = 0.05
    max_negative_pct: float = 0.001
    max_outlier_pct: float = 0.002
    max_holiday_rate_delta: float = 0.10
    max_corr_delta: float = 0.30
    outlier_quantile: float = 0.999


class DataQualityValidator:
    """Validate incoming data against baseline expectations."""

    def __init__(self, baseline_df: pd.DataFrame, thresholds: ValidationThresholds | None = None):
        self.baseline = baseline_df.copy()
        self.baseline["time_bucket"] = pd.to_datetime(self.baseline["time_bucket"])
        self.thresholds = thresholds or ValidationThresholds()
        self.issues: List[Dict] = []

    def validate(self, df: pd.DataFrame) -> Dict:
        self.issues = []
        current = df.copy()
        if "time_bucket" in current.columns:
            current["time_bucket"] = pd.to_datetime(current["time_bucket"])

        self.check_non_empty(current)
        self.check_critical_not_all_null(current)

        self.check_schema(current)
        self.check_duplicates(current)
        self.check_negative_values(current)
        self.check_outliers(current)
        self.check_holiday_rate_shift(current)
        self.check_correlation_shift(current)

        severity_rank = {"critical": 3, "high": 2, "medium": 1, "low": 0}
        max_severity = max((severity_rank[i["severity"]] for i in self.issues), default=0)
        # Week 3 strategy: block only on critical contract breaks.
        is_valid = max_severity < severity_rank["critical"]
        return {
            "is_valid": is_valid,
            "num_issues": len(self.issues),
            "issues": self.issues,
            "failed_severities": sorted({i["severity"] for i in self.issues}),
        }

    def check_non_empty(self, df: pd.DataFrame) -> None:
        if len(df) == 0:
            self._add_issue(
                issue_type="empty_dataset",
                severity="critical",
                description="Incoming dataset is empty after filtering.",
                count=0,
            )

    def check_critical_not_all_null(self, df: pd.DataFrame) -> None:
        for col in sorted(CRITICAL_NONNULL_COLUMNS):
            if col in df.columns and df[col].isna().all():
                self._add_issue(
                    issue_type="critical_all_null_column",
                    severity="critical",
                    description=f"Critical column is entirely null: {col}",
                    column=col,
                )

    def check_schema(self, df: pd.DataFrame) -> None:
        missing = sorted(REQUIRED_COLUMNS - set(df.columns))
        if missing:
            self._add_issue(
                issue_type="schema_missing_columns",
                severity="critical",
                description="Required columns are missing.",
                count=len(missing),
                columns=missing,
            )

    def check_duplicates(self, df: pd.DataFrame) -> None:
        if not {"PULocationID", "time_bucket"}.issubset(df.columns):
            return
        dup_mask = df.duplicated(subset=["PULocationID", "time_bucket"], keep=False)
        dup_rows = int(dup_mask.sum())
        dup_pct = dup_rows / len(df) if len(df) else 0.0
        if dup_rows > 0:
            severity = "high" if dup_pct > self.thresholds.max_duplicate_pct else "medium"
            self._add_issue(
                issue_type="duplicate_keys",
                severity=severity,
                description="Duplicate rows found for (PULocationID, time_bucket).",
                count=dup_rows,
                duplicate_pct=dup_pct,
                threshold=self.thresholds.max_duplicate_pct,
            )

    def check_negative_values(self, df: pd.DataFrame) -> None:
        if "trip_count" not in df.columns:
            return
        neg_rows = int((df["trip_count"] < 0).sum())
        neg_pct = neg_rows / len(df) if len(df) else 0.0
        if neg_rows > 0:
            severity = "high" if neg_pct > self.thresholds.max_negative_pct else "medium"
            self._add_issue(
                issue_type="negative_trip_count",
                severity=severity,
                description="trip_count contains negative values.",
                count=neg_rows,
                negative_pct=neg_pct,
                threshold=self.thresholds.max_negative_pct,
            )

    def check_outliers(self, df: pd.DataFrame) -> None:
        if "trip_count" not in df.columns:
            return
        upper = float(self.baseline["trip_count"].quantile(self.thresholds.outlier_quantile))
        out_rows = int((df["trip_count"] > upper).sum())
        out_pct = out_rows / len(df) if len(df) else 0.0
        if out_rows > 0:
            severity = "high" if out_pct > self.thresholds.max_outlier_pct else "medium"
            self._add_issue(
                issue_type="trip_count_outliers",
                severity=severity,
                description="trip_count exceeds baseline high quantile threshold.",
                count=out_rows,
                outlier_pct=out_pct,
                upper_threshold=upper,
                baseline_quantile=self.thresholds.outlier_quantile,
            )

    def check_holiday_rate_shift(self, df: pd.DataFrame) -> None:
        if "is_holiday" not in df.columns:
            return
        b_rate = float(self.baseline["is_holiday"].mean())
        c_rate = float(df["is_holiday"].mean())
        delta = c_rate - b_rate
        if abs(delta) > self.thresholds.max_holiday_rate_delta:
            self._add_issue(
                issue_type="holiday_rate_shift",
                severity="medium",
                description="Holiday flag rate shifted versus baseline.",
                baseline_rate=b_rate,
                current_rate=c_rate,
                abs_delta=abs(delta),
                threshold=self.thresholds.max_holiday_rate_delta,
            )

    def check_correlation_shift(self, df: pd.DataFrame) -> None:
        needed = {"lag_1h", "trip_count"}
        if not needed.issubset(df.columns) or not needed.issubset(self.baseline.columns):
            return
        b = self.baseline[list(needed)].dropna()
        c = df[list(needed)].dropna()
        if len(b) < 10 or len(c) < 10:
            return
        b_corr = float(b["lag_1h"].corr(b["trip_count"]))
        c_corr = float(c["lag_1h"].corr(c["trip_count"]))
        delta = abs(c_corr - b_corr)
        if delta > self.thresholds.max_corr_delta:
            self._add_issue(
                issue_type="lag_trip_correlation_shift",
                severity="high",
                description="lag_1h relationship with trip_count shifted versus baseline.",
                baseline_corr=b_corr,
                current_corr=c_corr,
                abs_delta=delta,
                threshold=self.thresholds.max_corr_delta,
            )

    def _add_issue(self, issue_type: str, severity: str, description: str, count: int | None = None, **details) -> None:
        issue = {"type": issue_type, "severity": severity, "description": description}
        if count is not None:
            issue["count"] = int(count)
        issue.update(details)
        self.issues.append(issue)


def run_validation(data_path: Path, baseline_path: Path) -> Dict:
    baseline_df = pd.read_parquet(baseline_path)
    current_df = pd.read_parquet(data_path)
    # Assignment framing: validate the new/corrupted window starting Jan 16, 2026.
    current_df["time_bucket"] = pd.to_datetime(current_df["time_bucket"])
    current_df = current_df[current_df["time_bucket"] >= pd.Timestamp("2026-01-16")].copy()
    validator = DataQualityValidator(baseline_df=baseline_df)
    return validator.validate(current_df)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Week 3 data quality validation.")
    parser.add_argument(
        "--data",
        default="data/demand_enriched_corrupted.parquet",
        help="Path to current/new data parquet.",
    )
    parser.add_argument(
        "--baseline",
        default="data/demand_enriched_baseline.parquet",
        help="Path to baseline parquet.",
    )
    parser.add_argument(
        "--out",
        default="validation-results.json",
        help="Output JSON report path.",
    )
    args = parser.parse_args()

    result = run_validation(Path(args.data), Path(args.baseline))
    Path(args.out).write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
    return 0 if result["is_valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
