"""Market-agnostic metric engine: per-asset stats, section picks, regime."""
from __future__ import annotations

import numpy as np
import pandas as pd

WINDOWS_TRADING = {"1d": 1, "1w": 5, "1m": 21, "2m": 42, "50ma": 50, "20ma": 20, "200ma": 200}
WINDOWS_CALENDAR = {"1d": 1, "1w": 7, "1m": 30, "2m": 60, "50ma": 50, "20ma": 20, "200ma": 200}


def _ret(series: pd.Series, n: int) -> float:
    s = series.dropna()
    if len(s) < n + 1:
        return np.nan
    prev = s.iloc[-(n + 1)]
    if prev == 0 or pd.isna(prev):
        return np.nan
    return float(s.iloc[-1] / prev - 1.0)


def trend_label(series: pd.Series, w: dict) -> str:
    s = series.dropna()
    if len(s) < w["50ma"] + 5:
        return "—"
    ma50 = s.rolling(w["50ma"]).mean()
    ma20 = s.rolling(w["20ma"]).mean()
    above = s.iloc[-1] > ma50.iloc[-1]
    slope_up = ma20.iloc[-1] > ma20.iloc[-6]
    if above and slope_up:
        return "uptrend"
    if above:
        return "cooling"
    if slope_up:
        return "bounce"
    return "downtrend"


def compute_asset_rows(prices: pd.DataFrame, benchmark: str, calendar_days: bool,
                       meta: dict | None = None) -> pd.DataFrame:
    w = WINDOWS_CALENDAR if calendar_days else WINDOWS_TRADING
    meta = meta or {}
    rows = []
    bench = prices[benchmark] if benchmark in prices.columns else None
    bench_r1m = _ret(bench, w["1m"]) if bench is not None else np.nan

    for sym in prices.columns:
        s = prices[sym].dropna()
        if len(s) < 10:
            continue
        m = meta.get(sym, {})
        r = {
            "symbol": sym,
            "name": m.get("name", sym),
            "group": m.get("group", ""),
            "sector": m.get("sector", ""),
            "rank": m.get("rank", 10**6),
            "r_1d": _ret(s, w["1d"]),
            "r_1w": _ret(s, w["1w"]),
            "r_1m": _ret(s, w["1m"]),
            "r_2m": _ret(s, w["2m"]),
            "trend": trend_label(s, w),
        }
        ma50 = s.rolling(w["50ma"]).mean()
        r["dist_50ma"] = float(s.iloc[-1] / ma50.iloc[-1] - 1.0) if len(s) >= w["50ma"] else np.nan
        if sym == benchmark:
            r["vs_bench_1m"] = np.nan
        else:
            r["vs_bench_1m"] = (r["r_1m"] - bench_r1m) if not pd.isna(bench_r1m) else np.nan
        if not pd.isna(r["r_1w"]) and not pd.isna(r["r_1m"]):
            r["accel"] = r["r_1w"] - r["r_1m"] * (w["1w"] / w["1m"])
        else:
            r["accel"] = np.nan
        daily = s.pct_change().dropna().tail(60)
        sd = float(daily.std()) if len(daily) >= 20 else np.nan
        ok = sd and not pd.isna(sd) and sd > 0 and not pd.isna(r["r_1d"])
        r["vol_1d_sigma"] = (r["r_1d"] / sd) if ok else np.nan
        rows.append(r)

    df = pd.DataFrame(rows)
    if df.empty:
        return df
    parts = [df[c].rank(pct=True) for c in ("r_1m", "r_2m", "dist_50ma", "vs_bench_1m")]
    df["strength"] = pd.concat(parts, axis=1).mean(axis=1)
    df["strength_pct"] = (df["strength"].rank(pct=True) * 100).round(0)
    return df.sort_values("rank").reset_index(drop=True)


def spark_series(prices: pd.DataFrame, symbol: str, days: int = 30) -> list:
    """Cumulative 30d return path minus the average tracked asset."""
    px = prices.tail(days + 1)
    rets = px.pct_change().iloc[1:]
    if symbol not in rets.columns or rets[symbol].dropna().empty:
        return []
    market = rets.mean(axis=1)
    diff = (rets[symbol].fillna(0) - market.fillna(0)).cumsum()
    return [round(float(x), 4) for x in diff.tolist()]


def pick_sections(df: pd.DataFrame, top_rank_cutoff: int | None = 30) -> dict:
    """top_rank_cutoff gates which names may *headline* a panel. Pass None when
    `rank` is not a meaningful importance ordering (e.g. config file order) —
    otherwise the panels can only ever surface names near the top of the file."""
    d = df.dropna(subset=["r_1m"]).copy()

    def split(sub, n_head):
        if top_rank_cutoff is None:
            return sub.head(n_head), []
        head = sub[sub["rank"] <= top_rank_cutoff].head(n_head)
        beyond = sub[sub["rank"] > top_rank_cutoff].head(10)["symbol"].tolist()
        return head, beyond

    strongest = d.sort_values("strength_pct", ascending=False)
    s_head, s_beyond = split(strongest[strongest["strength_pct"] >= 60], 6)
    accel = d[(d["accel"] > 0.01) & (d["r_1w"] > 0)].sort_values("accel", ascending=False)
    a_head, a_beyond = split(accel, 4)
    washed = d[d["r_2m"] < -0.15].sort_values("r_2m")
    w_head, w_beyond = split(washed, 5)
    big = d[d["vol_1d_sigma"].abs() > 2].copy()
    big["absmove"] = big["r_1d"].abs()
    big = big.sort_values("absmove", ascending=False)
    b_head, b_beyond = split(big, 4)
    return {"strongest": (s_head, s_beyond), "accel": (a_head, a_beyond),
            "washed": (w_head, w_beyond), "big": (b_head, b_beyond)}


def regime(prices: pd.DataFrame, benchmark: str, bench_label: str, calendar_days: bool) -> dict:
    w = WINDOWS_CALENDAR if calendar_days else WINDOWS_TRADING
    s = prices[benchmark].dropna() if benchmark in prices.columns else pd.Series(dtype=float)
    if len(s) < w["200ma"]:
        n = max(int(len(s) * 0.8), 20)
        note = f"average price of the past {n} days (limited history so far)"
    else:
        n = w["200ma"]
        note = "average price of the past 200 days"
    if len(s) < n:
        return {"state": "unknown", "text": f"Not enough history yet to judge the {bench_label} regime."}
    ma = s.rolling(n).mean().iloc[-1]
    if s.iloc[-1] > ma:
        return {"state": "up", "text": f"{bench_label} is in an uptrend — trading above its {note}. "
                                       "Strength readings have a stronger record in this state."}
    return {"state": "down", "text": f"{bench_label} is in a downtrend — trading below its {note}. "
                                     "Strength readings have a much weaker record in this state."}


def market_summary(df: pd.DataFrame) -> list:
    bits = []
    if df.empty:
        return bits
    up = int((df["r_1w"] > 0).sum())
    total = int(df["r_1w"].notna().sum())
    share = up / max(total, 1)
    tone = "broadly up" if share > 0.65 else "mixed" if share > 0.35 else "broadly down"
    bits.append(f"The market is {tone} — {up} of {total} assets are up over the past week.")
    avg = df["r_1m"].mean()
    if not pd.isna(avg):
        bits.append(f"The average tracked asset is {'up' if avg >= 0 else 'down'} "
                    f"{abs(avg)*100:.1f}% over the past month.")
    big_n = int((df["vol_1d_sigma"].abs() > 2).sum())
    if big_n:
        bits.append(f"{big_n} asset{'s' if big_n != 1 else ''} just made an unusually large one-day move "
                    "— outsized moves in large names have tended to keep drifting the same way.")
    return bits
