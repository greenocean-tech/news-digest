"""每日主程式：抓新聞 → 挑重點翻譯 → 存 data/ → 產生 docs/ 網站。

本機執行：python digest.py
環境變數：ANTHROPIC_API_KEY（建議）、NEWSAPI_KEY（選用），可寫在 .env 檔
"""
import json
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import build_site
import curate
import sources

ROOT = Path(__file__).parent
DATA = ROOT / "data"
SEEN = DATA / "seen.json"


def main() -> None:
    DATA.mkdir(exist_ok=True)
    today = datetime.now(ZoneInfo("Asia/Taipei")).strftime("%Y-%m-%d")
    seen = json.loads(SEEN.read_text("utf-8")) if SEEN.exists() else []

    print(f"== {today} 抓取新聞 ==")
    items = sources.fetch_all(set(seen))

    print("== 挑選與翻譯 ==")
    result = curate.curate(items)

    # 同一天跑第二次：保留早上已選的新聞，再合併新的
    today_file = DATA / f"{today}.json"
    if today_file.exists():
        old = json.loads(today_file.read_text("utf-8"))
        kept_ids = {s["id"] for s in result["stories"]}
        result["stories"] = curate._cap(result["stories"] + [s for s in old["stories"] if s["id"] not in kept_ids])
        result["headline"] = result["headline"] or old.get("headline", "")

    # 之前沒翻成功的（標題還是英文），再翻一次
    for s in result["stories"]:
        if s.get("zh_title") == s.get("title"):
            s["zh_title"] = curate.translate(s["title"])
            if s.get("zh_summary") and s["zh_summary"] == s.get("summary", "")[:300]:
                s["zh_summary"] = curate.translate(s["zh_summary"])
    result.setdefault("translate_errors", curate.ERRORS[:10])

    # 每週一：本週 S&P 100 財報行事曆
    now_tw = datetime.now(ZoneInfo("Asia/Taipei"))
    if now_tw.weekday() == 0 or os.getenv("FORCE_EARNINGS") == "1":
        import earnings
        cal = earnings.weekly_calendar(now_tw.date())
        if cal:
            result["earnings"] = cal
            print(f"本週財報：{cal['count']} 檔（{cal['source']}）")
    if today_file.exists() and "earnings" not in result:
        old_earn = json.loads(today_file.read_text("utf-8")).get("earnings")
        if old_earn:
            result["earnings"] = old_earn

    digest = {"date": today, "generated_at": datetime.now(ZoneInfo("Asia/Taipei")).isoformat(), **result}
    (DATA / f"{today}.json").write_text(json.dumps(digest, ensure_ascii=False, indent=2), "utf-8")
    print(f"今日選出 {len(result['stories'])} 則（{result['engine']}）")

    # 記住已看過的新聞，避免明天重複（只留最近 3000 筆）
    seen = (seen + [it["id"] for it in items])[-3000:]
    SEEN.write_text(json.dumps(seen), "utf-8")

    build_site.build()

    try:
        import card
        if digest["stories"]:
            print(f"IG 圖卡：{card.make_card(digest)}")
    except Exception as exc:  # 圖卡失敗不影響日報
        print(f"::warning title=IG 圖卡產生失敗::{exc}")


if __name__ == "__main__":
    main()
