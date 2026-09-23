# -*- coding: utf-8 -*-
"""
Bybit PUBLIC veri katmani - API key GEREKMEZ.
Kline + Funding + Open Interest ucretsiz public endpoint'lerden alinir.
"""
import time
import requests
import pandas as pd

from config import BYBIT_BASE, REQUEST_SLEEP

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "kripto-sinyal-botu/1.0"})


def _get(path: str, params: dict) -> dict:
    for attempt in range(3):
        try:
            r = SESSION.get(BYBIT_BASE + path, params=params, timeout=15)
            js = r.json()
            if js.get("retCode") == 0:
                return js
            rc = js.get("retCode")
            if rc in (10006, 10018):   # rate limit - daha uzun bekle
                time.sleep(4.0 * (attempt + 1))
            else:
                time.sleep(1.0 * (attempt + 1))
        except Exception:
            time.sleep(1.5 * (attempt + 1))
    return {"retCode": -1, "result": {}}


def get_klines(symbol: str, interval: str, limit: int = 300) -> pd.DataFrame:
    """Bybit kline; limit > 1000 ise geriye dogru sayfalayarak ceker."""
    rows = []
    end = None
    remaining = limit
    while remaining > 0:
        params = {"category": "linear", "symbol": symbol,
                  "interval": interval, "limit": min(remaining, 1000)}
        if end is not None:
            params["end"] = end
        js = _get("/v5/market/kline", params)
        lst = js.get("result", {}).get("list", [])
        if not lst:
            break
        rows.extend(lst)
        remaining -= len(lst)
        oldest = int(lst[-1][0])      # liste yeniden eskiye sirali, son eleman en eski
        end = oldest - 1
        if len(lst) < min(remaining + len(lst), 1000):
            break
        time.sleep(REQUEST_SLEEP)
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows, columns=["start", "open", "high", "low", "close",
                                     "volume", "turnover"]).drop_duplicates(subset="start")
    df["start"] = pd.to_datetime(df["start"].astype("int64"), unit="ms", utc=True)
    for c in ["open", "high", "low", "close", "volume", "turnover"]:
        df[c] = df[c].astype(float)
    df = df.sort_values("start").set_index("start")
    return df


def get_ticker(symbol: str) -> dict:
    js = _get("/v5/market/tickers", {
        "category": "linear", "symbol": symbol,
    })
    lst = js.get("result", {}).get("list", [])
    if not lst:
        return {}
    t = lst[0]
    return {
        "funding": float(t.get("fundingRate", 0) or 0),
        "mark": float(t.get("markPrice", 0) or 0),
        "oi_now": float(t.get("openInterest", 0) or 0),
        "turnover24h": float(t.get("turnover24h", 0) or 0),
    }


def get_all_tickers() -> dict:
    """Tum linear coinlerin funding/mark/turnover verisini TEK istekle ceker.
    GitHub runner IP'leri paylasimli oldugundan rate-limit riskini azaltir."""
    js = _get("/v5/market/tickers", {"category": "linear"})
    out = {}
    for t in js.get("result", {}).get("list", []):
        sym = t.get("symbol")
        try:
            out[sym] = {
                "funding": float(t.get("fundingRate", 0) or 0),
                "mark": float(t.get("markPrice", 0) or 0),
                "turnover24h": float(t.get("turnover24h", 0) or 0),
            }
        except (TypeError, ValueError):
            continue
    return out


def get_oi_history(symbol: str) -> pd.DataFrame:
    """Saatlik acik pozisyon gecmisi (son ~1-2 gun)"""
    js = _get("/v5/market/open-interest", {
        "category": "linear", "symbol": symbol,
        "intervalTime": "1h", "limit": 24,
    })
    lst = js.get("result", {}).get("list", [])
    if not lst:
        return pd.DataFrame()
    df = pd.DataFrame(lst)
    df["timestamp"] = pd.to_datetime(df["timestamp"].astype("int64"), unit="ms", utc=True)
    df["openInterest"] = df["openInterest"].astype(float)
    df = df.sort_values("timestamp").set_index("timestamp")
    return df


def sleep_between():
    time.sleep(REQUEST_SLEEP)


def fetch_all(symbol: str, tfs: tuple = ("15", "60", "240"), ticker_info: dict | None = None) -> dict:
    """Bir coin icin butun zaman dilimlerini + funding/OI cek.
    ticker_info verilirse (get_all_tickers ciktisi) tek tek ticker istegi atmaz."""
    out = {"symbol": symbol}
    for tf in tfs:
        out[f"df_{tf}"] = get_klines(symbol, tf)
        sleep_between()
    if ticker_info is not None:
        out.update(ticker_info.get(symbol, {}))
    else:
        out.update(get_ticker(symbol))
    sleep_between()
    oi = get_oi_history(symbol)
    out["oi_df"] = oi
    sleep_between()
    return out
