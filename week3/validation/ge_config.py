"""
Great Expectations configuration template.

This is a skeleton. Fill in the expectations based on issues you identified in Part 1.
"""

import pandas as pd
from great_expectations.dataset import PandasDataset


def validate_data(data_path: str, baseline_path: str = None) -> dict:
    """
    Validate data against expectations.

    TODO: Define expectations based on the 4+ quality issues you found.
    """
    df = pd.read_parquet(data_path)
    ge_df = PandasDataset(df)

    results = {}

    # TODO: Add expectations here
    # Example structure:
    # try:
    #     ge_df.expect_column_to_exist('column_name')
    #     results['check_name'] = 'PASS'
    # except Exception as e:
    #     results['check_name'] = f'FAIL: {e}'

    return results


if __name__ == "__main__":
    baseline = "week3/data/demand_enriched_baseline.parquet"
    corrupted = "week3/data/demand_enriched_corrupted.parquet"

    # TODO: Run validation on both files
    # Print results
