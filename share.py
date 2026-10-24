"""產生分享到 X / Threads 的預填文字與一鍵連結（不需要任何 API key）。"""
import unicodedata
from datetime import datetime
from urllib.parse import quote

import config

WEEKDAY = "一二三四五六日"
X_LIMIT = 280      # X 以「加權字數」計：中日韓字元算 2，網址固定算 23
THREADS_LIMIT = 500


def page_url(d: dict) -> str:
    return f"{config.SITE_URL}{d['date']}.html"


def _x_weight(text: str) -> int:
    w = 0
    for ch in text:
        cp = ord(ch)
        # X 規則：這些範圍算 1，其餘（含中日韓、全形標點、emoji）算 2
        light = (cp <= 0x10FF or 0x2000 <= cp <= 0x200D or 0x2010 <= cp <= 0x201F
                 or 0x2032 <= cp <= 0x2037)
        w += 1 if light else 2
    return w


def _top(d: dict, n: int) -> list[str]:
    stories = sorted(d.get("stories", []), key=lambda s: -s.get("importance", 0))
    return [s["zh_title"] for s in stories[:n]]


def _head(d: dict) -> str:
    dt = datetime.strptime(d["date"], "%Y-%m-%d")
    return f"📰 {config.SITE_TITLE}｜{dt.month}/{dt.day}（{WEEKDAY[dt.weekday()]}）"


def x_text(d: dict) -> str:
    """X 貼文：標題 + 盡量多的重點 + 連結，控制在 280 加權字數內。"""
    head, tail = _head(d), "#AI #美股"
    budget = X_LIMIT - 23 - 4  # 網址 23，換行與空白預留
    lines = [head]
    used = _x_weight(head) + _x_weight(tail) + 2
    for t in _top(d, 4):
        line = f"• {t}"
        if used + _x_weight(line) + 1 > budget:
            # 放不下整行就截短一次後停止
            room = budget - used - 3
            cut = ""
            for ch in line:
                if _x_weight(cut + ch) > room:
                    break
                cut += ch
            if len(cut) > 8:
                lines.append(cut + "…")
            break
        lines.append(line)
        used += _x_weight(line) + 1
    return "\n".join(lines) + f"\n{tail}"


def threads_text(d: dict) -> str:
    """Threads 貼文：最多 500 字。"""
    parts = [_head(d), ""]
    if d.get("headline"):
        parts += [d["headline"], ""]
    parts += [f"• {t}" for t in _top(d, 5)]
    parts += ["", f"完整摘要 👉 {page_url(d)}"]
    text = "\n".join(parts)
    while len(text) > THREADS_LIMIT and len(parts) > 4:
        parts.pop(-3)  # 從最後一則重點開始拿掉
        text = "\n".join(parts)
    return unicodedata.normalize("NFC", text)


def x_intent(d: dict) -> str:
    return f"https://x.com/intent/post?text={quote(x_text(d))}&url={quote(page_url(d))}"


def threads_intent(d: dict) -> str:
    return f"https://www.threads.net/intent/post?text={quote(threads_text(d))}"
