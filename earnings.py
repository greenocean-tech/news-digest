"""本週 S&P 100 財報行事曆（每週一顯示在日報最上方）。

資料來源：
  1. Nasdaq 財報行事曆（免費、不需要 key）
  2. 備案：Finnhub（有設定 FINNHUB_API_KEY 才會用；免費註冊只要 email）
成分股：每次從 Wikipedia 抓最新的 S&P 100 名單，抓不到就用內建名單。

測試：python earnings.py --week 2026-10-26
"""
import html
import os
import re
import sys
from datetime import date, datetime, timedelta

import requests

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36",
      "Accept": "application/json, text/plain, */*", "Accept-Language": "en-US,en;q=0.9",
      "Origin": "https://www.nasdaq.com", "Referer": "https://www.nasdaq.com/"}

# 2026-10 的 S&P 100 名單（Wikipedia 抓不到時使用）
SP100_FALLBACK = (
    "AAPL ABBV ABT ACN ADBE AMAT AMD AMGN AMT AMZN ANET AVGO AXP BA BAC BKNG BLK BMY BNY BRK.B "
    "C CAT CMCSA COF COP COST CRM CSCO CVS CVX DE DELL DHR DIS DUK EMR FDX GD GE GEV GILD GM GOOG "
    "GOOGL GS HD IBM INTC INTU ISRG JNJ JPM KO LIN LLY LMT LOW LRCX MA MCD MDLZ MDT META MMM MO MRK "
    "MS MSFT MU NEE NFLX NOW NVDA ORCL PANW PEP PFE PG PLTR PM QCOM RTX SBUX SCHW SNDK SO T TMO TMUS "
    "TSLA TXN UBER UNH UNP UPS USB V VZ WFC WMT XOM"
).split()

WEEKDAY = "一二三四五六日"
TIME_LABEL = {"time-pre-market": "盤前", "time-after-hours": "盤後", "bmo": "盤前", "amc": "盤後"}


def norm(sym: str) -> str:
    return re.sub(r"[./-]", "", (sym or "").upper().strip())


def sp100() -> dict[str, str]:
    """回傳 {正規化代號: 顯示代號}。"""
    try:
        r = requests.get("https://en.wikipedia.org/wiki/S%26P_100", headers={"User-Agent": UA["User-Agent"]},
                         timeout=20)
        r.raise_for_status()
        m = re.search(r'<table[^>]*id="constituents".*?</table>', r.text, re.S)
        tickers = re.findall(r"<tr>\s*<td>\s*(?:<a[^>]*>)?([A-Z][A-Z.]{0,5})(?:</a>)?\s*</td>", m.group(0)) if m else []
        if 95 <= len(tickers) <= 110:
            return {norm(t): t for t in tickers}
        print(f"  [S&P 100] Wikipedia 解析到 {len(tickers)} 檔，改用內建名單")
    except Exception as exc:
        print(f"  [S&P 100] Wikipedia 抓取失敗（{type(exc).__name__}），改用內建名單")
    return {norm(t): t for t in SP100_FALLBACK}


def week_of(day: date) -> list[date]:
    monday = day - timedelta(days=day.weekday())
    return [monday + timedelta(days=i) for i in range(5)]


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
    """回傳本週（週一到週五）S&P 100 財報；兩個來源都失敗就回傳 None。"""
    days = week_of(day)
    members = sp100()
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
    seen, uniq = set(), []
    for it in sorted(items, key=lambda x: (x["date"], x["time"] != "盤前", -x["market_cap"])):
        k = (it["date"], it["symbol"])
        if k not in seen:
            seen.add(k)
            uniq.append(it)
    grouped = []
    for d in days:
        its = [i for i in uniq if i["date"] == d.isoformat()]
        if its:
            grouped.append({"date": d.isoformat(), "label": f"{d.month}/{d.day}（{WEEKDAY[d.weekday()]}）", "items": its})
    return {"week_start": days[0].isoformat(), "week_end": days[-1].isoformat(), "source": source,
            "count": len(uniq), "days": grouped}


def headline(cal: dict) -> str:
    s, e = (datetime.strptime(cal[k], "%Y-%m-%d") for k in ("week_start", "week_end"))
    return f"本週 S&P 100 財報行事曆（{s.month}/{s.day}–{e.month}/{e.day}，美東時間）"


if __name__ == "__main__":
    arg = sys.argv[sys.argv.index("--week") + 1] if "--week" in sys.argv else date.today().isoformat()
    cal = weekly_calendar(date.fromisoformat(arg))
    if not cal:
        sys.exit(1)
    print(headline(cal), f"來源 {cal['source']}，共 {cal['count']} 檔")
    for d in cal["days"]:
        line = "、".join(f"{i['symbol']}（{i['time']}）" for i in d["items"])
        print(f"{d['label']}：{line}")
        print(f"::notice title=財報 {d['label']}::{line}")
