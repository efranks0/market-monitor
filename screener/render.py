"""Renders one self-contained index.html with three market tabs.
Visual language follows the reference: white broadsheet, hairline rules,
small-caps section labels, mono numerals, blue/ochre sparklines."""
from __future__ import annotations

import datetime as dt
import html

import pandas as pd

POS = "#3b6ea5"
NEG = "#b4550a"


def fmt_pct(x, digits=1, sign=True):
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return "—"
    v = x * 100
    s = "+" if (sign and v >= 0.05) else ""
    return f"{s}{v:.{digits}f}%"


def cls(x):
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return ""
    return "pos" if x >= 0 else "neg"


def spark_svg(points, w=96, h=26):
    if not points or len(points) < 3:
        return ""
    lo, hi = min(points + [0]), max(points + [0])
    rng = (hi - lo) or 1e-9
    pad = 2
    xs = [pad + i * (w - 2 * pad) / (len(points) - 1) for i in range(len(points))]
    ys = [h - pad - (p - lo) / rng * (h - 2 * pad) for p in points]
    y0 = h - pad - (0 - lo) / rng * (h - 2 * pad)
    d = "M " + " L ".join(f"{x:.1f} {y:.1f}" for x, y in zip(xs, ys))
    color = POS if points[-1] >= 0 else NEG
    return (f'<svg class="spark" viewBox="0 0 {w} {h}" width="{w}" height="{h}">'
            f'<line x1="{pad}" y1="{y0:.1f}" x2="{w-pad}" y2="{y0:.1f}" '
            f'stroke="#c9c4bb" stroke-width="1" stroke-dasharray="2 3"/>'
            f'<path d="{d}" fill="none" stroke="{color}" stroke-width="1.4" '
            f'stroke-linejoin="round" stroke-linecap="round"/></svg>')


def _panel(title, blurb, body, beyond, top_cutoff):
    extra = ""
    if beyond:
        extra = (f'<p class="beyond">beyond the top {top_cutoff}: '
                 + " · ".join(html.escape(s) for s in beyond) + "</p>")
    return (f'<section class="panel"><h2>{title}</h2><p class="blurb">{blurb}</p>'
            f'{body}{extra}</section>')


def mini_rows(rows):
    if not rows:
        return '<p class="empty">No names stand out today.</p>'
    out = []
    for r in rows:
        out.append('<div class="mini">'
                   f'<span class="sym">{html.escape(r["symbol"])}</span>'
                   f'{r.get("spark", "")}'
                   f'<span class="desc">{r["desc"]}</span></div>')
    return "".join(out)


CSS = """
:root { --ink:#1c1a17; --mut:#6f6a61; --faint:#9a948a; --rule:#e3ded5; --bg:#fdfcfa;
        --pos:POSCOLOR; --neg:NEGCOLOR; }
* { box-sizing:border-box; }
body { margin:0; background:var(--bg); color:var(--ink);
  font:14px/1.45 ui-sans-serif, system-ui, "Segoe UI", Helvetica, Arial, sans-serif; }
.wrap { max-width:1500px; margin:0 auto; padding:22px 28px 60px; }
header { display:flex; align-items:baseline; justify-content:space-between; gap:16px; flex-wrap:wrap; }
h1 { font-size:19px; letter-spacing:-.01em; margin:0; }
.sub { color:var(--mut); font-size:12.5px; margin:4px 0 0; }
.meta { font-size:11px; color:var(--faint); }
.tabs { display:inline-flex; border:1px solid var(--rule); border-radius:3px; overflow:hidden; margin-left:12px; }
.tab { appearance:none; border:0; background:transparent; padding:5px 12px; font-size:11px;
  letter-spacing:.08em; text-transform:uppercase; color:var(--mut); cursor:pointer; }
.tab.active { background:#efece6; color:var(--ink); font-weight:600; }
.banner { margin:20px 0 8px; font-weight:600; font-size:14.5px; }
.banner.down { color:#a03123; } .banner.up { color:#2c6141; } .banner.unknown { color:var(--mut); }
.bullets { display:flex; flex-wrap:wrap; gap:6px 26px; color:var(--mut); font-size:12.5px;
  padding:0 0 14px; border-bottom:1px solid var(--rule); }
.bullets span::before { content:"• "; color:var(--faint); }
.panels { display:grid; grid-template-columns:repeat(auto-fit,minmax(240px,1fr)); gap:0 34px; margin-top:6px; }
.panel h2 { font-size:11px; letter-spacing:.1em; text-transform:uppercase; font-weight:700;
  border-bottom:1px solid var(--ink); padding:14px 0 6px; margin:0 0 8px; }
.blurb { color:var(--mut); font-size:11.5px; margin:0 0 10px; }
.mini { display:grid; grid-template-columns:56px 96px 1fr; gap:10px; align-items:center; padding:5px 0; }
.mini .sym { font-weight:700; font-size:12.5px; }
.mini .desc { font-size:11.5px; color:var(--mut); }
.mini .desc b { color:var(--ink); font-weight:600; }
.beyond, .empty { font-size:11px; color:var(--faint); margin:10px 0 0; }
.note { font-size:11px; color:var(--faint); margin:18px 0 0; }
h3.all { font-size:11px; letter-spacing:.1em; text-transform:uppercase; border-bottom:1px solid var(--ink);
  padding:26px 0 6px; margin:12px 0 0; display:flex; justify-content:space-between; align-items:baseline; }
h3.all .ctl { font-weight:400; letter-spacing:0; text-transform:none; color:var(--faint); font-size:11px; }
.showall { border:1px solid var(--rule); background:#fff; border-radius:3px; font-size:10.5px;
  letter-spacing:.06em; text-transform:uppercase; padding:3px 9px; cursor:pointer; color:var(--mut); margin-left:10px; }
table { width:100%; border-collapse:collapse; margin-top:2px; }
th { font-size:10.5px; color:var(--mut); font-weight:600; text-align:right; padding:8px 10px 6px;
  border-bottom:1px solid var(--rule); cursor:pointer; white-space:nowrap; user-select:none; }
th.l, td.l { text-align:left; }
th .arr { color:var(--faint); font-size:9px; }
td { padding:6px 10px; border-bottom:1px solid #f0ece5; font-size:12.5px; text-align:right;
  font-variant-numeric:tabular-nums; font-family:ui-monospace,"SF Mono",Consolas,monospace; white-space:nowrap; }
td.l { font-family:inherit; }
td .nm { color:var(--faint); font-size:11px; margin-left:7px; }
td b { font-weight:700; }
.pos { color:var(--pos); } .neg { color:var(--neg); }
.plain { font-family:ui-sans-serif,system-ui,sans-serif; font-size:11.5px; }
.tag { font-family:ui-sans-serif,system-ui,sans-serif; font-size:10px; border:1px solid var(--rule);
  border-radius:3px; padding:1px 6px; color:var(--mut); }
.tag.warn { border-color:#d9b48a; color:#9c5a12; }
tr.hidden { display:none; }
.mkt { display:none; } .mkt.active { display:block; }
@media (max-width:760px) { .wrap{padding:16px 14px 40px} .mini{grid-template-columns:48px 80px 1fr}
  td .nm{display:none} th,td{padding:6px 6px} }
""".replace("POSCOLOR", POS).replace("NEGCOLOR", NEG)

JS = """
document.querySelectorAll('.tab').forEach(t => t.addEventListener('click', () => {
  document.querySelectorAll('.tab').forEach(x => x.classList.toggle('active', x===t));
  document.querySelectorAll('.mkt').forEach(m => m.classList.toggle('active', m.dataset.mkt===t.dataset.tab));
}));
document.querySelectorAll('.showall').forEach(b => b.addEventListener('click', () => {
  const tbl = document.querySelector('table[data-mkt="' + b.dataset.mkt + '"]');
  const showing = b.dataset.on === '1';
  tbl.querySelectorAll('tr.extra').forEach(r => r.classList.toggle('hidden', showing));
  b.dataset.on = showing ? '0' : '1';
  b.textContent = showing ? 'show all' : 'show fewer';
}));
document.querySelectorAll('th[data-col]').forEach(th => th.addEventListener('click', () => {
  const tbl = th.closest('table'), tb = tbl.querySelector('tbody');
  const col = +th.dataset.col, dir = th.dataset.dir === 'a' ? -1 : 1;
  tbl.querySelectorAll('th').forEach(h => delete h.dataset.dir);
  th.dataset.dir = dir === 1 ? 'a' : 'd';
  Array.from(tb.rows).sort((r1,r2) => {
    const a = parseFloat(r1.cells[col].dataset.v), b = parseFloat(r2.cells[col].dataset.v);
    const av = isNaN(a) ? -Infinity*dir : a, bv = isNaN(b) ? -Infinity*dir : b;
    return (av - bv) * -dir;
  }).forEach(r => tb.appendChild(r));
}));
"""


def render(markets, generated_utc, title="market-screener"):
    tabs, bodies = [], []
    for i, m in enumerate(markets):
        active = " active" if i == 0 else ""
        tabs.append(f'<button class="tab{active}" data-tab="{m["key"]}">{html.escape(m["label"])}</button>')
        bodies.append(_market_body(m, active))
    stamp = generated_utc.strftime("%Y-%m-%d %H:%M UTC")
    return ('<!DOCTYPE html>\n<html lang="en"><head>\n'
            '<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">\n'
            '<meta name="robots" content="noindex, nofollow">\n'
            f'<title>{html.escape(title)}</title>\n<style>{CSS}</style></head><body><div class="wrap">\n'
            '<header><div>'
            f'<h1>{html.escape(title)}</h1>'
            '<p class="sub">What’s strong, what’s moving, what’s crowded — measured daily across crypto, stocks and commodities.</p></div>'
            f'<div class="meta">data as of {stamp} <span class="tabs">{"".join(tabs)}</span></div>'
            '</header>\n'
            + "".join(bodies)
            + f'</div>\n<script>{JS}</script></body></html>')


def _market_body(m, active):
    df = m["table"]
    sparks = m["sparks"]
    sec = m["sections"]
    cutoff = m.get("top_cutoff", 30)

    def mrow(r, desc):
        return {"symbol": r["symbol"], "spark": spark_svg(sparks.get(r["symbol"], [])), "desc": desc}

    s_head, s_beyond = sec["strongest"]
    strongest = mini_rows([mrow(r, f'Stronger than <b>{int(r["strength_pct"])}%</b> of the market · {fmt_pct(r["r_1m"])} this month')
                           for _, r in s_head.iterrows()])
    a_head, a_beyond = sec["accel"]
    accel = mini_rows([mrow(r, f'<b>{fmt_pct(r["r_1w"])}</b> this past week · {fmt_pct(r["r_1m"])} over the whole month')
                       for _, r in a_head.iterrows()])
    w_head, w_beyond = sec["washed"]
    washed = mini_rows([mrow(r, f'<b>{fmt_pct(r["r_2m"])}</b> over the past two months')
                        for _, r in w_head.iterrows()])
    b_head, b_beyond = sec["big"]
    big = mini_rows([mrow(r, f'<b>{fmt_pct(r["r_1d"])}</b> yesterday · a {abs(r["vol_1d_sigma"]):.1f}σ move')
                     for _, r in b_head.iterrows()])
    crowd_body = m.get("crowding_html") or '<p class="empty">No major names stand out today.</p>'

    panels = (
        _panel("Strongest right now",
               "Best overall marks for the past month — returns, trend, and standing vs the rest of the market.",
               strongest, s_beyond, cutoff)
        + _panel("Picking up speed",
                 "Doing better over the past 1–3 weeks than their past month would suggest.",
                 accel, a_beyond, cutoff)
        + _panel(m.get("crowding_title", "Crowded longs"), m.get("crowding_blurb", ""),
                 crowd_body, m.get("crowding_beyond", []), cutoff)
        + _panel("Washed out",
                 "The biggest losers of the past two months — the zone where rebounds have historically formed. A watch list, not a buy list.",
                 washed, w_beyond, cutoff)
        + _panel("Yesterday’s big moves",
                 "Outsized one-day moves. Large names have tended to keep drifting the same way, not snap back.",
                 big, b_beyond, cutoff)
    )

    heads = [("l", "#"), ("l", "asset"), ("", "yesterday"), ("", "1 week"), ("", "1 month"),
             ("", "2 months"), ("l", "vs market · 1m"), ("l", "trend"),
             ("l", m.get("vs_bench_header", "vs benchmark · 1m")),
             ("l", m.get("hold_header", "cost to hold")), ("l", "worth noting")]
    ths = "".join(f'<th class="{c}" data-col="{i}">{h} <span class="arr">▾</span></th>'
                  for i, (c, h) in enumerate(heads))

    rows = []
    for i, (_, r) in enumerate(df.iterrows()):
        extra = ' class="extra hidden"' if i >= cutoff else ""
        vb = r["vs_bench_1m"] if not pd.isna(r["vs_bench_1m"]) else "nan"
        cells = "".join(
            f'<td data-v="{(r[c] if not pd.isna(r[c]) else "nan")}" class="{cls(r[c])}">{fmt_pct(r[c])}</td>'
            for c in ("r_1d", "r_1w", "r_1m", "r_2m"))
        rows.append(
            f'<tr{extra}>'
            f'<td class="l" data-v="{r["rank"]}">{int(r["rank"]) if r["rank"] < 10**6 else "—"}</td>'
            f'<td class="l" data-v="{r["rank"]}"><b>{html.escape(str(r["symbol"]))}</b>'
            f'<span class="nm">{html.escape(str(r["name"]))}</span></td>'
            + cells
            + f'<td class="l" data-v="{vb}">{spark_svg(sparks.get(r["symbol"], []))}</td>'
            f'<td class="l plain" data-v="0">{r["trend"]}</td>'
            f'<td class="l plain" data-v="{vb}">{r.get("vs_bench_label", "—")}</td>'
            f'<td class="l plain" data-v="0">{r.get("hold_label", "—")}</td>'
            f'<td class="l" data-v="0">{r.get("note_html", "—") or "—"}</td></tr>')

    bullets = "".join(f"<span>{b}</span>" for b in m["summary"])
    reg = m["regime"]
    n_shown = min(cutoff, len(df))

    return (f'<div class="mkt{active}" data-mkt="{m["key"]}">\n'
            f'<p class="banner {reg["state"]}">{reg["text"]}</p>\n'
            f'<div class="bullets">{bullets}</div>\n'
            f'<div class="panels">{panels}</div>\n'
            '<p class="note">Sparklines show each asset against the average tracked asset over the past month '
            '— above the dotted line means ahead of the market.</p>\n'
            f'<h3 class="all">All assets <span class="ctl">{n_shown} of {len(df)} tracked · click a column to sort '
            f'<button class="showall" data-mkt="{m["key"]}" data-on="0">show all</button></span></h3>\n'
            f'<table data-mkt="{m["key"]}"><thead><tr>{ths}</tr></thead><tbody>{"".join(rows)}</tbody></table>\n'
            '</div>')
