"""挑出重要新聞、分類、翻成台灣繁體中文。

有 ANTHROPIC_API_KEY → 用 Claude 挑重點 + 寫中文標題與摘要（品質好，推薦）
沒有 → 用關鍵字分類 + Google 免費翻譯（堪用，只翻標題與原文摘要）
"""
import json
import os
import re

import config

MAX_CANDIDATES = 120


def _kw_hits(text: str, words: list[str]) -> int:
    t = f" {text.lower()} "
    return sum(1 for w in words if re.search(rf"\b{re.escape(w)}\b", t))


def keyword_category(item: dict) -> tuple[str | None, int]:
    text = f"{item['title']} {item['summary']}"
    ai = _kw_hits(text, config.AI_WORDS)
    scores = {c: _kw_hits(text, ws) for c, ws in config.KEYWORDS.items()}
    if ai and scores["ai_startup"]:
        return "ai_startup", scores["ai_startup"] + ai
    if scores["ai_company"] and (ai or scores["ai_company"] >= 2):
        return "ai_company", scores["ai_company"] + ai
    if scores["finance"]:
        return "finance", scores["finance"]
    if ai:
        return "ai_company", ai
    return None, 0


def prefilter(items: list[dict]) -> list[dict]:
    scored = []
    for it in items:
        cat, score = keyword_category(it)
        if cat:
            it["guess"] = cat
            scored.append((score, it))
    scored.sort(key=lambda x: (x[0], x[1]["published"]), reverse=True)
    return [it for _, it in scored[:MAX_CANDIDATES]]


# ---------------- Claude ----------------
TOOL = {
    "name": "publish_digest",
    "description": "提交今天挑選並翻譯好的新聞清單",
    "input_schema": {
        "type": "object",
        "properties": {
            "headline": {"type": "string", "description": "今日導讀：2-3 句繁體中文，點出今天最重要的事"},
            "stories": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "category": {"type": "string", "enum": list(config.MAX_PER_CATEGORY)},
                        "importance": {"type": "integer", "minimum": 1, "maximum": 5},
                        "zh_title": {"type": "string"},
                        "zh_summary": {"type": "string"},
                        "why_it_matters": {"type": "string"},
                        "tags": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["id", "category", "importance", "zh_title", "zh_summary", "why_it_matters", "tags"],
                },
            },
        },
        "required": ["headline", "stories"],
    },
}

PROMPT = """你是台灣科技媒體（風格類似「科技報橘 TechOrange」）的資深編輯。
以下是過去一天美國的英文新聞候選清單（JSON）。請：

1. 挑出對台灣科技業、投資人、創業者最重要的新聞，分三類：
   - ai_company：AI 大廠（OpenAI、Anthropic、Google、Meta、Microsoft、NVIDIA、Apple、Amazon、xAI 等）
   - ai_startup：AI 新創的融資、併購、估值、重要產品發表
   - finance：美股、聯準會、總經數據、科技股財報與市場動向
   每類最多：{limits}。寧缺勿濫，八卦、促銷、重複事件不要選；同一事件多家報導只選一則。
2. 每則用「台灣繁體中文」與台灣慣用詞（人工智慧/AI、軟體、資料、晶片、新創、融資、伺服器、網路、影片），寫：
   - zh_title：吸引人但不誇大的中文標題（30 字內）
   - zh_summary：2-3 句中文重點摘要，用你自己的話改寫，不要逐句翻譯原文
   - why_it_matters：1 句「為什麼重要」，可連結到台灣產業（如台積電、供應鏈、台股）但不要硬湊
   - tags：2-4 個中文或英文標籤（公司名、主題）
   - importance：1-5，5 最重要
   人名、公司名、產品名保留英文原文（例如 Sam Altman、Claude、Gemini）。金額換算成「億美元」等中文單位。
3. 寫一段 headline 今日導讀。

只能根據候選清單提供的資訊撰寫，不要捏造數字或細節。完成後呼叫 publish_digest。

候選新聞：
{candidates}
"""


def curate_with_claude(cands: list[dict]) -> dict:
    import anthropic

    client = anthropic.Anthropic()
    slim = [{"id": c["id"], "source": c["source"], "title": c["title"],
             "summary": c["summary"][:400], "published": c["published"][:16]} for c in cands]
    msg = client.messages.create(
        model=config.CLAUDE_MODEL,
        max_tokens=8000,
        tools=[TOOL],
        tool_choice={"type": "tool", "name": "publish_digest"},
        messages=[{"role": "user", "content": PROMPT.format(
            limits=json.dumps(config.MAX_PER_CATEGORY),
            candidates=json.dumps(slim, ensure_ascii=False))}],
    )
    result = next(b.input for b in msg.content if b.type == "tool_use")
    by_id = {c["id"]: c for c in cands}
    stories = []
    for s in result.get("stories", []):
        src = by_id.get(s.get("id"))
        if not src:
            continue  # 模型給了不存在的 id，丟掉
        stories.append({**s, "title": src["title"], "url": src["url"],
                        "source": src["source"], "published": src["published"]})
    return {"headline": result.get("headline", ""), "stories": _cap(stories), "engine": config.CLAUDE_MODEL}


# ---------------- 免費備案 ----------------
def curate_fallback(cands: list[dict]) -> dict:
    try:
        from deep_translator import GoogleTranslator
        tr = GoogleTranslator(source="en", target="zh-TW")
        translate = lambda s: tr.translate(s) if s else ""
    except Exception as exc:
        print(f"  [翻譯不可用] {exc}，保留英文")
        translate = lambda s: s
    stories = []
    for c in cands:
        cat = c["guess"]
        if sum(1 for s in stories if s["category"] == cat) >= config.MAX_PER_CATEGORY[cat]:
            continue
        try:
            zh_title, zh_summary = translate(c["title"]), translate(c["summary"][:300])
        except Exception:
            zh_title, zh_summary = c["title"], c["summary"][:300]
        stories.append({**c, "category": cat, "importance": 3, "zh_title": zh_title,
                        "zh_summary": zh_summary, "why_it_matters": "", "tags": []})
    return {"headline": "", "stories": stories, "engine": "keyword + Google Translate"}


def _cap(stories: list[dict]) -> list[dict]:
    stories.sort(key=lambda s: -s.get("importance", 0))
    out, count = [], {}
    for s in stories:
        c = s["category"]
        if count.get(c, 0) < config.MAX_PER_CATEGORY.get(c, 0):
            out.append(s)
            count[c] = count.get(c, 0) + 1
    return out


def curate(items: list[dict]) -> dict:
    cands = prefilter(items)
    print(f"關鍵字預篩後 {len(cands)} 則候選")
    if not cands:
        return {"headline": "", "stories": [], "engine": "none"}
    if os.getenv("ANTHROPIC_API_KEY"):
        try:
            return curate_with_claude(cands)
        except Exception as exc:
            print(f"  [Claude 失敗，改用備案] {exc}")
    return curate_fallback(cands)
