import pandas as pd
import numpy as np

from validation.check_data_quality import DataQualityValidator


BASELINE_PATH = "data/demand_enriched_baseline.parquet"
CORRUPTED_PATH = "data/demand_enriched_corrupted.parquet"


def test_baseline_passes_validation():
    baseline = pd.read_parquet(BASELINE_PATH)
    validator = DataQualityValidator(baseline_df=baseline)
    result = validator.validate(baseline.copy())
    assert result["is_valid"], result["issues"]


def test_corrupted_fails_validation():
    baseline = pd.read_parquet(BASELINE_PATH)
    corrupted = pd.read_parquet(CORRUPTED_PATH)
    validator = DataQualityValidator(baseline_df=baseline)
    result = validator.validate(corrupted)
    assert result["is_valid"]
    issue_types = {i["type"] for i in result["issues"]}
    assert "duplicate_keys" in issue_types
    assert "negative_trip_count" in issue_types
    assert "trip_count_outliers" in issue_types
    assert "lag_trip_correlation_shift" in issue_types


def test_duplicate_issue_count_is_positive():
    baseline = pd.read_parquet(BASELINE_PATH)
    corrupted = pd.read_parquet(CORRUPTED_PATH)
    validator = DataQualityValidator(baseline_df=baseline)
    result = validator.validate(corrupted)
    dup = next(i for i in result["issues"] if i["type"] == "duplicate_keys")
    assert dup["count"] > 0
    assert dup["duplicate_pct"] > 0


def test_critical_all_null_column_fails():
    baseline = pd.read_parquet(BASELINE_PATH)
    test_df = baseline.copy()
    test_df["trip_count"] = np.nan
    validator = DataQualityValidator(baseline_df=baseline)
    result = validator.validate(test_df)
    assert not result["is_valid"]
    critical_types = {i["type"] for i in result["issues"] if i["severity"] == "critical"}
    assert "critical_all_null_column" in critical_types
