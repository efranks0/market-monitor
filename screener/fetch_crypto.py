"""Crypto: CoinGecko for universe + daily prices, Coinalyze (optional free
key) for funding and open interest. Cached under data/cache."""
from __future__ import annotations

import os
import time
from pathlib import Path

import pandas as pd
import requests

CACHE = Path("data/cache")
CG = "https://api.coingecko.com/api/v3"
CA = "https://api.coinalyze.net/v1"

STABLE_OR_WRAPPED = {
    "USDT", "USDC", "DAI", "USDS", "USDE", "FDUSD", "TUSD", "PYUSD", "USD1", "USDD",
    "WBTC", "WETH", "STETH", "WSTETH", "WEETH", "CBBTC", "WBETH", "RETH", "METH",
    "SOLVBTC", "LBTC", "BUIDL", "USDT0", "SUSDS", "SUSDE", "BSC-USD", "JITOSOL", "MSOL",
    "CBETH", "EZETH", "RSETH", "XAUT", "PAXG", "GUSD", "USDP", "EURC", "BNSOL",
}


def _cg_headers():
    key = os.environ.get("COINGECKO_API_KEY", "").strip()
    return {"x-cg-demo-api-key": key} if key else {}


def _throttle():
    return 2.2 if os.environ.get("COINGECKO_API_KEY") else 7.0


def _get(url, params=None, headers=None, tries=3):
    for i in range(tries):
        try:
            r = requests.get(url, params=params, headers=headers, timeout=30)
            if r.status_code == 429:
                time.sleep(20 * (i + 1))
                continue
            r.raise_for_status()
            return r.json()
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(5 * (i + 1))


def universe(n=100):
    """Top-n real coins by market cap (stables and wrapped assets removed)."""
    coins, page = [], 1
    while len(coins) < n and page <= 3:
        batch = _get(f"{CG}/coins/markets", params={
            "vs_currency": "usd", "order": "market_cap_desc",
            "per_page": 100, "page": page, "sparkline": "false",
        }, headers=_cg_headers())
        time.sleep(_throttle())
        for c in batch:
            sym = (c.get("symbol") or "").upper()
            if sym in STABLE_OR_WRAPPED or not c.get("market_cap"):
                continue
            coins.append({"id": c["id"], "symbol": sym, "name": c["name"],
                          "rank": c.get("market_cap_rank") or 9999})
        page += 1
    return coins[:n]


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


def prices(coins):
    """Daily close matrix. First run pulls ~100 days/coin; later runs top up."""
    cache = _load_cache("crypto_prices.csv")
    out = {}
    for c in coins:
        sym = c["symbol"]
        have = cache[sym].dropna() if sym in cache.columns else pd.Series(dtype=float)
        days = 100 if len(have) < 70 else 5
        try:
            data = _get(f"{CG}/coins/{c['id']}/market_chart",
                        params={"vs_currency": "usd", "days": days, "interval": "daily"},
                        headers=_cg_headers())
            time.sleep(_throttle())
            s = pd.Series({pd.to_datetime(t, unit="ms").normalize(): p
                           for t, p in data.get("prices", [])})
            s = s[~s.index.duplicated(keep="last")]
            out[sym] = s.combine_first(have) if not have.empty else s
        except Exception as e:
            print(f"  ! {sym}: price fetch failed ({e}); using cache")
            if not have.empty:
                out[sym] = have
    df = pd.DataFrame(out).sort_index()
    _save_cache(df, "crypto_prices.csv")
    return df


def derivatives(symbols):
    """Per symbol: funding_apr (%/yr), oi_chg_1d, oi_chg_1w. Best effort."""
    key = os.environ.get("COINALYZE_API_KEY", "").strip()
    if not key:
        print("  (no COINALYZE_API_KEY - funding/OI panels will be blank)")
        return {}
    headers = {"api_key": key}
    result = {}
    ca_syms = [(s, f"{s}USDT_PERP.A") for s in symbols]
    batches = [ca_syms[i:i + 10] for i in range(0, len(ca_syms), 10)]
    now = int(time.time())
    frm = now - 12 * 86400
    for batch in batches:
        joined = ",".join(v for _, v in batch)
        try:
            fr = _get(f"{CA}/funding-rate", params={"symbols": joined}, headers=headers)
            time.sleep(1.6)
            oi = _get(f"{CA}/open-interest-history",
                      params={"symbols": joined, "interval": "daily",
                              "from": frm, "to": now, "convert_to_usd": "true"},
                      headers=headers)
            time.sleep(1.6)
        except Exception as e:
            print(f"  ! coinalyze batch failed ({e})")
            continue
        fr_map = {d["symbol"]: d.get("value") for d in (fr or [])}
        oi_map = {d["symbol"]: d.get("history", []) for d in (oi or [])}
        for sym, ca in batch:
            rec = {}
            v = fr_map.get(ca)
            if v is not None:
                rec["funding_apr"] = float(v) * 3 * 365 * 100
            hist = oi_map.get(ca) or []
            closes = [h.get("c") for h in hist if h.get("c")]
            if len(closes) >= 2 and closes[-2]:
                rec["oi_chg_1d"] = closes[-1] / closes[-2] - 1
            if len(closes) >= 8 and closes[-8]:
                rec["oi_chg_1w"] = closes[-1] / closes[-8] - 1
            if rec:
                result[sym] = rec
    return result
