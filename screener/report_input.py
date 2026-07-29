"""Turns screener.json into the daily fundamentals report's mechanical inputs.

The screener measures price. The report reasons about fundamentals. This is the
seam: it pre-computes everything the report can get from the tape, so the
narrative work starts from numbers instead of from searches.

What it does NOT do is form a view. Every section below is the technical axis
only; the fundamental axis is added by hand on top.

    python -m screener.report_input
    python -m screener.report_input --url https://USER.github.io/market-screener/screener.json
    python -m screener.report_input --json     # machine-readable
"""
from __future__ import annotations

import argparse
import json
import statistics as st
import sys
from pathlib import Path

# Commodity groups promoted to their own report sectors (13 = energy, 14 = metals)
SECTOR_GROUPS = {"Energy": "13 · Energy complex", "Metals": "14 · Metals"}

# A theme this dominant in the outlier list means the "outliers" are one trade.
CONCENTRATION_WARN = 0.5


def load(src: str | None) -> dict:
    if src and src.startswith("http"):
        import urllib.request
        with urllib.request.urlopen(src, timeout=30) as r:
            return json.loads(r.read().decode())
    p = Path(src or "docs/screener.json")
    if not p.exists():
        sys.exit(f"no screener.json at {p} — run `python -m screener.main` first")
    return json.loads(p.read_text())


def _med(vals):
    vals = [v for v in vals if v is not None]
    return st.median(vals) if vals else None


def _pct(x, d=1):
    return "—" if x is None else f"{x * 100:+.{d}f}%"


# --------------------------------------------------------------- layer 0

def regimes(data: dict) -> list:
    out = []
    for key, m in data["markets"].items():
        r = m["regime"]
        out.append({"market": key, "state": r["state"],
                    "benchmark": m.get("benchmark"), "note": r["text"]})
    return out


def breadth(m: dict) -> dict:
    a = m["assets"]
    up_w = [x for x in a if (x.get("r_1w") or 0) > 0]
    up_m = [x for x in a if (x.get("r_1m") or 0) > 0]
    trends = {}
    for x in a:
        trends[x.get("trend", "—")] = trends.get(x.get("trend", "—"), 0) + 1
    return {"n": len(a), "up_1w": len(up_w), "up_1m": len(up_m),
            "median_1m": _med([x.get("r_1m") for x in a]), "trends": trends}


# --------------------------------------------------------------- layer 1

def group_sweep(m: dict) -> list:
    """Per-theme aggregates — the sector sweep, measured rather than asserted."""
    groups: dict[str, list] = {}
    for a in m["assets"]:
        groups.setdefault(a.get("group") or "Ungrouped", []).append(a)
    rows = []
    for g, items in groups.items():
        rows.append({
            "group": g, "n": len(items),
            "median_strength": _med([x.get("strength_pct") for x in items]),
            "median_1m": _med([x.get("r_1m") for x in items]),
            "median_2m": _med([x.get("r_2m") for x in items]),
            "n_uptrend": sum(1 for x in items if x.get("trend") == "uptrend"),
            "n_downtrend": sum(1 for x in items if x.get("trend") == "downtrend"),
            "leaders": [x["symbol"] for x in sorted(
                items, key=lambda y: y.get("strength_pct") or 0, reverse=True)[:3]],
            "laggards": [x["symbol"] for x in sorted(
                items, key=lambda y: y.get("strength_pct") or 0)[:3]],
        })
    return sorted(rows, key=lambda r: r["median_strength"] or 0, reverse=True)


# --------------------------------------------------------------- layer 3

def outliers(m: dict, min_strength=70.0) -> dict:
    """Strong and still accelerating. Flags whether they are all one trade —
    the check I have otherwise been doing by eye."""
    picks = [a for a in m["assets"]
             if (a.get("strength_pct") or 0) >= min_strength
             and (a.get("accel") or 0) > 0]
    picks.sort(key=lambda a: a.get("strength_pct") or 0, reverse=True)
    picks = picks[:8]
    conc = {}
    for a in picks:
        g = a.get("group") or "Ungrouped"
        conc[g] = conc.get(g, 0) + 1
    top_share = (max(conc.values()) / len(picks)) if picks else 0
    dominant = max(conc, key=conc.get) if conc else None
    # "Ungrouped" is absence of tagging, not a shared trade — never warn on it.
    warn = (dominant not in (None, "Ungrouped")
            and top_share >= CONCENTRATION_WARN and len(picks) >= 3)
    return {"names": picks, "concentration": conc,
            "dominant_group": dominant, "top_share": top_share,
            "warn": warn, "untagged": dominant == "Ungrouped"}


def washed(m: dict, max_2m=-0.15) -> list:
    """Worst 2-month performers. A watch list until the fundamental leg says
    otherwise — that adjudication is not made here."""
    picks = [a for a in m["assets"] if (a.get("r_2m") or 0) <= max_2m]
    return sorted(picks, key=lambda a: a.get("r_2m") or 0)[:8]


# --------------------------------------------------------------- crowding

def crowding(key: str, m: dict) -> list:
    out = []
    for a in m["assets"]:
        if key == "crypto":
            apr, oi = a.get("funding_apr"), a.get("oi_chg_1w")
            if apr is not None and apr > 20 and (oi or 0) > 0.08:
                out.append({"symbol": a["symbol"],
                            "why": f"funding ~{apr:.0f}%/yr, OI +{oi * 100:.0f}% 1w"})
        elif key == "commodities":
            p = a.get("cot_pctile")
            if p is not None and (p >= 90 or p <= 10):
                side = "long" if p >= 90 else "short"
                out.append({"symbol": a["symbol"],
                            "why": f"specs crowded {side}, {p:.0f}th pctile"})
        else:
            d = a.get("dist_50ma")
            if d is not None and d > 0.20:
                out.append({"symbol": a["symbol"],
                            "why": f"{d * 100:+.0f}% vs 50-day"})
    return out


# --------------------------------------------- report sectors 13 & 14

def commodity_sectors(data: dict) -> dict:
    m = data["markets"].get("commodities")
    if not m:
        return {}
    out = {}
    for grp, label in SECTOR_GROUPS.items():
        items = [a for a in m["assets"] if a.get("group") == grp]
        if not items:
            continue
        out[label] = sorted(items, key=lambda a: a.get("r_1m") or 0, reverse=True)
    return out


# --------------------------------------------------------------- output

def build(data: dict) -> dict:
    return {
        "updated": data.get("updated"),
        "regimes": regimes(data),
        "markets": {k: {"breadth": breadth(m), "groups": group_sweep(m),
                        "outliers": outliers(m), "washed": washed(m),
                        "crowded": crowding(k, m)}
                    for k, m in data["markets"].items()},
        "commodity_sectors": commodity_sectors(data),
    }


def emit(b: dict) -> None:
    W = 74
    print("=" * W)
    print(f"REPORT INPUTS · screener data as of {b['updated']}")
    print("=" * W)

    print("\nLAYER 0 — REGIME\n" + "-" * W)
    for r in b["regimes"]:
        print(f"  {r['market']:<13} {r['state'].upper():<8} (vs {r['benchmark']})")

    for key, m in b["markets"].items():
        bd = m["breadth"]
        print(f"\n{key.upper()} — breadth\n" + "-" * W)
        print(f"  {bd['up_1w']}/{bd['n']} up 1w · {bd['up_1m']}/{bd['n']} up 1m "
              f"· median 1m {_pct(bd['median_1m'])}")
        print("  trends: " + " · ".join(f"{k} {v}" for k, v in sorted(bd["trends"].items())))

        print(f"\nLAYER 1 — {key} group sweep\n" + "-" * W)
        print(f"  {'group':<16}{'n':>4}{'str':>7}{'1m':>9}{'2m':>9}   up/down   leaders")
        for g in m["groups"]:
            s = "—" if g["median_strength"] is None else f"{g['median_strength']:.0f}"
            print(f"  {g['group'][:15]:<16}{g['n']:>4}{s:>7}"
                  f"{_pct(g['median_1m']):>9}{_pct(g['median_2m']):>9}"
                  f"   {g['n_uptrend']}/{g['n_downtrend']:<5}  {', '.join(g['leaders'])}")

        o = m["outliers"]
        print(f"\nLAYER 3 — {key} outliers (strong + accelerating)\n" + "-" * W)
        if not o["names"]:
            print("  none clear the screen today.")
        for a in o["names"]:
            print(f"  {a['symbol']:<8} str {a['strength_pct']:>3.0f} · "
                  f"1m {_pct(a.get('r_1m')):>8} · accel {_pct(a.get('accel')):>7} · "
                  f"{a.get('group') or '—'}")
        if o["warn"]:
            print(f"\n  ** CONCENTRATION: {o['top_share']:.0%} of these are "
                  f"{o['dominant_group']}. Not diversification — one trade. **")
        elif o.get("untagged"):
            print("\n  (no group tags in this universe — concentration check unavailable)")

        if m["crowded"]:
            print(f"\n{key} — crowded\n" + "-" * W)
            for c in m["crowded"]:
                print(f"  {c['symbol']:<8} {c['why']}")

        if m["washed"]:
            print(f"\n{key} — washed out (watch list, needs fundamental leg)\n" + "-" * W)
            print("  " + " · ".join(f"{a['symbol']} {_pct(a.get('r_2m'), 0)}"
                                    for a in m["washed"]))

    if b["commodity_sectors"]:
        print("\nREPORT SECTORS 13 & 14\n" + "-" * W)
        for label, items in b["commodity_sectors"].items():
            print(f"\n  {label}")
            for a in items:
                cot = a.get("cot_pctile")
                tail = f" · COT {cot:.0f}th" if cot is not None else ""
                print(f"    {a['symbol']:<8}{_pct(a.get('r_1w')):>9} 1w"
                      f"{_pct(a.get('r_1m')):>10} 1m  {a.get('trend', '—'):<10}{tail}")

    print("\n" + "=" * W)
    print("Technical axis only. Fundamental axis is added by hand:")
    print("  strong + improving  -> confirmed trend")
    print("  strong + deteriorating -> distribution risk   <- the valuable cell")
    print("  washed + improving  -> contrarian list")
    print("  washed + deteriorating -> value trap")
    print("=" * W)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", help="live screener.json URL")
    ap.add_argument("--path", help="local screener.json (default docs/screener.json)")
    ap.add_argument("--json", action="store_true", help="emit JSON instead of text")
    args = ap.parse_args()
    b = build(load(args.url or args.path))
    print(json.dumps(b, indent=2)) if args.json else emit(b)


if __name__ == "__main__":
    main()
