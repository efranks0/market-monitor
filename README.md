# market-screener

A private dashboard that answers, twice a day: **what's strong, what's moving,
what's crowded** — across ~100 crypto assets, ~90 thematic stocks, and ~27
commodities. Inspired by the crypto-screener format: strength ranks, momentum
acceleration, crowded positioning, washed-out watch lists, and big-move
follow-through, each translated to its market's native data.

**No server, no cost.** GitHub Actions rebuilds the page at ~07:00 and ~15:00
Cyprus time; GitHub Pages hosts it at your own URL.

---

## One-time setup (~15 minutes, no coding)

### 1. Create a GitHub account
Go to https://github.com/signup if you don't have one.

### 2. Create the repository
- Click **+** (top right) → **New repository**
- Name: `market-screener` · visibility: **Public** (required for free Pages)
- Do **not** tick "Add a README" · click **Create repository**

### 3. Upload the project
- On the empty repo page click **uploading an existing file**
- Drag in ALL files and folders from the unzipped project **except** the
  `.github` folder (GitHub's uploader often skips dot-folders — we add it next)
- Click **Commit changes**

### 4. Add the automation file
- Click **Add file → Create new file**
- In the name box type exactly: `.github/workflows/update.yml`
  (typing the `/` creates the folders)
- Paste in the full contents of `setup/update.yml` from this project
- Click **Commit changes**

### 5. Get your two free API keys
- **CoinGecko** (crypto prices): https://www.coingecko.com/en/api → sign up →
  Developer Dashboard → create a **Demo** key → copy it
- **Coinalyze** (funding & open interest): https://coinalyze.net → sign up →
  Account → API → copy your key

### 6. Add the keys to the repo
- In your repo: **Settings → Secrets and variables → Actions → New repository secret**
- Name: `COINGECKO_API_KEY`, paste the CoinGecko key → **Add secret**
- Repeat with name `COINALYZE_API_KEY` and the Coinalyze key

### 7. Turn on the web page
- **Settings → Pages** → under "Build and deployment":
  Source **Deploy from a branch** · Branch **main** · Folder **/docs** → **Save**

### 8. Run it for the first time
- **Actions** tab → click **update screener** → **Run workflow → Run workflow**
- The first run takes ~10 minutes (it downloads 100 days of history for
  every asset; later runs are much faster)
- When it's green, your dashboard is live at:
  `https://YOUR-USERNAME.github.io/market-screener/`
- Bookmark it. It refreshes itself twice a day from now on.

---

## Everyday use

- **Change the stock list**: edit `config/stocks.txt` in the GitHub website
  (pencil icon), commit — the next update picks it up. Same for
  `config/commodities.txt`.
- **Force a refresh now**: Actions tab → update screener → Run workflow.
- **If a run fails**: open the red run in the Actions tab, copy the log,
  and paste it to Claude — it's usually a one-line fix.

## What the metrics mean

- **Strongest right now** — composite of 1m/2m returns, distance above the
  50-day average, and performance vs the benchmark; shown as "stronger than
  X% of the market".
- **Picking up speed** — assets whose past week beat the pace their past
  month implied. Early inflections.
- **Crowded longs / Stretched / Crowded positioning** — the risk overlay:
  perp funding + open-interest build-up (crypto), extension above the 50-day
  average (stocks), speculator COT percentiles (commodities). Crowded ≠ weak;
  it means the exit is narrow.
- **Washed out** — worst 2-month performers. A watch list, not a buy list.
- **Yesterday's big moves** — 1-day moves beyond 2 standard deviations of the
  asset's own volatility; large names tend to drift onward, not snap back.
- **Regime banner** — Bitcoin / the S&P 500 / the commodity basket vs its
  200-day average. Context that changes how everything above should be read.

*Not investment advice. Data: CoinGecko, Coinalyze, Yahoo Finance, CFTC.*

---

## The portfolio cockpit (`portfolio.html`)

A second, **private** component: a single file you keep on your own computer.
It is deliberately NOT part of the public web page — your positions, balances
and PnL never leave your browser.

**Setup**: double-click `portfolio.html`. That's it. Then:
1. **Settings** → add your accounts (IBKR, Kraken, …) and paste your feed URL:
   `https://YOUR-USERNAME.github.io/market-screener/prices.json`
2. **Journal** → record a *deposit* into each account, then add your trades
   (buys/sells with symbol, quantity, price, theme).
3. **Positions/Dashboard** now show live-marked values, exposure by theme and
   account, unrealized/realized PnL.
4. **History** → press *Snapshot now* once a day; the equity chart,
   flow-adjusted PnL calendar, and SPY/BTC benchmark overlay build from these.

**Protect your data**: it lives in the browser's local storage. Use
*Settings → Export backup* regularly (the file also moves your cockpit to
another device via *Import backup*). *Privacy mode* blurs all money amounts
for screenshots. Auto-sync from brokers/exchanges is a possible later phase.
