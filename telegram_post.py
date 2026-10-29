"""把今天的日報發到 Telegram 頻道（每天一則，不會重複發）。

需要兩個 GitHub Secrets：
  TELEGRAM_BOT_TOKEN  從 @BotFather 拿到的機器人權杖
  TELEGRAM_CHAT_ID    頻道帳號，例如 @greenocean_news（公開頻道）或 -100 開頭的數字（私人頻道）
沒設定就自動略過。機器人必須先被加為頻道「管理員」。

本機預覽不真的發：python telegram_post.py --dry-run
"""
import json
import os
import re
import sys
from datetime import datetime
from html import escape
from pathlib import Path

import requests

import config
import share

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
    if d.get("earnings"):
        import earnings
        cal = d["earnings"]
        lines.append(f"<b>📅 {escape(earnings.headline(cal))}</b>")
        week = None
        for day in cal.get("days", []):
            if day.get("week") != week:
                week = day.get("week")
                lines.append(f"<i>{escape(week or '')}</i>")
            lines.append(f"{escape(day['label'])}：" + "、".join(escape(earnings.item_text(i)) for i in day["items"]))
        if not cal.get("days"):
            lines.append("追蹤清單中的公司，這兩週都沒有公布財報。")
        lines.append("")
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
    lines.append(f'📤 一鍵分享：<a href="{escape(share.x_intent(d))}">X</a>｜'
                 f'<a href="{escape(share.threads_intent(d))}">Threads</a>')
    return "\n".join(lines)


def clean_token(raw: str) -> str | None:
    """從貼上的內容中找出「數字:英數字」權杖；容許多餘文字、換行、空白、bot 前綴。"""
    pattern = r"(?<![A-Za-z0-9])(\d{5,15}:[A-Za-z0-9_-]{30,50})(?![A-Za-z0-9_-])"
    raw = re.sub(r"(?i)bot(?=\d{5,15}:)", " ", raw)  # 去掉 bot 前綴
    m = re.search(pattern, raw)  # 先在原文找（整段 BotFather 訊息也可以）
    if not m:
        m = re.search(pattern, re.sub(r"\s+", "", raw))  # 權杖中間被換行切斷時
    return m.group(1) if m else None


def clean_chat(raw: str) -> str:
    """接受 @name、name、t.me/name、https://t.me/name 或 -100 開頭的數字。"""
    c = raw.strip()
    m = re.search(r"t\.me/([A-Za-z0-9_]+)", c)
    if m:
        return "@" + m.group(1)
    if re.fullmatch(r"-?\d+", c):
        return c
    return c if c.startswith("@") else "@" + c


def tg(token: str, method: str, payload: dict | None = None, tries: int = 4) -> dict:
    """呼叫 Telegram；網路錯誤或 5xx/429 會等一下再試。"""
    import time
    last = {}
    for attempt in range(tries):
        try:
            r = requests.post(f"https://api.telegram.org/bot{token}/{method}", json=payload or {}, timeout=30)
            body = r.json()
            retry = body.get("error_code") == 429 or r.status_code >= 500
            if not retry:
                return body
            last = body
            wait = (body.get("parameters") or {}).get("retry_after") or 5 * (attempt + 1)
        except Exception as exc:  # 不印出網址，避免露出權杖
            last = {"ok": False, "error_code": "network", "description": type(exc).__name__}
            wait = 5 * (attempt + 1)
        if attempt < tries - 1:
            time.sleep(min(wait, 30))
    return last


def send_card(token: str, chat: str, d: dict) -> bool:
    """發 IG 圖卡（照片）＋可直接複製的 IG 文案；失敗只警告，不影響主貼文。"""
    path = ROOT / "docs" / "cards" / f"{d['date']}.png"
    if not path.exists():
        print("[TG] 今天沒有圖卡，略過")
        return False
    try:
        import card
        caption = card.ig_caption(d)[:1000]  # Telegram 圖片說明上限 1024 字
        with path.open("rb") as fh:
            r = requests.post(f"https://api.telegram.org/bot{token}/sendPhoto",
                              data={"chat_id": chat, "caption": caption},
                              files={"photo": (path.name, fh, "image/png")}, timeout=60)
        body = r.json()
        if body.get("ok"):
            print("[TG] 已發 IG 圖卡")
            return True
        else:
            print(f"::warning title=Telegram 圖卡發送失敗::{body.get('error_code')}: {body.get('description')}")
    except Exception as exc:
        print(f"::warning title=Telegram 圖卡發送失敗::{type(exc).__name__}")
    return False


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

    raw_token, raw_chat = os.getenv("TELEGRAM_BOT_TOKEN") or "", os.getenv("TELEGRAM_CHAT_ID") or ""
    if not raw_token or not raw_chat:
        print("[TG] 沒有 TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID，略過")
        return
    token, chat = clean_token(raw_token), clean_chat(raw_chat)
    if not token:
        # 只描述格式，不印出內容
        compact = re.sub(r"\s+", "", raw_token)
        hint = (f"長度 {len(compact)}，{'有' if ':' in compact else '沒有'}冒號，"
                f"{'看起來像頻道帳號（@ 開頭）' if compact.startswith('@') else '不是「數字:英數字」格式'}")
        print(f"::error title=Telegram 權杖格式不對::TELEGRAM_BOT_TOKEN {hint}。可能貼反了，或只複製到一部分。")
        sys.exit(1)
    me = tg(token, "getMe")
    if not me.get("ok"):
        if me.get("error_code") == "network":
            print(f"::error title=Telegram 連線失敗::{me.get('description')}（重試多次仍連不上 Telegram，通常是暫時性問題，下一個排程會自動補發）")
        else:
            print(f"::error title=Telegram 權杖無效::{me.get('error_code')}: {me.get('description')}（請到 @BotFather 用 /token 重新取得）")
        sys.exit(1)
    print(f"[TG] 機器人 @{me['result'].get('username')} 驗證成功，發到 {chat}")

    posted = json.loads(POSTED.read_text("utf-8")) if POSTED.exists() else {}
    card_key = f"{d['date']}-card"
    if d["date"] in posted:
        print(f"[TG] {d['date']} 文字已經發過")
        if card_key not in posted and send_card(token, chat, d):
            posted[card_key] = True
            POSTED.write_text(json.dumps(posted, indent=2), "utf-8")
        return

    body = tg(token, "sendMessage", {"chat_id": chat, "text": message, "parse_mode": "HTML",
                                     "link_preview_options": {"is_disabled": True}})
    if not body.get("ok"):
        print(f"::error title=Telegram 發文失敗::{body.get('error_code')}: {body.get('description')}")
        print(f"[TG 發文失敗] {body.get('error_code')}: {body.get('description')}")
        if body.get("error_code") == 400 and "chat not found" in str(body.get("description")):
            print("  → 檢查 TELEGRAM_CHAT_ID 是否正確（公開頻道要含 @）")
        if body.get("error_code") == 404:
            print("  → TELEGRAM_BOT_TOKEN 格式不對：應該只有「數字:英數字」一串，不要多複製其他文字")
        if body.get("error_code") == 401:
            print("  → TELEGRAM_BOT_TOKEN 不正確，請重新從 @BotFather 複製")
        if body.get("error_code") in (400, 403):
            info = tg(token, "getChat", {"chat_id": chat}).get("result") or {}
            print(f"::error title=Telegram 診斷::機器人 @{me['result'].get('username')}；"
                  f"TELEGRAM_CHAT_ID={chat} 對應到頻道「{info.get('title', '找不到')}」"
                  f"(@{info.get('username', '-')}, {info.get('type', '-')})")
        if body.get("error_code") == 403:
            print("  → 機器人還不是頻道管理員，請到頻道設定把它加為管理員")
        sys.exit(1)
    posted[d["date"]] = body["result"]["message_id"]
    if send_card(token, chat, d):
        posted[card_key] = True
    POSTED.write_text(json.dumps(posted, indent=2), "utf-8")
    print(f"[TG] 已發文到 {chat}（message_id {posted[d['date']]}）")


if __name__ == "__main__":
    main(dry_run="--dry-run" in sys.argv)
