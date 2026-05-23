# Week 3 Setup Checklist

## Before Starting

- [ ] Read READING.md (context on data quality)
- [ ] Install dependencies: `pip install great_expectations pandas numpy pytest`
- [ ] Set up Git LFS and pull data:
  ```bash
  git lfs install
  git lfs pull
  ls -lh week3/data/*.parquet  # Verify files are MB, not KB
  ```

## Part 1: Identify Issues

- [ ] Load baseline and corrupted data into Python
- [ ] Explore both datasets - compare:
  - Row counts and date ranges
  - Null rates per column
  - Value ranges (min/max)
  - Data types
  - Unique values for categorical fields
  
- [ ] Document 4+ distinct issues found:
  - [ ] Issue 1: __________ (affected rows: ____)
  - [ ] Issue 2: __________ (affected rows: ____)
  - [ ] Issue 3: __________ (affected rows: ____)
  - [ ] Issue 4: __________ (affected rows: ____)

- [ ] For each issue, note:
  - What is wrong (specific problem)
  - How many rows affected
  - Why it breaks the model/API
  - Root cause hypothesis

## Part 2: Build Validation

- [ ] Create `week3/validation/check_data_quality.py`
  - Write functions to detect each of your 4+ issues
  - Return structured results (which rows/columns failed)
  
- [ ] Test your validation against both datasets:
  - Baseline should pass (or mostly pass)
  - Corrupted should fail on your identified issues

## Part 3: Graceful Degradation

- [ ] Copy `week2/backend/data.py` to `week3/backend/data.py`
- [ ] Add validation calls to data loading
- [ ] Implement fallbacks for each issue type
- [ ] Add logging when degradation happens
- [ ] Test that API still runs with corrupted data

## Part 4: Write Tests

- [ ] Create `week3/validation/test_data_quality.py`
- [ ] Write tests that:
  - [ ] Pass for clean (baseline) data
  - [ ] Fail for corrupted data
  - [ ] Test each issue type individually
  - [ ] Verify graceful degradation

- [ ] Run tests: `python -m pytest week3/validation/test_data_quality.py -v`

## Part 5: Combined Report (3 pages max)

Write single report:
- [ ] Page 1: Issues found (what, how many rows, why it matters)
- [ ] Page 2: Validation approach + graceful degradation (how you fix each issue)
- [ ] Page 3: Strategy (where validation runs, monitoring, trade-offs)

## Deliverables Checklist

- [ ] `week3/validation/check_data_quality.py` - validation code
- [ ] `week3/validation/test_data_quality.py` - tests
- [ ] `week3/backend/data.py` - graceful degradation
- [ ] `REPORT.md` or `REPORT.pdf` (3 pages max):
  - Page 1: Issues identified
  - Page 2: Validation approach + fallbacks
  - Page 3: Strategy & trade-offs
