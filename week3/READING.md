# Week 3: Data Quality, Validation, and Graceful Degradation

## The Silent Failure Problem

A system can run smoothly while producing wrong answers. No crashes, no errors logged, no alarms triggered. The application continues to serve requests with high confidence, but the underlying data changed and nobody noticed.

This is the core problem of data quality in production. Data failures are fundamentally different from code failures. Code fails loudly: a connection breaks, an exception is raised. Data fails silently: the data arrives structurally valid (correct schema, data types present), but the values are wrong. The model produces predictions anyway—confidently, incorrectly.

## How to Think About Finding Data Quality Issues

You have 4 weeks of clean historical data and 2 weeks of potentially corrupted new data. Compare them systematically.

### Define What Valid Data Looks Like

What constraints should valid data satisfy?

- **Shape:** Expected row counts. Duplicate rows.
- **Values:** Valid ranges per column. Which columns can be null?
- **Rates:** For categorical columns, expected percentages. Do they match historical?
- **Relationships:** Which columns should correlate. Should some columns be independent?

Then compare: which constraints are violated in new data?

### Layer 1: Compare Raw Statistics

Summary statistics, unique counts, null rates. How do they differ from historical data?

### Layer 2: Look for Anomalies in Patterns

Temporal patterns (daily/weekly cycles), segment-specific patterns (zone behavior), categorical distributions. Where do they deviate from baseline?

### Layer 3: Verify Features Still Predict

A feature can pass structural checks (in-range, non-null) but stop being predictive. Check: do features maintain their expected relationships with the target in new data? Compare historical relationships to new data relationships. Divergences indicate problems.

---

## Validation Placement: Where and When to Catch Problems

Data in production does not arrive perfectly. It comes from multiple upstream sources. Each source has contracts (expected schema, value ranges, distributions, feature correlations). When any break, downstream predictions become unreliable.

[Data contracts—formal agreements about schema, quality rules, and SLAs between producers and consumers—are emerging as best practice.](https://github.com/datacontract/datacontract-specification) Instead of assuming data meets expectations, teams explicitly document valid data properties and validate against the contract.

Three strategies exist, each catching different failure modes:

**CI/CD pipeline validation**: Before deploying, run comprehensive checks on incoming data. Block deployment if issues found.
- **Catches:** Structural corruption (duplicates, out-of-range), distribution shifts, missing columns
- **Tradeoff:** Slower (validation runs after tests); can't catch issues that only appear after deployment
- **Use when:** New data batches arrive on a schedule and you can afford to delay deployment

**API startup validation**: When the API starts (pod startup), validate that loaded data meets constraints. Log warnings, continue if non-fatal.
- **Catches:** Configuration errors, stale caches, loading failures
- **Tradeoff:** Readiness probes take longer; doesn't catch gradual drift over time
- **Use when:** You need fast feedback that data is loadable before serving requests

**Runtime monitoring**: While serving requests, continuously monitor data quality metrics. Log anomalies, emit alerts.
- **Catches:** Drift that develops over hours/days, subtle correlation shifts, real-time degradation
- **Tradeoff:** Expensive (validation on every request); errors already served before detection
- **Use when:** You need to detect slow degradation or poison pills that appear after deployment

Production systems layer all three. CI catches obvious problems early. Startup validates configuration. Runtime catches drift.

## Great Expectations Framework

Great Expectations is the widely-adopted open-source framework for validating data. It works by defining expectations: explicit rules about what valid data looks like.

Example expectations:
```
expect_column_values_to_be_in_set: is_holiday in {0, 1, 2}
expect_column_values_to_be_between: trip_count between 0 and 10000
expect_column_values_to_not_be_null: pickup_latitude, pickup_longitude
expect_table_columns_to_match_set: [zone_id, time_bucket, trip_count, ...]
expect_column_values_to_match_regex: date column matches YYYY-MM-DD
```

Benefits of Great Expectations:
- Expectations are declarative, not code—easier to understand and audit
- Built-in profiling discovers expectations from data
- Validation produces structured reports (passed/failed expectations, which rows failed)
- Integrates with data quality platforms (Data Contracts, Soda, etc.)

The limitation: Great Expectations is a validation tool, not an enforcement tool. It tells you whether data is bad; it doesn't make the system continue working when data is bad.

## Graceful Degradation: When Data Is Incomplete or Invalid

Validation catches corruption before it reaches production. But bad data can arrive at runtime—new corruption types, pipeline failures, gradual drift. Your API must handle this without crashing.

**Duplicate rows:** Choose deduplication strategy (keep first, keep last). Log what you removed.

**Out-of-range values:** Constrain to valid range or replace with sensible default. Log the action.

**Unexpected categorical rates:** Detect deviations from baseline. Log warning. Decide whether to proceed or fail.

**Feature no longer predicts:** Detect by comparing correlations to baseline. Log or alert. Use fallback feature if available.

**Critical feature missing:** Fail loudly. Return error. Don't guess at missing data.

Rule: decide what to do before bad data arrives. Code fallbacks. Always log what degraded and why. Some failures degrade gracefully (use a fallback). Others fail loud and alert operators. [Graceful degradation](https://martinfowler.com/articles/patterns-of-distributed-systems/graceful-degradation.html) is transparent, not silent.

## API Resilience for Data Quality Issues

When data validation fails at startup, the API has choices:

**Fail fast (CI strategy):** Block deployment. Don't start the API. This is safest but requires manual intervention.

**Start with degraded mode (graceful degradation strategy):** Load data despite warnings. Use fallbacks for corrupted rows. Log severity. This keeps the service running but operators must monitor logs for alerts.

**Health checks with recovery:** Add a readiness probe that re-validates data periodically. If validation fails, mark the pod as not-ready. Kubernetes removes it from service. After data is fixed, the pod becomes ready again and resumes serving.

Example readiness check logic:
```python
# On pod startup: validate data
@app.get("/health/ready")
def readiness():
    if not validate_data():
        return {"status": "not_ready", "reason": "data_quality_failed"}
    return {"status": "ready"}
```

If validation fails, Kubernetes gradually drains requests and replaces the pod. When data is fixed, new pods start successfully.

**Timeout on validation:** If validation takes >30s on startup, return "partially ready" and continue. Validation is important but not worth blocking traffic forever.

The broader principle: [API resilience patterns](https://learn.microsoft.com/en-us/azure/architecture/patterns/resilience-patterns) apply to data failures too. Don't let a single corrupted row bring down the service. Degrade gracefully, stay observable, let operators respond.

## Monitoring Data Quality: What to Measure

Measure what reveals problems before predictions become wrong.

**Structural signals:** Duplicate counts. Out-of-range rates. Null rates per column. Compare to baseline.

**Distribution signals:** Summary statistics per column. Categorical rates. Temporal patterns. Do they match historical baseline?

**Relationship signals:** Feature correlations with target. Do they match historical baseline?

**Segment-specific signals:** Metrics per zone, per time window. A problem hidden in global aggregates might be obvious when segmented.

Specificity matters. "Data changed" is vague. "Demand correlation dropped in 3 zones" is actionable.

## The Subtle Issue: When Data Looks Valid But Is Useless

Some corruptions are obvious (negative trip counts, 100% nulls, duplicates). Others pass structural checks but break predictive relationships.

Example: a feature is "demand from this zone last week." Structurally correct—in-range values, no nulls. But half the zones are receiving values from a different zone. The values look fine, but the feature becomes uncorrelated with the target for those zones.

Basic validation won't catch this. You need to check: do features maintain their expected relationships with the target? Compare historical correlations to new data correlations. Large deviations indicate problems.

## Data Contracts and Observability

[The emerging practice of data contracts formalizes the agreement between upstream producers and downstream consumers.](https://www.datacontract.dev/) A data contract specifies:
- Schema (expected columns, types)
- Quality rules (non-null rates, value ranges, uniqueness)
- SLAs (latency, completeness, accuracy)
- Physical location (where data lives, how to access it)

Contracts are validated in CI. When new data arrives, it's tested against the contract. When a contract is broken, downstream systems are alerted automatically.

This shifts ownership: the producer of data is responsible for meeting the contract. The consumer can rely on contracts being enforced. No more silent failures because nobody validated.

## Implications for Your System

Your prediction API depends on data. When data breaks:

1. **Can you detect it?** (validation + monitoring)
2. **What happens if you don't?** (predictions become wrong; users make bad decisions)
3. **What should you do?** (graceful degradation: serve something useful, log the problem, alert)
4. **How do you prevent it recurring?** (automated tests catch similar issues in future data)

This week, you implement all four: detection (validation framework), response (graceful degradation), prevention (tests).

## References

[Hidden Technical Debt in Machine Learning Systems](https://papers.nips.cc/paper/5656-hidden-technical-debt-in-machine-learning-systems.pdf) (Sculley et al., Google, NeurIPS 2015)
- Foundational work identifying data pipelines as the primary source of technical debt; validation and monitoring are critical

[Fairness and Machine Learning](https://fairmlbook.org/), Chapter on Datasets
- How distribution shifts and data quality failures harm model fairness

[Data Contracts: Formally Specifying Data Semantics and Quality](https://www.datacontract.dev/)
- Emerging standard for formalizing data expectations

[Great Expectations: Professional Data Quality](https://greatexpectations.io/)
- Open-source framework used in production systems for data validation

[API Resilience Patterns](https://learn.microsoft.com/en-us/azure/architecture/patterns/resilience-patterns)
- Circuit breaker, retry, timeout, bulkhead patterns

[Lessons from Production Failures: The Data Quality Edition](https://www.metaflow.org/blog/data-quality-in-production) (Metaflow)
- Case studies of production failures caused by data quality issues

[Machine Learning Operations (MLOps) Maturity Model](https://ml-ops.systems/)
- Data quality is a maturity level; relates to monitoring, governance, and operational readiness
