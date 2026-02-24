---
name: akshare-online-alpha
description: Run Wyckoff master-style analysis from stock codes, CSV data, and optional chart images. Use when users want online multi-source data fetching with source switching, strict Beijing-time trading-session checks, fixed system prompt analysis, and a two-step analyze-then-plot workflow.
---

# Akshare Online Alpha

Use this skill for a strict sequence:

1. User provides stock codes and/or CSV and optional chart image.
2. Agent fetches market data online with source fallback and normalizes OHLCV.
3. Agent applies fixed Wyckoff system prompt from `rules/alpha-system-prompt.md`.
4. Agent outputs analysis first, then plotting code/results.

## Required Execution Order

1. Validate input modes in order:
- CSV (if provided): main source for historical structure.
- Text instructions: constraints and goals.
- Image (if provided): supplemental intraday/micro-structure signal.

2. Resolve current Beijing time before any trading suggestion:
- Fetch actual current time from tool/system.
- Convert to `Asia/Shanghai`.
- Print `当前北京时间：YYYY-MM-DD HH:MM（UTC+8）`.
- Determine if in A-share continuous auction window.

3. Enforce trading-session rules:
- If not in tradable session, only provide post-market review/next-day plan/order strategy.
- Do not output immediate intraday execution commands.

4. Fetch data with online source switching:
- Use `rules/source-fallbacks.md` order.
- For each symbol, keep source audit log.
- If source fails or columns incomplete, switch source.

5. Perform Wyckoff analysis first:
- Analyze latest 500 days structure with MA50/MA200.
- Identify phases/events without forcing full phase set.
- Allow event-date news checks only for verification, not as decision basis.

6. Plot only when allowed:
- If current time is intraday trading time, skip plotting.
- Otherwise generate plotting code/result using hard rendering constraints from system prompt.

## Hard Constraints

- Do not change the fixed prompt wording unless explicitly requested.
- Do not fabricate missing OHLCV rows.
- Do not ignore image input if image is parseable.
- Do not use opaque white text boxes in chart annotations.

## Resources

- `rules/alpha-system-prompt.md`: fixed role and hard rules.
- `rules/source-fallbacks.md`: online source switching policy.
