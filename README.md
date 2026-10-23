# news-digest｜綠洋 SI 日報（GreenOcean SI Daily）

每天台灣時間早上 6:00 自動：

1. 抓美國 AI 大廠、AI 新創、財經新聞（13 個 RSS 來源 + 選用 NewsAPI.org）
2. 用 Claude 挑出最重要的新聞，分三類，寫台灣繁體中文標題、摘要與「為什麼重要」
3. 產生網站（GitHub Pages）與 RSS feed，可再接 Facebook / LINE / Telegram 自動發文

## 一次性設定（約 10 分鐘）

1. **API key 放進 GitHub Secrets**
   Repo → Settings → Secrets and variables → Actions → New repository secret
   - `ANTHROPIC_API_KEY`：到 https://platform.claude.com/settings/keys 申請（建議，翻譯品質關鍵）
   - `NEWSAPI_KEY`：你申請的 NewsAPI.org key（選用，沒有也能跑）
2. **允許 Actions 寫入 repo**
   Settings → Actions → General → Workflow permissions → 選 **Read and write permissions** → Save
3. **開啟 GitHub Pages**
   Settings → Pages → Source 選 **Deploy from a branch** → Branch `main`、資料夾 `/docs` → Save
4. **手動跑一次測試**
   Actions → Daily News Digest → Run workflow。約 1–2 分鐘後，網站在
   `https://greenocean-tech.github.io/news-digest/`

之後每天自動執行，不用再管。

## Telegram 頻道自動發文（選用）

每天產生日報後，自動在 Telegram 頻道發一則今日重點（標題直接連到原文）。
設定 `TELEGRAM_BOT_TOKEN`、`TELEGRAM_CHAT_ID` 兩個 Secrets 即啟用。預覽：`python telegram_post.py --dry-run`

## Facebook 粉專自動發文（選用）

每天產生日報後，自動在粉專發一篇「今日重點＋網站連結」。設定 `FB_PAGE_ID`、`FB_PAGE_TOKEN` 兩個 Secrets 即啟用，沒設定就略過。
預覽發文內容：`python facebook_post.py --dry-run`

## 本機測試（Windows）

```
copy .env.example .env      (填入 key)
run_news.bat                (跑完會自動打開網頁)
```

## 調整

全部在 `config.py`：新聞來源、每類篇數、網站名稱、Claude 模型（`claude-haiku-5-5` 較便宜）。

## 檔案

| 檔案 | 作用 |
|---|---|
| `digest.py` | 主程式 |
| `sources.py` | 抓 RSS / NewsAPI、去重 |
| `curate.py` | 挑重點、翻譯（Claude；沒 key 時改用 Google 免費翻譯） |
| `telegram_post.py` | 發文到 Telegram 頻道 |
| `facebook_post.py` | 發文到 Facebook 粉專 |
| `build_site.py` | 產生 `docs/` 網站與 `feed.xml` |
| `data/` | 每日結果 JSON（之後要接社群發文可直接讀） |

## 注意

- 網站只放 AI 改寫的摘要並連回原文，不轉貼全文，避免著作權問題。
- NewsAPI 免費方案限開發用途、文章有延遲；正式商用請升級或只用 RSS。
