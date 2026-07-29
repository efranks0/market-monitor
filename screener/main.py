"""Build the dashboard: fetch -> compute -> render -> docs/index.html.
Run `python -m screener.main` (or with --demo for synthetic data)."""
from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from . import metrics as M
from . import render as R
from .fetch_markets import read_config, prices_yf, cot_positioning


def _labels_common(df, bench_name, thresh=0.02):
    def lab(v):
        if pd.isna(v):
            return "—"
        if v > thresh:
            return f'<span class="pos">ahead of {bench_name}</span>'
        if v < -thresh:
            return f'<span class="neg">behind {bench_name}</span>'
        return f"tracks {bench_name}"
    df["vs_bench_label"] = df["vs_bench_1m"].map(lab)


def _crowding_panel(rows):
    if not rows:
        return ""
    out = []
    for r in rows:
        out.append('<div class="mini"><span class="sym">' + r["symbol"] + '</span>'
                   + R.spark_svg(r.get("spark", []))
                   + '<span class="desc">' + r["desc"] + '</span></div>')
    return "".join(out)


# ------------------------------ CRYPTO ------------------------------

def build_crypto(demo=False):
    if demo:
        px, meta, deriv = _demo_prices("crypto")
    else:
        from .fetch_crypto import universe, prices, derivatives
        coins = universe(100)
        meta = {c["symbol"]: {"name": c["name"], "rank": c["rank"]} for c in coins}
        print(f"crypto: {len(coins)} coins in universe, fetching prices...")
        px = prices(coins)
        print("crypto: fetching funding / open interest...")
        deriv = derivatives(list(px.columns))

    df = M.compute_asset_rows(px, "BTC", calendar_days=True, meta=meta)
    _labels_common(df, "BTC", 0.03)

    holds, notes, crowd = [], [], []
    raw = {"funding_apr": [], "oi_chg_1d": [], "oi_chg_1w": []}
    for _, r in df.iterrows():
        d = deriv.get(r["symbol"], {})
        apr, oi1d, oi1w = d.get("funding_apr"), d.get("oi_chg_1d"), d.get("oi_chg_1w")
        for k, v in (("funding_apr", apr), ("oi_chg_1d", oi1d), ("oi_chg_1w", oi1w)):
            raw[k].append(np.nan if v is None else float(v))
        if apr is None:
            holds.append("—")
        elif apr < -3:
            holds.append('<span class="pos">paid to hold</span>')
        elif apr > 25:
            holds.append(f'<span class="neg">~{apr:.0f}%/yr</span>')
        else:
            holds.append("normal")
        tag = "—"
        if oi1d is not None and oi1d < -0.12:
            tag = '<span class="tag warn">flushed</span>'
        elif oi1w is not None and oi1w > 0.25 and not pd.isna(r["r_1w"]) and r["r_1w"] > 0:
            tag = '<span class="tag warn">longs piling in</span>'
        elif apr is not None and apr < -15:
            tag = '<span class="tag">shorts crowded</span>'
        notes.append(tag)
        if (apr is not None and oi1w is not None and apr > 20 and oi1w > 0.08
                and not pd.isna(r["r_1w"]) and r["r_1w"] > 0 and r["rank"] <= 30):
            crowd.append({"symbol": r["symbol"],
                          "desc": f'funding <b>~{apr:.0f}%/yr</b> · positions +{oi1w*100:.0f}% this week'})
    df["hold_label"], df["note_html"] = holds, notes
    for k, v in raw.items():
        df[k] = v

    return _assemble("crypto", "Crypto", df, px, "BTC", "Bitcoin", True,
                     crowding_title="Crowded longs",
                     crowding_blurb="Where long positioning is stacked up — expensive funding this past week, or leverage piling in as price climbs. Says nothing about strength.",
                     crowding_rows=crowd, vs_bench_header="vs bitcoin · 1m",
                     hold_header="cost to hold · 1w")


# ------------------------------ STOCKS ------------------------------

def build_stocks(demo=False):
    items = read_config("config/stocks.txt")
    syms = [i["symbol"] for i in items]
    if demo:
        px, _, _ = _demo_prices("stocks", syms)
    else:
        px = prices_yf(syms, "stock_prices.csv")
    meta = {i["symbol"]: {"name": f'{i["name"]} · {i["group"]}', "rank": k + 1,
                          "group": i["group"], "sector": i.get("sector", "")}
            for k, i in enumerate(items)}

    df = M.compute_asset_rows(px, "SPY", calendar_days=False, meta=meta)
    df = df[df["symbol"] != "SPY"].reset_index(drop=True)
    df["rank"] = range(1, len(df) + 1)
    _labels_common(df, "SPX", 0.02)

    holds, notes, rng_pos = [], [], []
    for _, r in df.iterrows():
        s = px[r["symbol"]].dropna().tail(252)
        rng = (s.max() - s.min()) or 1e-9
        pos = (s.iloc[-1] - s.min()) / rng
        rng_pos.append(float(pos))
        if pos > 0.95:
            holds.append("near 52w high")
        elif pos < 0.08:
            holds.append("near 52w low")
        else:
            holds.append(f"{pos*100:.0f}% of 52w range")
        tag = "—"
        if pos >= 0.99:
            tag = '<span class="tag">new 52w high</span>'
        elif pos <= 0.01:
            tag = '<span class="tag warn">new 52w low</span>'
        elif not pd.isna(r["vol_1d_sigma"]) and abs(r["vol_1d_sigma"]) > 3:
            tag = f'<span class="tag warn">{abs(r["vol_1d_sigma"]):.0f}σ move</span>'
        notes.append(tag)
    df["hold_label"], df["note_html"] = holds, notes
    df["pct_52w_range"] = rng_pos

    crowd = []
    d = df.dropna(subset=["dist_50ma"]).copy()
    if not d.empty:
        z = (d["dist_50ma"] - d["dist_50ma"].mean()) / (d["dist_50ma"].std() or 1e-9)
        for _, r in d[z > 1.8].sort_values("dist_50ma", ascending=False).head(4).iterrows():
            crowd.append({"symbol": r["symbol"],
                          "desc": f'<b>{r["dist_50ma"]*100:+.0f}%</b> above its 50-day average — extended by its own standards'})

    return _assemble("stocks", "Stocks", df, px, "SPY", "The S&P 500", False,
                     crowding_title="Stretched",
                     crowding_blurb="Trading unusually far above their own 50-day average — extension, not a verdict on strength.",
                     crowding_rows=crowd, vs_bench_header="vs S&P 500 · 1m",
                     hold_header="52-week range", panel_rank_gate=None)


# ---------------------------- COMMODITIES ----------------------------

def build_commodities(demo=False):
    items = read_config("config/commodities.txt")
    syms = [i["symbol"] for i in items]
    if demo:
        px, _, _ = _demo_prices("commodities", syms)
        cot = {}
    else:
        px = prices_yf(syms, "commodity_prices.csv")
        print("commodities: fetching CFTC positioning...")
        cot = cot_positioning(items)
    meta = {i["symbol"]: {"name": f'{i["name"]} · {i["group"]}', "rank": k + 1,
                          "group": i["group"]}
            for k, i in enumerate(items)}

    basket = (px.pct_change().mean(axis=1).fillna(0) + 1).cumprod() * 100
    px2 = px.copy()
    px2["BASKET"] = basket
    df = M.compute_asset_rows(px2, "BASKET", calendar_days=False, meta=meta)
    df = df[df["symbol"] != "BASKET"].reset_index(drop=True)
    _labels_common(df, "the basket", 0.02)

    holds, notes, crowd = [], [], []
    raw = {"cot_pctile": [], "cot_net_pct_oi": [], "cot_date": []}
    for _, r in df.iterrows():
        c = cot.get(r["symbol"])
        for k in ("cot_pctile", "cot_net_pct_oi"):
            raw[k].append(np.nan if not c else float(c[k]))
        raw["cot_date"].append("" if not c else c.get("cot_date", ""))
        if not c:
            holds.append("—")
            notes.append("—")
            continue
        p = c["cot_pctile"]
        side = "long" if c["cot_net_pct_oi"] >= 0 else "short"
        holds.append(f"{p:.0f}th pctile {side}")
        if p >= 90:
            notes.append('<span class="tag warn">specs crowded long</span>')
            crowd.append({"symbol": r["symbol"],
                          "desc": f'speculators net long at the <b>{p:.0f}th percentile</b> of the past 3 years'})
        elif p <= 10:
            notes.append('<span class="tag">specs crowded short</span>')
            crowd.append({"symbol": r["symbol"],
                          "desc": f'speculators net short at the <b>{p:.0f}th percentile</b> — stretched the other way'})
        else:
            notes.append("—")
    df["hold_label"], df["note_html"] = holds, notes
    for k, v in raw.items():
        df[k] = v

    return _assemble("commodities", "Commodities", df, px2, "BASKET",
                     "The commodity basket", False,
                     crowding_title="Crowded positioning",
                     crowding_blurb="Speculator net positioning at 3-year extremes (weekly CFTC data). Crowded trades unwind hard.",
                     crowding_rows=crowd, vs_bench_header="vs basket · 1m",
                     hold_header="spec positioning", top_cutoff=27,
                     panel_rank_gate=None)


# ------------------------------ shared ------------------------------

def _assemble(key, label, df, px, bench_sym, bench_label, calendar_days,
              crowding_title, crowding_blurb, crowding_rows,
              vs_bench_header, hold_header, top_cutoff=30,
              panel_rank_gate="use_cutoff"):
    spark_px = px.drop(columns=["BASKET"]) if "BASKET" in px.columns else px
    sparks = {s: M.spark_series(spark_px, s) for s in df["symbol"]}
    for r in crowding_rows:
        r["spark"] = sparks.get(r["symbol"], [])
    gate = top_cutoff if panel_rank_gate == "use_cutoff" else panel_rank_gate
    return {
        "key": key, "label": label, "table": df, "sparks": sparks, "px": px,
        "benchmark": bench_sym,
        "crowded_symbols": [r["symbol"] for r in crowding_rows],
        "sections": M.pick_sections(df, gate),
        "regime": M.regime(px, bench_sym, bench_label, calendar_days),
        "summary": M.market_summary(df),
        "crowding_title": crowding_title, "crowding_blurb": crowding_blurb,
        "crowding_html": _crowding_panel(crowding_rows),
        "crowding_beyond": [], "vs_bench_header": vs_bench_header,
        "hold_header": hold_header, "top_cutoff": top_cutoff,
    }


def _demo_prices(kind, syms=None):
    """Synthetic random walks for previewing the page without network."""
    rng = np.random.default_rng(abs(hash(kind)) % 2**32)
    if kind == "crypto":
        syms = ["BTC", "ETH", "BNB", "XRP", "SOL", "TRX", "DOGE", "ADA", "HYPE", "LINK",
                "XLM", "XMR", "ZEC", "BCH", "SUI", "DOT", "UNI", "AVAX", "LTC", "TON",
                "SHIB", "PEPE", "AAVE", "NEAR", "APT", "ARB", "OP", "TIA", "SEI", "INJ",
                "FIL", "ATOM", "GRT", "PENDLE", "LDO", "ENA", "STRK", "JUP", "MORPHO", "TAO"]
    dates = pd.date_range(end=pd.Timestamp.today().normalize(), periods=260, freq="D")
    data, deriv = {}, {}
    for s in syms:
        drift = rng.normal(0.0004, 0.0025)
        vol = rng.uniform(0.012, 0.05)
        data[s] = 100 * np.exp(np.cumsum(rng.normal(drift, vol, len(dates))))
        deriv[s] = {"funding_apr": float(rng.normal(8, 18)),
                    "oi_chg_1d": float(rng.normal(0, 0.08)),
                    "oi_chg_1w": float(rng.normal(0.03, 0.15))}
    px = pd.DataFrame(data, index=dates)
    meta = {s: {"name": s.title(), "rank": i + 1} for i, s in enumerate(syms)}
    return px, meta, deriv


def main():
    demo = "--demo" in sys.argv
    markets = []
    for name, builder in (("crypto", build_crypto), ("stocks", build_stocks),
                          ("commodities", build_commodities)):
        try:
            markets.append(builder(demo=demo))
            print(f"{name}: ok ({len(markets[-1]['table'])} assets)")
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"{name}: FAILED ({e}) - skipping this tab")
    if not markets:
        raise SystemExit("No market could be built.")
    html = R.render(markets, dt.datetime.now(dt.timezone.utc))
    Path("docs").mkdir(exist_ok=True)
    Path("docs/index.html").write_text(html, encoding="utf-8")
    print(f"wrote docs/index.html ({len(html)//1024} kB)")
    _write_prices_json(markets)
    _write_screener_json(markets)


SCREENER_NUM_COLS = [
    "r_1d", "r_1w", "r_1m", "r_2m", "dist_50ma", "vs_bench_1m", "accel",
    "vol_1d_sigma", "strength_pct", "pct_52w_range",
    "funding_apr", "oi_chg_1d", "oi_chg_1w", "cot_pctile", "cot_net_pct_oi",
]


def _jsonable(v):
    """NaN/inf -> None; numpy scalars -> plain Python."""
    import math
    if v is None:
        return None
    if isinstance(v, (np.floating, np.integer)):
        v = v.item()
    if isinstance(v, float):
        return None if (math.isnan(v) or math.isinf(v)) else round(v, 6)
    return v


def _write_screener_json(markets):
    """Machine-readable twin of index.html.

    index.html is for reading; this is for consuming. Same numbers, no HTML —
    per-asset metrics, the section picks, and the regime call, so downstream
    tools can reason about the screener's output instead of re-deriving it."""
    import json

    out = {"updated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
           "markets": {}}

    for m in markets:
        df = m["table"]
        cols = [c for c in SCREENER_NUM_COLS if c in df.columns]
        assets = []
        for _, r in df.iterrows():
            a = {"symbol": r["symbol"], "name": r.get("name", r["symbol"]),
                 "group": r.get("group", "") or "", "sector": r.get("sector", "") or "",
                 "rank": int(r["rank"]) if r["rank"] < 10**6 else None,
                 "trend": r.get("trend", "—")}
            for c in cols:
                a[c] = _jsonable(r[c])
            if "cot_date" in df.columns and r["cot_date"]:
                a["cot_date"] = r["cot_date"]
            assets.append(a)

        sec = m["sections"]
        picks = {k: sec[k][0]["symbol"].tolist() for k in ("strongest", "accel", "washed", "big")}
        picks["crowded"] = m.get("crowded_symbols", [])

        out["markets"][m["key"]] = {
            "label": m["label"], "benchmark": m.get("benchmark"),
            "regime": m["regime"], "summary": m["summary"],
            "picks": picks, "assets": assets,
        }

    Path("docs/screener.json").write_text(json.dumps(out), encoding="utf-8")
    n = sum(len(v["assets"]) for v in out["markets"].values())
    print(f"wrote docs/screener.json ({n} assets across {len(out['markets'])} markets)")


def _write_prices_json(markets):
    """Small feed the local portfolio cockpit reads: latest price per symbol
    plus ~120 days of SPY and BTC closes for benchmark overlays."""
    import json
    prices, benchmarks = {}, {}
    for m in markets:
        px = m.get("px")
        if px is None:
            continue
        for sym in px.columns:
            if sym == "BASKET":
                continue
            s = px[sym].dropna()
            if not s.empty:
                prices[sym] = round(float(s.iloc[-1]), 8)
        for b in ("SPY", "BTC"):
            if b in px.columns and b not in benchmarks:
                s = px[b].dropna().tail(120)
                benchmarks[b] = [[i.strftime("%Y-%m-%d"), round(float(v), 4)]
                                 for i, v in s.items()]
    out = {"updated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
           "prices": prices, "benchmarks": benchmarks}
    Path("docs/prices.json").write_text(json.dumps(out), encoding="utf-8")
    print(f"wrote docs/prices.json ({len(prices)} symbols)")


if __name__ == "__main__":
    main()
