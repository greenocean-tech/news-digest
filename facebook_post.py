"""把今天的日報發到 Facebook 粉絲專頁（每天一篇，不會重複發）。

需要兩個 GitHub Secrets：
  FB_PAGE_ID     粉專 ID（數字）
  FB_PAGE_TOKEN  粉專的長期 Page Access Token（權限 pages_manage_posts）
沒設定就自動略過。

本機測試不真的發文：python facebook_post.py --dry-run
"""
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import requests

import config

ROOT = Path(__file__).parent
DATA = ROOT / "data"
POSTED = DATA / "fb_posted.json"
GRAPH = "https://graph.facebook.com/v23.0"
EMOJI = {"ai_company": "🤖", "ai_startup": "🚀", "finance": "📈"}
WEEKDAY = "一二三四五六日"
PER_CATEGORY = 3


def build_message(d: dict) -> str:
    dt = datetime.strptime(d["date"], "%Y-%m-%d")
    lines = [f"📰 {config.SITE_TITLE}｜{dt.month}/{dt.day}（{WEEKDAY[dt.weekday()]}）", ""]
    if d.get("headline"):
        lines += [d["headline"], ""]
    for cat, label in config.CATEGORY_LABELS.items():
        stories = sorted((s for s in d["stories"] if s["category"] == cat),
                         key=lambda s: -s.get("importance", 0))[:PER_CATEGORY]
        if stories:
            lines.append(f"{EMOJI[cat]} {label}")
            lines += [f"• {s['zh_title']}" for s in stories]
            lines.append("")
    lines.append("👉 完整摘要與原文連結：")
    lines.append(f"{config.SITE_URL}{d['date']}.html")
    lines += ["", "#AI #人工智慧 #新創 #美股 #科技新聞"]
    return "\n".join(lines)


def main(dry_run: bool = False) -> None:
    files = sorted(DATA.glob("20*.json"))
    if not files:
        print("[FB] 沒有日報資料，略過")
        return
    d = json.loads(files[-1].read_text("utf-8"))
    if not d.get("stories"):
        print("[FB] 今天沒有新聞，略過")
        return
    message = build_message(d)
    if dry_run:
        print(message)
        return

    page_id, token = os.getenv("FB_PAGE_ID"), os.getenv("FB_PAGE_TOKEN")
    if not page_id or not token:
        print("[FB] 沒有 FB_PAGE_ID / FB_PAGE_TOKEN，略過")
        return
    posted = json.loads(POSTED.read_text("utf-8")) if POSTED.exists() else {}
    if d["date"] in posted:
        print(f"[FB] {d['date']} 已經發過（{posted[d['date']]}），略過")
        return

    r = requests.post(f"{GRAPH}/{page_id}/feed",
                      data={"message": message, "link": f"{config.SITE_URL}{d['date']}.html",
                            "access_token": token}, timeout=30)
    body = r.json()
    if "id" not in body:
        err = body.get("error", {})
        print(f"::error title=Facebook 發文失敗::{err.get('code')}: {err.get('message')}")
        print(f"[FB 發文失敗] {err.get('code')} {err.get('type')}: {err.get('message')}")
        sys.exit(1)
    posted[d["date"]] = body["id"]
    POSTED.write_text(json.dumps(posted, indent=2), "utf-8")
    print(f"[FB] 已發文：https://www.facebook.com/{body['id']}")


if __name__ == "__main__":
    main(dry_run="--dry-run" in sys.argv)
