"""把今天的日報發到 Telegram 頻道（每天一則，不會重複發）。

需要兩個 GitHub Secrets：
  TELEGRAM_BOT_TOKEN  從 @BotFather 拿到的機器人權杖
  TELEGRAM_CHAT_ID    頻道帳號，例如 @greenocean_news（公開頻道）或 -100 開頭的數字（私人頻道）
沒設定就自動略過。機器人必須先被加為頻道「管理員」。

本機預覽不真的發：python telegram_post.py --dry-run
"""
import json
import os
import sys
from datetime import datetime
from html import escape
from pathlib import Path

import requests

import config

ROOT = Path(__file__).parent
DATA = ROOT / "data"
POSTED = DATA / "tg_posted.json"
EMOJI = {"ai_company": "🤖", "ai_startup": "🚀", "finance": "📈"}
WEEKDAY = "一二三四五六日"
PER_CATEGORY = 4


def build_message(d: dict) -> str:
    dt = datetime.strptime(d["date"], "%Y-%m-%d")
    page = f"{config.SITE_URL}{d['date']}.html"
    lines = [f"<b>📰 {escape(config.SITE_TITLE)}｜{dt.month}/{dt.day}（{WEEKDAY[dt.weekday()]}）</b>", ""]
    if d.get("headline"):
        lines += [escape(d["headline"]), ""]
    for cat, label in config.CATEGORY_LABELS.items():
        stories = sorted((s for s in d["stories"] if s["category"] == cat),
                         key=lambda s: -s.get("importance", 0))[:PER_CATEGORY]
        if stories:
            lines.append(f"<b>{EMOJI[cat]} {label}</b>")
            # 每則標題直接連到原文
            lines += [f'• <a href="{escape(s["url"])}">{escape(s["zh_title"])}</a>' for s in stories]
            lines.append("")
    lines.append(f'👉 <a href="{page}">完整摘要</a>')
    return "\n".join(lines)


def main(dry_run: bool = False) -> None:
    files = sorted(DATA.glob("20*.json"))
    if not files:
        print("[TG] 沒有日報資料，略過")
        return
    d = json.loads(files[-1].read_text("utf-8"))
    if not d.get("stories"):
        print("[TG] 今天沒有新聞，略過")
        return
    message = build_message(d)
    if dry_run:
        print(message)
        return

    token, chat = os.getenv("TELEGRAM_BOT_TOKEN"), os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat:
        print("[TG] 沒有 TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID，略過")
        return
    posted = json.loads(POSTED.read_text("utf-8")) if POSTED.exists() else {}
    if d["date"] in posted:
        print(f"[TG] {d['date']} 已經發過，略過")
        return

    try:
        r = requests.post(f"https://api.telegram.org/bot{token.strip()}/sendMessage",
                          json={"chat_id": chat.strip(), "text": message, "parse_mode": "HTML",
                                "link_preview_options": {"is_disabled": True}}, timeout=30)
        body = r.json()
    except Exception as exc:  # 不印出網址，避免露出權杖
        body = {"ok": False, "error_code": "network", "description": type(exc).__name__}
    if not body.get("ok"):
        print(f"::error title=Telegram 發文失敗::{body.get('error_code')}: {body.get('description')}")
        print(f"[TG 發文失敗] {body.get('error_code')}: {body.get('description')}")
        if body.get("error_code") == 400 and "chat not found" in str(body.get("description")):
            print("  → 檢查 TELEGRAM_CHAT_ID 是否正確（公開頻道要含 @）")
        if body.get("error_code") == 404:
            print("  → TELEGRAM_BOT_TOKEN 格式不對：應該只有「數字:英數字」一串，不要多複製其他文字")
        if body.get("error_code") == 401:
            print("  → TELEGRAM_BOT_TOKEN 不正確，請重新從 @BotFather 複製")
        if body.get("error_code") == 403:
            print("  → 機器人還不是頻道管理員，請到頻道設定把它加為管理員")
        sys.exit(1)
    posted[d["date"]] = body["result"]["message_id"]
    POSTED.write_text(json.dumps(posted, indent=2), "utf-8")
    print(f"[TG] 已發文到 {chat}（message_id {posted[d['date']]}）")


if __name__ == "__main__":
    main(dry_run="--dry-run" in sys.argv)
