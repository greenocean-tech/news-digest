"""每日 IG 新聞圖卡（1080×1350，IG 直式最佳比例）＋ 可直接複製的 IG 文案。

輸出：docs/cards/YYYY-MM-DD.png、docs/cards/latest.png
字型：Noto Sans CJK（GitHub Actions 上由 workflow 安裝 fonts-noto-cjk）
"""
import glob
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import config

ROOT = Path(__file__).parent
CARDS = ROOT / "docs" / "cards"
W, H = 1080, 1350
PAD = 84
WEEKDAY = "一二三四五六日"
NO_LINE_START = set("，。、；：？！）」』”’,.;:?!)]%…")

BG_TOP, BG_BOTTOM = (6, 46, 52), (9, 84, 82)      # 深海綠漸層
INK, MUTED, ACCENT = (240, 247, 245), (164, 205, 198), (255, 196, 92)
CHIP = {"ai_company": (91, 196, 255), "ai_startup": (255, 158, 122), "finance": (134, 222, 160)}
CHIP_LABEL = {"ai_company": "AI 大廠", "ai_startup": "AI 新創", "finance": "財經"}

_font_cache: dict = {}


def font(weight: str, size: int) -> ImageFont.FreeTypeFont:
    """找繁體中文（TC）字面；不同系統的 .ttc 內字面順序不同，所以逐一比對名稱。"""
    key = (weight, size)
    if key in _font_cache:
        return _font_cache[key]
    paths = sorted(glob.glob(f"/usr/share/fonts/**/NotoSansCJK*-{weight}.tt[cf]", recursive=True)) or \
        sorted(glob.glob("/usr/share/fonts/**/NotoSansCJK*.tt[cf]", recursive=True))
    for path in paths:
        for idx in range(10):
            try:
                f = ImageFont.truetype(path, size, index=idx)
            except OSError:
                break
            if "TC" in " ".join(f.getname()):
                _font_cache[key] = f
                return f
    if paths:
        _font_cache[key] = ImageFont.truetype(paths[0], size)
        return _font_cache[key]
    raise RuntimeError("找不到 Noto Sans CJK 字型，請安裝 fonts-noto-cjk")


def wrap(draw: ImageDraw.ImageDraw, text: str, f, width: int, max_lines: int) -> list[str]:
    """中文逐字換行；英文單字盡量不切斷。超過行數就用 … 收尾。"""
    tokens, buf = [], ""
    for ch in text:
        if ch.isascii() and ch != " ":
            buf += ch
            continue
        if buf:
            tokens.append(buf)
            buf = ""
        tokens.append(ch)
    if buf:
        tokens.append(buf)

    lines, cur, i = [], "", 0
    while i < len(tokens):
        tok = tokens[i]
        if tok == " " and not cur:  # 行首不留空格
            i += 1
            continue
        hang = tok in NO_LINE_START and cur
        if draw.textlength(cur + tok, font=f) <= width or not cur or hang:
            cur += tok
            i += 1
        else:
            lines.append(cur.rstrip())
            cur = ""
            if len(lines) == max_lines:
                break
    if cur and len(lines) < max_lines:
        lines.append(cur.rstrip())
        i = len(tokens)
    if i < len(tokens):  # 還有字沒放進去 → 最後一行加 …
        last = lines[-1]
        while last and draw.textlength(last + "…", font=f) > width:
            last = last[:-1]
        lines[-1] = last.rstrip() + "…"
    return lines


def pick(d: dict, n: int = 4) -> list[dict]:
    """每類先挑最重要的一則，再依重要度補滿。"""
    stories = sorted(d.get("stories", []), key=lambda s: -s.get("importance", 0))
    chosen, seen = [], set()
    for cat in config.CATEGORY_LABELS:
        s = next((s for s in stories if s["category"] == cat), None)
        if s:
            chosen.append(s)
            seen.add(s["id"])
    for s in stories:
        if len(chosen) >= n:
            break
        if s["id"] not in seen:
            chosen.append(s)
            seen.add(s["id"])
    order = {c: i for i, c in enumerate(config.CATEGORY_LABELS)}
    return sorted(chosen[:n], key=lambda s: order.get(s["category"], 9))


def make_card(d: dict) -> Path:
    img = Image.new("RGB", (W, H))
    draw = ImageDraw.Draw(img)
    for y in range(H):  # 垂直漸層
        t = y / H
        draw.line([(0, y), (W, y)], fill=tuple(int(a + (b - a) * t) for a, b in zip(BG_TOP, BG_BOTTOM)))

    dt = datetime.strptime(d["date"], "%Y-%m-%d")
    # 頁首
    draw.text((PAD, 88), "綠洋 SI 日報", font=font("Bold", 64), fill=INK)
    draw.text((PAD, 172), "GreenOcean SI Daily", font=font("Medium", 30), fill=MUTED)
    date_txt = f"{dt.year}.{dt.month:02d}.{dt.day:02d}（{WEEKDAY[dt.weekday()]}）"
    dw = draw.textlength(date_txt, font=font("Medium", 32))
    draw.text((W - PAD - dw, 112), date_txt, font=font("Medium", 32), fill=ACCENT)
    draw.line([(PAD, 246), (W - PAD, 246)], fill=(255, 255, 255, 60), width=2)
    draw.text((PAD, 278), "今日 AI 與財經重點", font=font("Bold", 40), fill=ACCENT)

    # 新聞：先試排，確保不會擠到頁尾
    title_f, chip_f, src_f = font("Bold", 42), font("Bold", 26), font("Regular", 24)
    top, bottom = 368, 1180
    items, layout = pick(d), []
    for n in (4, 3, 2, 1):
        for max_lines in (3, 2):
            layout = [(s, wrap(draw, s["zh_title"], title_f, W - 2 * PAD, max_lines)) for s in items[:n]]
            if top + sum(62 + 58 * len(ls) + 34 for _, ls in layout) - 34 <= bottom:
                break
        else:
            continue
        break
    y = top
    for s, lines in layout:
        label = CHIP_LABEL.get(s["category"], "")
        cw = draw.textlength(label, font=chip_f) + 32
        draw.rounded_rectangle([PAD, y, PAD + cw, y + 44], radius=22, fill=CHIP.get(s["category"], MUTED))
        draw.text((PAD + 16, y + 6), label, font=chip_f, fill=(10, 30, 34))
        draw.text((PAD + cw + 18, y + 9), s.get("source", ""), font=src_f, fill=MUTED)
        y += 62
        for line in lines:
            draw.text((PAD, y), line, font=title_f, fill=INK)
            y += 58
        y += 34

    # 頁尾
    draw.line([(PAD, 1206), (W - PAD, 1206)], fill=(255, 255, 255, 60), width=2)
    draw.text((PAD, 1232), "完整摘要與原文連結 → 個人檔案連結", font=font("Medium", 30), fill=INK)
    draw.text((PAD, 1280), config.SITE_URL.replace("https://", "").rstrip("/"), font=font("Regular", 26), fill=MUTED)

    CARDS.mkdir(parents=True, exist_ok=True)
    out = CARDS / f"{d['date']}.png"
    img.save(out, optimize=True)
    img.save(CARDS / "latest.png", optimize=True)
    return out


def ig_caption(d: dict) -> str:
    dt = datetime.strptime(d["date"], "%Y-%m-%d")
    lines = [f"綠洋 SI 日報｜{dt.month}/{dt.day}（{WEEKDAY[dt.weekday()]}）今日 AI 與財經重點", ""]
    if d.get("headline"):
        lines += [d["headline"], ""]
    for s in pick(d, 5):
        lines.append(f"▪️ {s['zh_title']}")
    lines += ["", "📌 每天早上更新，完整摘要與原文連結在個人檔案",
              "", "#AI #人工智慧 #科技新聞 #美股 #新創 #OpenAI #輝達 #綠洋SI日報"]
    return "\n".join(lines)[:2100]  # IG 上限 2200 字


if __name__ == "__main__":
    import json
    f = sorted((ROOT / "data").glob("20*.json"))[-1]
    d = json.loads(f.read_text("utf-8"))
    print(make_card(d))
    print(ig_caption(d))
