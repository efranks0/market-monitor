# Setup — start to finish

You do not need Python. You do not need to install anything. Everything runs on
GitHub's computers. All you need is a browser.

Budget about 20 minutes, most of it waiting.

---

## 1. GitHub account

https://github.com/signup — skip if you have one.

## 2. Make the repository

Top right **+** → **New repository**.

- Name: `market-screener`
- Visibility: **Public** — required for free Pages hosting
- Do **not** tick "Add a README"
- **Create repository**

Public means the code and the market data are visible to anyone. Your positions
are not in the repo — they live in your browser only. See step 10.

## 3. Upload the files

On the empty repo page click **uploading an existing file**.

Unzip the bundle. Open the `market-screener` folder. Select everything inside
it and drag it into the browser window.

GitHub's uploader silently skips folders starting with a dot, so the
`.github` folder will not make it. That is expected — step 4 handles it.

Scroll down, click **Commit changes**.

Check you now have: `screener/`, `config/`, `docs/`, `requirements.txt`,
`portfolio.html`, `README.md`, `REPORT-SPEC.md`, `SETUP.md`.

## 4. Add the automation file by hand

**Add file** → **Create new file**.

In the filename box type exactly, including both slashes:

```
.github/workflows/update.yml
```

The slashes create the folders as you type.

Open `.github/workflows/update.yml` from the unzipped bundle in any text editor,
copy all of it, paste it into the big box. **Commit changes**.

## 5. Two free API keys

**CoinGecko** — crypto prices.
https://www.coingecko.com/en/api → sign up → Developer Dashboard → create a
**Demo** key → copy it.

**Coinalyze** — funding rates and open interest.
https://coinalyze.net → sign up → Account → API → copy the key.

Both are free. Coinalyze is optional — without it the crypto crowding panel is
blank and the report loses its positioning data, but everything else works.

## 6. Store the keys in the repo

**Settings** → **Secrets and variables** → **Actions** → **New repository
secret**.

- Name `COINGECKO_API_KEY`, paste the CoinGecko key, **Add secret**
- Name `COINALYZE_API_KEY`, paste the Coinalyze key, **Add secret**

Type the names exactly. Secrets are encrypted and are not visible in the public
repo.

## 7. Run it

**Actions** tab. If it asks you to enable workflows, say yes.

Click **update screener** in the left sidebar → **Run workflow** → **Run
workflow**.

Refresh after a few seconds. A yellow dot means running. **The first run takes
about ten minutes** because it downloads 100 days of history for every asset.
Later runs take one or two minutes. Green tick means done.

If it goes red, click into it, copy the log, paste it to Claude.

## 8. Turn on the web page

**Settings** → **Pages**. Under "Build and deployment":

- Source: **Deploy from a branch**
- Branch: **main**, folder: **/docs**
- **Save**

Wait a minute or two, then open:

```
https://YOUR-USERNAME.github.io/market-screener/
```

Bookmark it. It refreshes itself twice a day from now on.

## 9. Give Claude the feed URL

For the daily fundamentals report, Claude needs the raw file, not the Pages URL:

```
https://raw.githubusercontent.com/YOUR-USERNAME/market-screener/main/docs/screener.json
```

Paste that into a chat when you ask for a report.

## 10. The portfolio cockpit

`portfolio.html` is separate and private. It never goes on the web page.

Download it from the repo to your own computer and double-click it. Then:

1. **Settings** → add your accounts → paste your feed URL:
   `https://YOUR-USERNAME.github.io/market-screener/prices.json`
2. **Journal** → record a deposit into each account, then add your trades
3. **Positions / Dashboard** now show live-marked values
4. **History** → press *Snapshot now* once a day to build the equity chart

Your positions live in your browser's local storage and are sent nowhere. Use
**Settings → Export backup** regularly — clearing browser data will erase them.

---

## Everyday use

- **Change the stock list** — edit `config/stocks.txt` on the GitHub website
  (pencil icon), commit. The next run picks it up.
- **Force a refresh** — Actions → update screener → Run workflow.
- **A run failed** — open the red run, copy the log, paste it to Claude.

## Timing

The two scheduled runs are 04:00 and 12:00 UTC, which in Cyprus summer time is
about 07:00 and 15:00 — before the European open and before the US open.

GitHub's scheduler is best-effort and often runs late under load. If a run is
missing, trigger it manually.
