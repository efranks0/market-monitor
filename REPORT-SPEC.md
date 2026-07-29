# Daily Fundamentals Report — spec

The counterpart to the screener. The screener measures price; this reasons about
fundamentals. Neither is complete alone.

Delivered on request, fresh each time. Separate from chart analysis — that has
its own structure and the two never merge.

**Feed it first:** `python -m screener.report_input --url <pages-url>/screener.json`
The digest that prints is the technical axis for Layers 0, 1 and 3. Start there,
then add the fundamental axis. Anything the screener can measure should not be
asserted from memory.

---

## TL;DR (top of report)

Above everything else. Nobody should read 2,000 words to get the call.

- **Daily** — into the next session close. Directional label plus the payoff
  structure, not just a direction.
- **Weekly** — 1–2 weeks, split by asset class. Each gets: 🟢/🟡/🔴, a conviction
  level, the supporting evidence, and **an explicit invalidation.**
- **The one thing to watch** — a single variable.

Invalidation is event-and-data based, not chart levels. Precise support and
resistance belongs in the chart deliverable where the tape is visible.

---

## Layer 0 — Macro

Runs every day whether or not anything printed. The regime call is what the rest
of the report hangs off.

Fixed sub-sections, in order:

1. **Regime call** — one paragraph, the frame
2. **Growth** — GDP tracking vs official forecasts; note the gap between
   corporate earnings growth and real GDP
3. **Inflation** — headline and core, m/m and y/y, with the goods/services and
   energy decomposition. Energy-only disinflation is reversible; core services
   softness is not. Say which one it is.
4. **Labour** — payrolls, revisions, participation, real wages. Check whether an
   unemployment-rate move came from the numerator or the denominator.
5. **Rates and curve** — 2s, 10s, 10s2s. Compare the 2-year to the fed funds
   midpoint: that spread is how much tightening is already priced.
6. **Dollar, commodities** — and which single variable the regime currently
   runs through
7. **Credit conditions** — spreads, CDS, issuance. Financial conditions tighten
   outside the policy rate and that is frequently the real story.
8. **Policy** — decision, dots, and the gap between the data and the rhetoric
9. **Global** — non-US central banks, Europe, China
10. **Crypto–macro link** — crypto trades as a duration asset; say what it is
    currently pricing
11. **Calendar** and **what would change the regime call**

---

## Layer 1 — Sector sweep

14 buckets. Four lines each: constituents, quality read, last 24h, sector state
(improving / deteriorating / flat).

| # | Bucket |
|---|---|
| 1–11 | GICS sectors, top 10 by market cap |
| 12 | Crypto — top 10 protocols, scored on fees, active addresses, TVL, supply schedule, staking |
| 13 | **Energy complex** — crude, refined products, natural gas |
| 14 | **Metals** — precious and industrial as separate sub-reads |

**Double-count rule.** GICS Energy and Materials are *equities*. Buckets 13 and
14 are the *physical*. They have different drivers and different invalidation,
and the spread between them is often the signal. Never collapse them.

**Metals is two markets.** Precious is a real-rates trade. Industrial is a
growth-and-electrification trade. One narrative covering both will be wrong.

Uranium gets its own line under 14 — not a metal in the usual sense, but the
nuclear names in `config/stocks.txt` trade off it. Watch term contracting, not
spot; utilities transact on term.

---

## Layer 2 — Deep dive

One sector daily. Full table: market cap, forward P/E, EV/EBITDA, revenue
growth, gross and operating margin, FCF margin, net debt/EBITDA, ROIC. Then a
quality ranking and where the numbers disagree with the pricing.

**Selection:** whichever bucket has the most real fundamental news flow that day.
Override by naming one. Rotation only as a dead-news-day fallback — the flow
should pick, not the calendar.

---

## Layer 3 — Outlier screen

Non-top-10 names with fundamental support. 5–8, capped for readability.

`report_input.py` produces the candidate list mechanically: strength ≥ 70 and
still accelerating, with the concentration check computed rather than eyeballed.
The report adds the fundamental leg — revisions, FCF inflection, leverage.

**Heed the concentration warning.** If most of the list shares a theme, that is
one trade wearing several costumes, and it must be said plainly.

Washed-out names stay a watch list until the fundamental leg adjudicates. That
adjudication is the whole point of the section.

---

## Layer 4 — Calendar

Earnings inside the covered universe over 48h, plus macro prints that reprice
sectors. For crypto, include options expiry and unlock schedules.

---

## The 2×2

The unifying frame, shared with the chart deliverable's confluence-vs-conflict
section. Technical axis from the screener, fundamental axis from the report.

| | Fundamentals improving | Fundamentals deteriorating |
|---|---|---|
| **Screener: strong** | Confirmed trend | **Distribution risk** |
| **Screener: washed out** | **Contrarian list** | Value trap |

The off-diagonals are the entire point. Neither system finds them alone.

---

## Discipline

- **Every figure carries an as-of date.** Anything not sourceable same-day is
  flagged stale, never quietly filled in from memory.
- **Check the primary release date.** A figure quoted in a two-week-old
  secondary article may already be superseded. This has caused one error: May
  CPI at 4.2% was cited on 28 July when the June print (3.5% headline, 2.6%
  core, released 14 July) had already landed.
- **Corrections go at the top of the next report**, before anything else.
- **Sell-side price targets are events, not analysis.** Ratings changes appear in
  the 24h line. They never appear as conclusions.
- **Say what could not be verified.** A flagged gap is worth more than a
  confident guess.
- **Conviction is stated, not implied.** Low conviction said plainly beats a
  hedged paragraph.
- **No personal-position commentary from raw position data.** Aggregate theme
  weights only, never sizes. `portfolio.html` keeps positions in the browser by
  design and that design holds.
