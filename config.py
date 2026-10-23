"""
News Digest 設定檔 — 想加減新聞來源、改每類篇數，都在這裡改。
"""

SITE_TITLE = "綠洋 SI 日報"
SITE_TAGLINE = "GreenOcean SI Daily｜當 AI 成為 SI，每天早上 6 點用繁體中文看懂美國 AI、新創與財經大事"
SITE_URL = "https://greenocean-tech.github.io/news-digest/"  # 開好 GitHub Pages 後確認網址

# 只收最近幾小時內的新聞
LOOKBACK_HOURS = 30

# 每個分類最多挑幾則
MAX_PER_CATEGORY = {
    "ai_company": 6,   # AI 大廠：OpenAI、Anthropic、Google、Meta、Microsoft、NVIDIA...
    "ai_startup": 6,   # AI 新創：融資、併購、新產品
    "finance": 6,      # 財經：美股、Fed、科技股財報
}

CATEGORY_LABELS = {
    "ai_company": "AI 大廠動態",
    "ai_startup": "AI 新創與融資",
    "finance": "財經與市場",
}

# ---- RSS 來源（免費、不需要 key）----
RSS_FEEDS = [
    # AI / 科技
    ("TechCrunch AI", "https://techcrunch.com/category/artificial-intelligence/feed/"),
    ("TechCrunch Startups", "https://techcrunch.com/category/startups/feed/"),
    ("TechCrunch Venture", "https://techcrunch.com/category/venture/feed/"),
    ("The Verge AI", "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml"),
    ("VentureBeat AI", "https://venturebeat.com/category/ai/feed/"),
    ("Ars Technica AI", "https://arstechnica.com/ai/feed/"),
    ("MIT Technology Review AI", "https://www.technologyreview.com/topic/artificial-intelligence/feed"),
    ("Wired AI", "https://www.wired.com/feed/tag/ai/latest/rss"),
    # 財經
    ("CNBC Technology", "https://www.cnbc.com/id/19854910/device/rss/rss.html"),
    ("CNBC Finance", "https://www.cnbc.com/id/10000664/device/rss/rss.html"),
    ("CNBC Markets", "https://www.cnbc.com/id/15839069/device/rss/rss.html"),
    ("MarketWatch Top Stories", "https://feeds.content.dowjones.io/public/rss/mw_topstories"),
    ("Yahoo Finance", "https://finance.yahoo.com/news/rssindex"),
]

# ---- NewsAPI.org 搜尋關鍵字（有設定 NEWSAPI_KEY 才會用）----
NEWSAPI_QUERIES = [
    '(OpenAI OR Anthropic OR "Google DeepMind" OR Nvidia OR Microsoft OR Meta) AND AI',
    '"AI startup" AND (raises OR funding OR acquires OR valuation)',
    '(Fed OR "Wall Street" OR Nasdaq OR "S&P 500") AND (stocks OR earnings OR rates)',
]

# 沒有 Claude key 時，用關鍵字粗分類
KEYWORDS = {
    "ai_company": ["openai", "anthropic", "google", "deepmind", "gemini", "meta", "llama",
                   "microsoft", "copilot", "nvidia", "apple", "amazon", "aws", "xai", "grok",
                   "chatgpt", "claude", "tesla", "tsmc", "amd", "intel"],
    "ai_startup": ["startup", "raises", "funding", "series a", "series b", "series c",
                   "seed round", "valuation", "acquires", "acquisition", "unicorn", "ipo",
                   "y combinator", "venture"],
    "finance": ["stock", "stocks", "market", "nasdaq", "dow", "s&p", "fed", "rates",
                "inflation", "earnings", "revenue", "treasury", "bond", "wall street",
                "economy", "jobs report", "bitcoin"],
}
AI_WORDS = ["ai", "artificial intelligence", "llm", "model", "gpt", "machine learning",
            "chatbot", "agent", "generative"]

# Claude 模型（翻譯與挑選重點）
CLAUDE_MODEL = "claude-sonnet-5-5"   # 想省錢可改成 "claude-haiku-5-5"

# ---- 自家產品推廣（每日頁面中間一張卡片 + 頁尾一行）；不想顯示就把 PROMO 設成 None ----
PROMO = {
    "label": "綠洋科技出品",
    "title": "Afterword｜有些話，即使你不能親口說，也該送到",
    "body": ("AI 讓世界變得越來越快，但有些話只有你能說。寫下給重要的人的話，"
             "若你連續 30 天沒有登入，Afterword 會以 Email 私下送給你指定的人。內容加密儲存，我們不閱讀、不出售。"),
    "cta": "寫下我的話 →",
    "url": "https://last-words-theta.vercel.app/zh-TW?utm_source=si-daily&utm_medium=web&utm_campaign=promo",
    "footer": "想留下給重要的人的話？試試 Afterword",
}
