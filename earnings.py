"""追蹤股財報行事曆：本週＋下週（每週一顯示在日報最上方）。

追蹤清單在 config.py 的 EARNINGS_WATCHLIST。

資料來源：
  1. Nasdaq 財報行事曆（免費、不需要 key）
  2. 備案：Finnhub（有設定 FINNHUB_API_KEY 才會用；免費註冊只要 email）

測試：python earnings.py --week 2026-10-26
"""
import html
import os
import re
import sys
from datetime import date, datetime, timedelta

import requests

import config

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36",
      "Accept": "application/json, text/plain, */*", "Accept-Language": "en-US,en;q=0.9",
      "Origin": "https://www.nasdaq.com", "Referer": "https://www.nasdaq.com/"}

WEEKDAY = "一二三四五六日"
TIME_LABEL = {"time-pre-market": "盤前", "time-after-hours": "盤後", "bmo": "盤前", "amc": "盤後"}


def norm(sym: str) -> str:
    return re.sub(r"[./-]", "", (sym or "").upper().strip())


def watchlist() -> dict[str, str]:
    """回傳 {正規化代號: 顯示代號}。"""
    return {norm(t): t for t, _ in config.EARNINGS_WATCHLIST}


NAMES = {t: n for t, n in config.EARNINGS_WATCHLIST}


def week_of(day: date) -> list[date]:
    """本週一到下週五的 10 個交易日。"""
    monday = day - timedelta(days=day.weekday())
    return [monday + timedelta(days=w * 7 + i) for w in range(2) for i in range(5)]


def _money(v) -> float:
    try:
        return float(re.sub(r"[^\d.]", "", str(v)) or 0)
    except ValueError:
        return 0.0


def from_nasdaq(days: list[date], members: dict[str, str]) -> list[dict]:
    out = []
    for d in days:
        r = requests.get("https://api.nasdaq.com/api/calendar/earnings", params={"date": d.isoformat()},
                         headers=UA, timeout=25)
        r.raise_for_status()
        rows = ((r.json().get("data") or {}).get("rows")) or []
        for row in rows:
            key = norm(row.get("symbol"))
            if key in members:
                out.append({"date": d.isoformat(), "symbol": members[key],
                            "name": html.unescape(row.get("name") or ""),
                            "time": TIME_LABEL.get(row.get("time"), "時間未定"),
                            "eps_forecast": row.get("epsForecast") or "",
                            "market_cap": _money(row.get("marketCap"))})
    return out


def from_finnhub(days: list[date], members: dict[str, str]) -> list[dict]:
    key = os.getenv("FINNHUB_API_KEY")
    if not key:
        raise RuntimeError("沒有 FINNHUB_API_KEY")
    r = requests.get("https://finnhub.io/api/v1/calendar/earnings",
                     params={"from": days[0].isoformat(), "to": days[-1].isoformat(), "token": key}, timeout=25)
    r.raise_for_status()
    out = []
    for row in r.json().get("earningsCalendar") or []:
        k = norm(row.get("symbol"))
        if k in members:
            eps = row.get("epsEstimate")
            out.append({"date": row.get("date"), "symbol": members[k], "name": "",
                        "time": TIME_LABEL.get(row.get("hour"), "時間未定"),
                        "eps_forecast": f"${eps:.2f}" if isinstance(eps, (int, float)) else "", "market_cap": 0})
    return out


def weekly_calendar(day: date) -> dict | None:
    """回傳本週＋下週追蹤股財報；兩個來源都失敗就回傳 None。"""
    days = week_of(day)
    members = watchlist()
    items, source, errors = None, "", []
    for name, fn in (("Nasdaq", from_nasdaq), ("Finnhub", from_finnhub)):
        try:
            items, source = fn(days, members), name
            break
        except Exception as exc:
            errors.append(f"{name}: {type(exc).__name__}: {str(exc)[:120]}")
    if items is None:
        for e in errors:
            print(f"::warning title=財報行事曆抓取失敗::{e}")
        return None
    for it in items:
        it["zh_name"] = NAMES.get(it["symbol"], "")
    seen, uniq = set(), []
    for it in sorted(items, key=lambda x: (x["date"], x["time"] != "盤前", -x["market_cap"])):
        k = (it["date"], it["symbol"])
        if k not in seen:
            seen.add(k)
            uniq.append(it)
    grouped = []
    for idx, d in enumerate(days):
        its = [i for i in uniq if i["date"] == d.isoformat()]
        if its:
            grouped.append({"date": d.isoformat(), "week": "本週" if idx < 5 else "下週",
                            "label": f"{d.month}/{d.day}（{WEEKDAY[d.weekday()]}）", "items": its})
    reported = {i["symbol"] for i in uniq}
    return {"week_start": days[0].isoformat(), "week_end": days[-1].isoformat(), "source": source,
            "count": len(uniq), "days": grouped,
            "none": [t for t, _ in config.EARNINGS_WATCHLIST if t not in reported]}


def headline(cal: dict) -> str:
    s, e = (datetime.strptime(cal[k], "%Y-%m-%d") for k in ("week_start", "week_end"))
    return f"本週＋下週 追蹤股財報（{s.month}/{s.day}–{e.month}/{e.day}，美東時間）"


def item_text(i: dict) -> str:
    name = f" {i['zh_name']}" if i.get("zh_name") and i["zh_name"] != i["symbol"] else ""
    return f"{i['symbol']}{name}（{i['time']}）"


if __name__ == "__main__":
    arg = sys.argv[sys.argv.index("--week") + 1] if "--week" in sys.argv else date.today().isoformat()
    cal = weekly_calendar(date.fromisoformat(arg))
    if not cal:
        sys.exit(1)
    print(headline(cal), f"來源 {cal['source']}，共 {cal['count']} 檔；兩週內沒有財報：{'、'.join(cal['none']) or '無'}")
    for d in cal["days"]:
        line = "、".join(item_text(i) for i in d["items"])
        print(f"{d['week']} {d['label']}：{line}")
        print(f"::notice title=財報 {d['label']}::{line}")
