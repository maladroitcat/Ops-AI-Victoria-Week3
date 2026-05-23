# Week 3 — Data Quality Validation in CI/CD Pipeline

## Before You Start

1. Read [READING.md](READING.md) - data quality failures, validation strategies, graceful degradation
2. Have Week 2 deployed and running
3. Install: `pip install pandas numpy pytest`

## Assignment

Add automated data quality validation to your Week 2 deployed API. New upstream data has issues.

**Your tasks:**
1. Identify data quality issues in the corrupted dataset
2. Write validation checks to detect them
3. Add validation workflow to GitHub Actions (runs on schedule)
4. **YOU DECIDE:** How often to validate? (15min? 1hr? 1day? At startup?)
5. Make the API gracefully degrade on bad data (log issues, don't crash)

**Deliverables:**
- `.github/workflows/validate-data.yml` - new validation workflow
- `validation/check_data_quality.py` - validation functions
- Updated `data.py` - graceful degradation
- Tests - verify validation works
- **Report (1 page max):**
  - Issues found + impact
  - Validation schedule choice + justification
  - Graceful degradation strategy

---

## What You Have

```
week3/
├── .github/workflows/
│   └── validate-data.yml     (TEMPLATE: Fill in TODOs - decide frequency, implement validation)
├── backend/                  ← Copy from week2, you modify data.py
│   ├── main.py
│   ├── data.py               (MODIFY: add validation + fallbacks)
│   └── requirements.txt
├── data/
│   ├── demand_enriched_baseline.parquet   (Jan 1-15, clean)
│   └── demand_enriched_corrupted.parquet  (Jan 16-Feb 1, dirty)
├── validation/
│   ├── ge_config.py          (Great Expectations starter)
│   ├── check_data_quality_template.py    (TEMPLATE: Implement 4+ validation checks)
│   └── test_data_quality_template.py     (TEMPLATE: Write tests)
└── README.md (this file)
```

**All files are provided. All work happens in week3/.**

### GitHub Actions Workflow

You have a template `.github/workflows/validate-data.yml`. Fill in the TODOs:
1. Choose validation frequency (15min? 1hr? daily?)
2. Implement validation logic in the workflow step
3. Report validation results (fail if issues found)

---

## Setup: Install Git LFS

The parquet files are stored with Git LFS. After cloning:

```bash
# Install Git LFS
brew install git-lfs  # macOS
apt-get install git-lfs  # Linux

# One-time setup (first time only)
git lfs install

# Pull actual files from LFS
git lfs pull

# Verify files are downloaded (should show MB, not KB)
ls -lh week3/data/*.parquet
```

If files show `version https://git-lfs.github.com/3` or `oid sha256:...`, LFS didn't pull. Run `git lfs pull` again.

**Troubleshooting:**
- `git lfs pull` takes a minute or two (74MB of data)
- Requires internet connection
- If still having issues, run: `git lfs install --force` then `git lfs pull`

---

## Part 1: Set Up CI/CD Workflow

Edit `.github/workflows/validate-data.yml`:
1. Choose your validation frequency in the `schedule` cron expression
   - `0 * * * *` = Every hour
   - `0 0 * * *` = Daily at midnight
   - `*/15 * * * *` = Every 15 minutes
2. Update the `run` step to call your validation code
3. Fill in other TODOs in the workflow

Then move to Part 2.

## Part 2: Identify Data Quality Issues

Load both parquet files and find 4+ issues that would break the model.

### Load Data

```python
import pandas as pd

baseline = pd.read_parquet('week3/data/demand_enriched_baseline.parquet')
corrupted = pd.read_parquet('week3/data/demand_enriched_corrupted.parquet')

print(f"Baseline: {len(baseline)} rows")
print(f"Corrupted: {len(corrupted)} rows")
print(f"\nBaseline columns: {baseline.columns.tolist()}")
print(f"\nBaseline null rates:\n{baseline.isna().mean()}")
print(f"\nCorrupted null rates:\n{corrupted.isna().mean()}")
```

### What to Look For

Compare baseline to corrupted data:

- **Missing values**: Increase in nulls in any column?
- **Outliers**: Values outside expected ranges? (e.g., trip_count > 10x normal)
- **Duplicates**: Rows repeated multiple times?
- **Distribution shifts**: Mean/std significantly different?
- **Schema changes**: New/missing columns?
- **Type issues**: Integer columns with floats? Strings instead of numbers?

### Document Each Issue

For each issue, note:
- **What**: Type of problem (nulls, outliers, duplicates, etc.)
- **Where**: Which zones/dates/times affected? How many rows?
- **Impact**: How does this break predictions? What's the output quality cost?
- **Root cause**: Why did this happen?

---

## Part 2: Write Validation Code

Create `validation/check_data_quality.py` with functions to detect each issue:

```python
def validate_data(df: pd.DataFrame, baseline_df: pd.DataFrame) -> dict:
    """Check data quality. Return {is_valid: bool, issues: list}"""
    issues = []
    # TODO: Check for each of your 4+ issues
    return {
        'is_valid': len(issues) == 0,
        'issues': issues
    }
```

This code will be called by your CI/CD workflow.

---

## Part 3: Add Validation Workflow

Create `.github/workflows/validate-data.yml` to run validation on schedule.

**YOU DECIDE:** How often should this run?

**Options:**
- **Every 15 minutes:** Catch issues immediately (higher cost, faster detection)
- **Every 30 minutes:** Balance between cost and responsiveness
- **Every 1 hour:** Good for daily operations
- **Every 1 day:** Cost-effective, checks overnight
- **At startup:** Only when pod starts (no ongoing monitoring)
- **Hybrid:** Startup + hourly checks

**Workflow pattern:**
```yaml
name: Data Quality Check

on:
  schedule:
    - cron: '0 * * * *'  # Every hour (YOU CHOOSE)
  push:
    branches: [main]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - run: python -m validation.check_data_quality week3/data/
      - if: failure()
        run: |
          echo "Data validation failed - blocking deployment"
          # Alert ops, don't deploy
```

**Justification in report:** Why did you choose that frequency?

---

## Part 4: Implement Graceful Degradation

Modify `week3/backend/data.py`:

```python
def load_and_validate_data(path: str, baseline_data: pd.DataFrame):
    """Load data, validate, gracefully degrade if issues found."""
    try:
        df = pd.read_parquet(path)
        result = validate_data(df, baseline_data)
        if not result['is_valid']:
            logger.warning(f"Data issues detected: {result['issues']}")
            # Fallback: drop bad rows, use median for nulls, etc.
            df = apply_graceful_degradation(df, result['issues'])
        return df
    except Exception as e:
        logger.error(f"Data loading failed: {e}")
        # Use cached data or synthetic baseline
        return get_last_valid_data()
```

**Key:** API must continue running. Log what degraded so operators know.

## Part 5: Write Tests

Create `validation/test_data_quality.py`:
- Baseline data should pass validation
- Corrupted data should fail (detect 4+ issues)
- Test each issue separately
- Test that API doesn't crash with bad data

## Part 6: Report (1 page MAX)

**Summary of Issues & Strategy**
- List 4+ issues found in corrupted data (what, how many rows, impact)
- Your validation schedule choice (15min/hourly/daily?) + brief justification (cost vs detection speed)
- How API gracefully degrades on bad data (drop rows? fill nulls? fallback to baseline?)

---

## Common Mistakes

**Validation too strict:** Rejects valid edge cases. Balance sensitivity/specificity.

**Graceful degradation silent:** API returns wrong answers without logging. Always log what degraded.

**No segmentation:** Check null rates globally. Should check per-zone, per-hour, etc.

**Tests don't match issues:** Test files exist but don't actually check for the issues you identified.

---

## Grading

| Criterion | Weight |
|-----------|--------|
| Issues identified and documented | 30% |
| Validation code works correctly | 25% |
| Graceful degradation (API handles bad data) | 20% |
| Tests verify validation works | 15% |
| Report (clear, 1 page max) | 10% |

---

## Due

End of Week 3 (see syllabus)
