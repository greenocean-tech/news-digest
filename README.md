# 綠洋 SI 日報｜GreenOcean SI Daily

**[繁體中文](#繁體中文) ｜ [English](#english)**

🌐 網站 Website：https://greenocean-tech.github.io/news-digest/
📲 Telegram：https://t.me/GREENOcean_news

---

## 繁體中文

當 AI 成為 SI（超級智慧）之後，世界改變的速度只會更快。綠洋 SI 日報每天早上整理美國 AI 大廠、AI 新創與財經市場最重要的新聞，用繁體中文幫你跟上。

### 每天自動做的事（台灣時間早上 6:00）

1. 從 13 個 RSS 來源（另可選用 NewsAPI.org）抓取美國 AI 大廠、AI 新創與財經新聞
2. 挑出最重要的新聞，分成三類，寫成台灣繁體中文的標題與摘要
   - 有 `ANTHROPIC_API_KEY`：由 Claude 改寫，並加上「為什麼重要」與今日導讀
   - 沒有 key：用關鍵字分類，再用免費翻譯服務翻譯
3. 產生網站（GitHub Pages）、RSS feed，以及給其他網站使用的 `latest.json`
4. 產生 IG 新聞圖卡（1080×1350）與 IG 文案
5. 發到 Telegram 頻道：文字重點（附一鍵分享到 X / Threads 的連結）＋ IG 圖卡
6. **每週一**：在最上方加上追蹤股「本週＋下週」財報行事曆

### 一次性設定（約 10 分鐘）

1. **把金鑰放進 GitHub Secrets**
   Repo → Settings → Secrets and variables → Actions → New repository secret

   | Secret | 用途 | 必要嗎 |
   |---|---|---|
   | `ANTHROPIC_API_KEY` | Claude 改寫與挑選，到 https://platform.claude.com/settings/keys 申請 | 建議 |
   | `NEWSAPI_KEY` | NewsAPI.org 額外新聞來源 | 選用 |
   | `TELEGRAM_BOT_TOKEN`、`TELEGRAM_CHAT_ID` | Telegram 頻道自動發文 | 選用 |
   | `FB_PAGE_ID`、`FB_PAGE_TOKEN` | Facebook 粉專自動發文 | 選用 |
   | `FINNHUB_API_KEY` | 財報行事曆的備用資料來源 | 選用 |

2. **允許 Actions 寫入 repo**：Settings → Actions → General → Workflow permissions → **Read and write permissions**
3. **開啟 GitHub Pages**：Settings → Pages → Deploy from a branch → `main`、`/docs`
4. **手動試跑**：Actions → Daily News Digest → Run workflow

### 發到 IG / Facebook / Threads / X

- **IG＋FB＋Threads**：每天在 Telegram 長按圖卡存到手機、複製文案，在 IG 發文時打開「Facebook」與「Threads」開關，一次發到三個平台
- **X / Threads**：點 Telegram 貼文或網站上的「一鍵分享」，內容已經預先填好
- **全自動發到 X / Threads**：用 IFTTT 讀取社群專用 RSS `https://greenocean-tech.github.io/news-digest/social.xml`（每天一則；標題＝X 貼文、內容＝Threads 貼文）

### 調整設定

全部在 `config.py`：新聞來源、每類篇數、網站名稱、Claude 模型、Afterword 推廣卡片（`PROMO`）、Telegram 頻道，以及財報追蹤清單（`EARNINGS_WATCHLIST`）。

目前追蹤的財報：TSM、NVDA、AMD、SPCX、META、KLAC、AMAT、DELL、ARM、MU、SKHY、SNDK

### 本機測試（Windows）

```
copy .env.example .env      (填入 key)
run_news.bat                (跑完會自動打開網頁)
```

預覽發文內容、不實際發送：`python telegram_post.py --dry-run`

### 檔案

| 檔案 | 作用 |
|---|---|
| `digest.py` | 主程式 |
| `sources.py` | 抓 RSS / NewsAPI、去重 |
| `curate.py` | 挑重點、翻譯 |
| `build_site.py` | 產生 `docs/` 網站、`feed.xml`、`latest.json` |
| `card.py` | IG 新聞圖卡與文案 |
| `share.py` | X / Threads 一鍵分享 |
| `earnings.py` | 每週財報行事曆 |
| `telegram_post.py` | 發文到 Telegram 頻道 |
| `facebook_post.py` | 發文到 Facebook 粉專 |
| `data/` | 每日結果 JSON |

### 注意

- 網站只放自己改寫的摘要並連回原文，不轉貼全文，以尊重著作權。
- 本日報為新聞整理與產業解讀，**不構成投資建議**。財報日期可能變動，請以公司公告為準。
- NewsAPI 免費方案限開發用途；正式商用請升級，或只使用 RSS。

---

## English

After AI became SI (superintelligence), the world started moving faster than ever. Every morning, GreenOcean SI Daily brings you the most important news on US AI companies, AI startups and the markets, summarized in Traditional Chinese.

### What runs automatically every day (6:00 AM Taiwan time)

1. Fetches US news on AI companies, AI startups and markets from 13 RSS feeds (plus NewsAPI.org, optional)
2. Picks the most important stories, sorts them into three categories, and writes Traditional Chinese headlines and summaries
   - With `ANTHROPIC_API_KEY`: Claude rewrites each story and adds "why it matters" and a daily lead
   - Without a key: keyword-based sorting plus free machine translation
3. Builds the website (GitHub Pages), an RSS feed, and `latest.json` for other sites to embed
4. Renders an Instagram news card (1080×1350) and an IG caption
5. Posts to the Telegram channel: the text digest (with one-tap share links for X / Threads) plus the IG card
6. **Every Monday**: adds a "this week + next week" earnings calendar for the watchlist at the top

### One-time setup (about 10 minutes)

1. **Add keys as GitHub Secrets**
   Repo → Settings → Secrets and variables → Actions → New repository secret

   | Secret | Purpose | Required? |
   |---|---|---|
   | `ANTHROPIC_API_KEY` | Claude curation and rewriting — get one at https://platform.claude.com/settings/keys | Recommended |
   | `NEWSAPI_KEY` | Extra news source from NewsAPI.org | Optional |
   | `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | Auto-post to a Telegram channel | Optional |
   | `FB_PAGE_ID`, `FB_PAGE_TOKEN` | Auto-post to a Facebook Page | Optional |
   | `FINNHUB_API_KEY` | Backup data source for the earnings calendar | Optional |

2. **Let Actions write to the repo**: Settings → Actions → General → Workflow permissions → **Read and write permissions**
3. **Turn on GitHub Pages**: Settings → Pages → Deploy from a branch → `main`, `/docs`
4. **Test run**: Actions → Daily News Digest → Run workflow

### Posting to Instagram / Facebook / Threads / X

- **IG + FB + Threads**: in Telegram, long-press the daily card to save it and copy the caption. When posting on Instagram, turn on "Facebook" and "Threads" to publish to all three at once.
- **X / Threads**: tap "one-tap share" in the Telegram post or on the website. The text is already filled in.
- **Fully automatic X / Threads**: point IFTTT at the social feed `https://greenocean-tech.github.io/news-digest/social.xml` (one item per day; title = X post, description = Threads post).

### Configuration

Everything lives in `config.py`: news sources, stories per category, site name, Claude model, the Afterword promo card (`PROMO`), the Telegram channel, and the earnings watchlist (`EARNINGS_WATCHLIST`).

Current earnings watchlist: TSM, NVDA, AMD, SPCX, META, KLAC, AMAT, DELL, ARM, MU, SKHY, SNDK

### Run locally (Windows)

```
copy .env.example .env      (fill in your keys)
run_news.bat                (opens the site when done)
```

Preview the post without sending it: `python telegram_post.py --dry-run`

### Files

| File | Purpose |
|---|---|
| `digest.py` | Main script |
| `sources.py` | Fetch RSS / NewsAPI and de-duplicate |
| `curate.py` | Pick top stories and translate |
| `build_site.py` | Build the `docs/` site, `feed.xml` and `latest.json` |
| `card.py` | Instagram news card and caption |
| `share.py` | One-tap share links for X / Threads |
| `earnings.py` | Weekly earnings calendar |
| `telegram_post.py` | Post to the Telegram channel |
| `facebook_post.py` | Post to a Facebook Page |
| `data/` | Daily results as JSON |

### Notes

- The site publishes only our own rewritten summaries and links to the original articles. It never republishes full text, out of respect for copyright.
- This digest is news curation and industry commentary, **not investment advice**. Earnings dates can change, so always check the company's own announcement.
- NewsAPI's free plan is for development only. Upgrade for commercial use, or rely on RSS only.
