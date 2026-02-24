# Source Fallbacks (Online Fetch)

Use this order for each symbol:

1. Eastmoney / Akshare public endpoints (preferred)
- Reason: stable A-share coverage and daily bars.

2. Sina Finance historical endpoints
- Reason: good backup for daily K data.

3. Tencent quote/history endpoints
- Reason: useful fallback when above sources fail.

4. Other reputable financial pages with machine-readable tables
- Example: exchange pages or major portal historical data tables.

## Query Guidance

For each symbol, use at least one query pattern:
- `<symbol> A股 日线 OHLCV 历史`
- `<symbol> Eastmoney 历史行情`
- `<symbol> 新浪 财经 K线`

## Completeness Checks

A valid symbol dataset must satisfy:
- Has columns equivalent to `date, open, high, low, close, volume`.
- Has at least 30 daily rows (target 60).
- Date sequence is parseable.

If checks fail, switch source immediately.

## Audit Requirement

Track for each symbol:
- `source_used`
- `rows_kept`
- `window_end_date`
- `fallback_count`
