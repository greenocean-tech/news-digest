"""抓新聞：RSS（免費）+ NewsAPI.org（選用，需要 NEWSAPI_KEY）。"""
import hashlib
import html
import os
import re
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

import feedparser
import requests

import config

UA = "Mozilla/5.0 (news-digest; +https://github.com/greenocean-tech/news-digest)"


def _clean(text: str, limit: int = 600) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = html.unescape(re.sub(r"\s+", " ", text)).strip()
    return text[:limit]


def _norm_url(url: str) -> str:
    url = (url or "").split("#")[0]
    url = re.sub(r"[?&](utm_[^=&]+|guccounter|guce_[^=&]+)=[^&]*", "", url)
    return url.rstrip("?&/")


def _id(url: str, title: str) -> str:
    return hashlib.sha1((_norm_url(url) or title.lower()).encode()).hexdigest()[:12]


def _entry_time(e) -> datetime | None:
    for key in ("published_parsed", "updated_parsed"):
        t = e.get(key)
        if t:
            return datetime(*t[:6], tzinfo=timezone.utc)
    for key in ("published", "updated"):
        if e.get(key):
            try:
                return parsedate_to_datetime(e[key]).astimezone(timezone.utc)
            except Exception:
                pass
    return None


def fetch_rss(since: datetime) -> list[dict]:
    items = []
    for source, url in config.RSS_FEEDS:
        try:
            resp = requests.get(url, headers={"User-Agent": UA}, timeout=20)
            resp.raise_for_status()
            feed = feedparser.parse(resp.content)
        except Exception as exc:
            print(f"  [RSS 失敗] {source}: {exc}")
            continue
        n = 0
        for e in feed.entries:
            published = _entry_time(e)
            if published and published < since:
                continue
            title = _clean(e.get("title", ""), 300)
            link = e.get("link", "")
            if not title or not link:
                continue
            items.append({
                "id": _id(link, title),
                "title": title,
                "url": _norm_url(link),
                "source": source,
                "summary": _clean(e.get("summary", "") or e.get("description", "")),
                "published": (published or datetime.now(timezone.utc)).isoformat(),
            })
            n += 1
        print(f"  [RSS] {source}: {n} 則")
    return items


def fetch_newsapi(since: datetime) -> list[dict]:
    key = os.getenv("NEWSAPI_KEY")
    if not key:
        print("  [NewsAPI] 沒有 NEWSAPI_KEY，略過")
        return []
    items = []
    for q in config.NEWSAPI_QUERIES:
        try:
            resp = requests.get(
                "https://newsapi.org/v2/everything",
                params={"q": q, "language": "en", "sortBy": "publishedAt",
                        "from": since.strftime("%Y-%m-%dT%H:%M:%S"), "pageSize": 50},
                headers={"X-Api-Key": key, "User-Agent": UA},
                timeout=20,
            )
            data = resp.json()
            if data.get("status") != "ok":
                print(f"  [NewsAPI 錯誤] {data.get('code')}: {data.get('message')}")
                continue
        except Exception as exc:
            print(f"  [NewsAPI 失敗] {exc}")
            continue
        for a in data.get("articles", []):
            title, link = a.get("title") or "", a.get("url") or ""
            if not title or not link or title == "[Removed]":
                continue
            items.append({
                "id": _id(link, title),
                "title": _clean(title, 300),
                "url": _norm_url(link),
                "source": (a.get("source") or {}).get("name") or "NewsAPI",
                "summary": _clean(a.get("description") or ""),
                "published": a.get("publishedAt") or datetime.now(timezone.utc).isoformat(),
            })
        print(f"  [NewsAPI] {q[:40]}…: {len(data.get('articles', []))} 則")
    return items


def fetch_all(seen_ids: set[str]) -> list[dict]:
    since = datetime.now(timezone.utc) - timedelta(hours=config.LOOKBACK_HOURS)
    items = fetch_rss(since) + fetch_newsapi(since)
    out, titles = [], set()
    for it in items:
        key = re.sub(r"\W+", "", it["title"].lower())[:80]
        if it["id"] in seen_ids or key in titles:
            continue
        titles.add(key)
        out.append(it)
    print(f"共 {len(items)} 則，去重後 {len(out)} 則新新聞")
    return out
