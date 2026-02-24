#!/usr/bin/env python3
"""Normalize OHLCV CSV columns for Alpha analysis payload."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime


COLUMN_ALIASES = {
    "date": "date",
    "日期": "date",
    "open": "open",
    "开盘": "open",
    "high": "high",
    "最高": "high",
    "low": "low",
    "最低": "low",
    "close": "close",
    "收盘": "close",
    "volume": "volume",
    "成交量": "volume",
}

REQUIRED = ["date", "open", "high", "low", "close", "volume"]


def _normalize_header(raw_headers: list[str]) -> list[str]:
    return [COLUMN_ALIASES.get(h.strip(), h.strip()) for h in raw_headers]


def _parse_date(value: str) -> str:
    value = (value or "").strip()
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y%m%d"):
        try:
            return datetime.strptime(value, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return value


def _to_float(value: str) -> str:
    value = (value or "").replace(",", "").strip()
    if value == "":
        return ""
    try:
        return str(float(value))
    except ValueError:
        return ""


def normalize_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    out = []
    for row in rows:
        normalized = {
            "date": _parse_date(row.get("date", "")),
            "open": _to_float(row.get("open", "")),
            "high": _to_float(row.get("high", "")),
            "low": _to_float(row.get("low", "")),
            "close": _to_float(row.get("close", "")),
            "volume": _to_float(row.get("volume", "")),
        }
        if not normalized["date"]:
            continue
        out.append(normalized)

    by_date: dict[str, dict[str, str]] = {}
    for row in out:
        by_date[row["date"]] = row
    deduped = list(by_date.values())
    deduped.sort(key=lambda r: r["date"])
    return deduped


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize OHLCV CSV")
    parser.add_argument("--input", required=True, help="Input CSV path")
    parser.add_argument("--output", required=True, help="Output CSV path")
    args = parser.parse_args()

    with open(args.input, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError("CSV has no header")
        headers = _normalize_header(reader.fieldnames)
        rows = []
        for raw in reader:
            mapped = {}
            for src, dst in zip(reader.fieldnames, headers):
                mapped[dst] = raw.get(src, "")
            rows.append(mapped)

    normalized = normalize_rows(rows)
    if len(normalized) < 30:
        raise RuntimeError(f"not enough valid rows after normalization: {len(normalized)}")

    with open(args.output, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=REQUIRED)
        writer.writeheader()
        writer.writerows(normalized)

    print(f"normalized rows: {len(normalized)}")
    print(f"written: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
