"""把 data/*.json 變成 docs/ 靜態網站（GitHub Pages 直接讀 docs/）。"""
import json
from datetime import datetime
from email.utils import format_datetime
from html import escape
from pathlib import Path

import config

ROOT = Path(__file__).parent
DATA, DOCS = ROOT / "data", ROOT / "docs"
WEEKDAY = "一二三四五六日"

CSS = """
:root{--bg:#fbfaf8;--card:#fff;--ink:#1d1d1f;--muted:#6b6b70;--line:#ebe7e1;--accent:#f26b1d;--accent-soft:#fff1e8}
@media (prefers-color-scheme:dark){:root{--bg:#131314;--card:#1c1c1e;--ink:#f2f2f2;--muted:#a1a1a6;--line:#2c2c2e;--accent:#ff8a3d;--accent-soft:#2a1d14}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.75 -apple-system,"PingFang TC","Noto Sans TC","Microsoft JhengHei",sans-serif}
a{color:inherit}.wrap{max-width:780px;margin:0 auto;padding:0 16px}
header{border-bottom:1px solid var(--line);background:var(--card)}
.top{display:flex;align-items:baseline;justify-content:space-between;gap:12px;padding:18px 0}
.brand{font-weight:800;font-size:22px;text-decoration:none}.brand span{color:var(--accent)}
nav a{color:var(--muted);text-decoration:none;font-size:14px;margin-left:14px}
.date{margin:28px 0 4px;color:var(--muted);font-size:14px;letter-spacing:.05em}
h1{font-size:28px;line-height:1.35;margin:0 0 12px}
.lead{background:var(--accent-soft);border-left:4px solid var(--accent);padding:14px 18px;border-radius:6px;margin:16px 0 8px}
h2{font-size:19px;margin:40px 0 12px;padding-bottom:6px;border-bottom:2px solid var(--accent);display:inline-block}
.story{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:18px 20px;margin:14px 0}
.story h3{font-size:18px;line-height:1.45;margin:0 0 8px}.story h3 a{text-decoration:none}.story h3 a:hover{color:var(--accent)}
.story p{margin:6px 0}.why{color:var(--muted);font-size:15px}.why b{color:var(--accent)}
.meta{display:flex;flex-wrap:wrap;gap:6px 12px;align-items:center;font-size:13px;color:var(--muted);margin-top:10px}
.tag{background:var(--accent-soft);color:var(--accent);border-radius:999px;padding:1px 10px}
.orig{font-size:13px;color:var(--muted);font-style:italic}
.hot{color:var(--accent);font-weight:700}
.archive li{margin:6px 0}footer{color:var(--muted);font-size:13px;padding:40px 0;text-align:center}
"""


def page(title: str, body: str, desc: str = "") -> str:
    return f"""<!doctype html><html lang="zh-Hant-TW"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(title)}</title><meta name="description" content="{escape(desc or config.SITE_TAGLINE)}">
<meta property="og:title" content="{escape(title)}"><meta property="og:description" content="{escape(desc or config.SITE_TAGLINE)}">
<link rel="alternate" type="application/rss+xml" title="{escape(config.SITE_TITLE)}" href="feed.xml">
<style>{CSS}</style></head><body>
<header><div class="wrap top"><a class="brand" href="index.html">{escape(config.SITE_TITLE[:2])}<span>{escape(config.SITE_TITLE[2:])}</span></a>
<nav><a href="index.html">今日</a><a href="archive.html">歷史</a><a href="feed.xml">RSS</a></nav></div></header>
<main class="wrap">{body}</main>
<footer class="wrap">{escape(config.SITE_TAGLINE)}<br>摘要由 AI 改寫整理，詳細內容請點標題閱讀原文。</footer></body></html>"""


def nice_date(d: str) -> str:
    dt = datetime.strptime(d, "%Y-%m-%d")
    return f"{dt.year} 年 {dt.month} 月 {dt.day} 日（{WEEKDAY[dt.weekday()]}）"


def story_html(s: dict) -> str:
    tags = "".join(f'<span class="tag">{escape(t)}</span>' for t in s.get("tags", []))
    hot = '<span class="hot">重點</span>' if s.get("importance", 0) >= 5 else ""
    why = f'<p class="why"><b>為什麼重要：</b>{escape(s["why_it_matters"])}</p>' if s.get("why_it_matters") else ""
    return f"""<article class="story"><h3><a href="{escape(s['url'])}" target="_blank" rel="noopener">{escape(s['zh_title'])}</a></h3>
<p>{escape(s.get('zh_summary', ''))}</p>{why}
<p class="orig">{escape(s['title'])}</p>
<div class="meta">{hot}<span>來源：{escape(s['source'])}</span>{tags}</div></article>"""


def day_body(d: dict) -> str:
    parts = [f'<p class="date">{nice_date(d["date"])}</p><h1>今日 AI 與財經重點</h1>']
    if d.get("headline"):
        parts.append(f'<div class="lead">{escape(d["headline"])}</div>')
    for cat, label in config.CATEGORY_LABELS.items():
        stories = [s for s in d["stories"] if s["category"] == cat]
        if stories:
            parts.append(f"<section><h2>{label}</h2>{''.join(story_html(s) for s in stories)}</section>")
    if not d["stories"]:
        parts.append("<p>今天沒有抓到新的重要新聞。</p>")
    return "".join(parts)


def feed_xml(days: list[dict]) -> str:
    items = []
    for d in days[:14]:
        for s in d["stories"]:
            pub = format_datetime(datetime.fromisoformat(s["published"].replace("Z", "+00:00")))
            desc = s.get("zh_summary", "") + (f"（為什麼重要：{s['why_it_matters']}）" if s.get("why_it_matters") else "")
            items.append(f"<item><title>{escape(s['zh_title'])}</title><link>{escape(s['url'])}</link>"
                         f"<guid isPermaLink=\"false\">{s['id']}</guid><pubDate>{pub}</pubDate>"
                         f"<category>{escape(config.CATEGORY_LABELS[s['category']])}</category>"
                         f"<description>{escape(desc)}</description></item>")
    return (f'<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel>'
            f"<title>{escape(config.SITE_TITLE)}</title><link>{escape(config.SITE_URL)}</link>"
            f"<description>{escape(config.SITE_TAGLINE)}</description><language>zh-TW</language>"
            f"{''.join(items)}</channel></rss>")


def build() -> None:
    DOCS.mkdir(exist_ok=True)
    days = [json.loads(p.read_text("utf-8")) for p in sorted(DATA.glob("20*.json"), reverse=True)]
    for d in days:
        (DOCS / f"{d['date']}.html").write_text(
            page(f"{nice_date(d['date'])} | {config.SITE_TITLE}", day_body(d), d.get("headline", "")), "utf-8")
    if days:
        (DOCS / "index.html").write_text(page(config.SITE_TITLE, day_body(days[0]), days[0].get("headline", "")), "utf-8")
    links = "".join(f'<li><a href="{d["date"]}.html">{nice_date(d["date"])}</a> · {len(d["stories"])} 則</li>' for d in days)
    (DOCS / "archive.html").write_text(page(f"歷史日報 | {config.SITE_TITLE}", f'<h1 style="margin-top:28px">歷史日報</h1><ul class="archive">{links}</ul>'), "utf-8")
    (DOCS / "feed.xml").write_text(feed_xml(days), "utf-8")
    # 給其他網站（例如 Afterword /news 頁）讀的資料：最近 7 天
    keep = ("id", "category", "importance", "zh_title", "zh_summary", "why_it_matters",
            "tags", "title", "url", "source", "published")
    public = {"site": config.SITE_URL, "updated": days[0].get("generated_at", "") if days else "",
              "days": [{"date": d["date"], "headline": d.get("headline", ""),
                        "stories": [{k: s.get(k) for k in keep} for s in d["stories"]]} for d in days[:7]]}
    (DOCS / "latest.json").write_text(json.dumps(public, ensure_ascii=False), "utf-8")
    (DOCS / ".nojekyll").write_text("")
    print(f"網站已產生：docs/（{len(days)} 天）")


if __name__ == "__main__":
    build()
