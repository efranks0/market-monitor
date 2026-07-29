"""Stocks & commodities: yfinance daily closes (cached) + CFTC COT."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import requests

CACHE = Path("data/cache")
COT_API = "https://publicreporting.cftc.gov/resource/6dca-aqww.json"


def read_config(path):
    """Lines: SYMBOL | Name | Group | COT-code-or-Sector  (# = comment).

    The 4th field is the CFTC COT code for commodities; it is unused for stocks,
    so it doubles as a GICS sector tag there. Both names are returned."""
    items = []
    for line in Path(path).read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split("|")]
        items.append({"symbol": parts[0],
                      "name": parts[1] if len(parts) > 1 else parts[0],
                      "group": parts[2] if len(parts) > 2 else "",
                      "cot": parts[3] if len(parts) > 3 else "",
                      "sector": parts[3] if len(parts) > 3 else ""})
    return items


def _load_cache(name):
    f = CACHE / name
    if f.exists():
        df = pd.read_csv(f, index_col=0, parse_dates=True)
        df.index = pd.to_datetime(df.index).tz_localize(None)
        return df
    return pd.DataFrame()


def _save_cache(df, name):
    CACHE.mkdir(parents=True, exist_ok=True)
    df.sort_index().tail(400).to_csv(CACHE / name)


def prices_yf(symbols, cache_name):
    import yfinance as yf
    cache = _load_cache(cache_name)
    period = "1y" if cache.empty or len(cache) < 150 else "1mo"
    try:
        raw = yf.download(symbols, period=period, interval="1d",
                          auto_adjust=True, progress=False, threads=True)
        close = raw["Close"] if isinstance(raw.columns, pd.MultiIndex) else raw[["Close"]]
        if not isinstance(close, pd.DataFrame):
            close = close.to_frame(symbols[0])
        close.index = pd.to_datetime(close.index).tz_localize(None)
    except Exception as e:
        print(f"  ! yfinance batch failed ({e}); using cache only")
        close = pd.DataFrame()
    merged = close.combine_first(cache) if not cache.empty else close
    merged = merged.dropna(how="all")
    _save_cache(merged, cache_name)
    return merged


def cot_positioning(items):
    """Speculator net positioning percentile over ~3y of weekly reports."""
    out = {}
    for it in items:
        sym, code = it["symbol"], it.get("cot", "")
        if not code:
            continue
        try:
            r = requests.get(COT_API, params={
                "cftc_contract_market_code": code,
                "$select": "report_date_as_yyyy_mm_dd,noncomm_positions_long_all,"
                           "noncomm_positions_short_all,open_interest_all",
                "$order": "report_date_as_yyyy_mm_dd DESC",
                "$limit": 160,
            }, timeout=30)
            r.raise_for_status()
            rows = r.json()
            if len(rows) < 30:
                continue
            df = pd.DataFrame(rows)
            cols = ("noncomm_positions_long_all", "noncomm_positions_short_all", "open_interest_all")
            for c in cols:
                df[c] = pd.to_numeric(df[c], errors="coerce")
            df["net_pct_oi"] = (df[cols[0]] - df[cols[1]]) / df[cols[2]]
            df = df.dropna(subset=["net_pct_oi"]).iloc[::-1]
            latest = df["net_pct_oi"].iloc[-1]
            pctile = float((df["net_pct_oi"] <= latest).mean() * 100)
            out[sym] = {"cot_pctile": round(pctile),
                        "cot_net_pct_oi": round(float(latest) * 100, 1),
                        "cot_date": str(df["report_date_as_yyyy_mm_dd"].iloc[-1])[:10]}
        except Exception as e:
            print(f"  ! COT {sym} failed ({e})")
    return out
