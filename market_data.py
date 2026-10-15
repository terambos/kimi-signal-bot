# -*- coding: utf-8 -*-
"""
Bybit PUBLIC veri katmani - API key GEREKMEZ.
Kline + Funding + Open Interest ucretsiz public endpoint'lerden alinir.
Paralel sembol cekimi icin ThreadPoolExecutor kullanilir.
"""
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
import pandas as pd

from config import BYBIT_BASE, REQUEST_SLEEP, MAX_WORKERS

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "kripto-sinyal-botu/1.0"})


def _get(path: str, params: dict) -> dict:
    for attempt in range(3):
        try:
            r = SESSION.get(BYBIT_BASE + path, params=params, timeout=(10, 20))
            js = r.json()
            if js.get("retCode") == 0:
                return js
            rc = js.get("retCode")
            if rc in (10006, 10018):
                time.sleep(4.0 * (attempt + 1))
            else:
                time.sleep(1.0 * (attempt + 1))
        except Exception:
            time.sleep(1.5 * (attempt + 1))
    return {"retCode": -1, "result": {}}


def get_klines(symbol: str, interval: str, limit: int = 200) -> pd.DataFrame:
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
        oldest = int(lst[-1][0])
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


def get_open_interest(symbol: str, interval: str = "15", limit: int = 30) -> pd.DataFrame:
    """
    Bybit v5 open-interest endpoint'i. intervalTime: 5m, 15m, 30m, 1h, 4h, 1d
    Donen df: index=timestamp, kolon=openInterest
    """
    js = _get("/v5/market/open-interest", {
        "category": "linear", "symbol": symbol,
        "intervalTime": interval, "limit": limit,
    })
    lst = js.get("result", {}).get("list", [])
    if not lst:
        return pd.DataFrame()
    df = pd.DataFrame(lst)
    df["timestamp"] = pd.to_datetime(df["timestamp"].astype("int64"), unit="ms", utc=True)
    df["openInterest"] = df["openInterest"].astype(float)
    df = df.sort_values("timestamp").set_index("timestamp")
    return df[["openInterest"]]


def get_ticker(symbol: str) -> dict:
    js = _get("/v5/market/tickers", {"category": "linear", "symbol": symbol})
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


def sleep_between():
    time.sleep(REQUEST_SLEEP)


def fetch_all(symbol: str, tfs: tuple = ("15", "60", "240"),
              ticker_info: dict | None = None) -> dict:
    """Tek sembol icin tum zaman dilimleri + funding + OI cek."""
    out = {"symbol": symbol}
    for tf in tfs:
        out[f"df_{tf}"] = get_klines(symbol, tf, limit=200)
        sleep_between()
    if ticker_info is not None:
        out.update(ticker_info.get(symbol, {}))
    else:
        out.update(get_ticker(symbol))
    sleep_between()
    # OI: 15dk periyotta son 30 nokta (1s degisim icin yeter)
    out["oi_df"] = get_open_interest(symbol, interval="15", limit=30)
    return out


def fetch_all_parallel(symbols: list, tfs: tuple = ("15", "60", "240"),
                       ticker_info: dict | None = None,
                       max_workers: int = MAX_WORKERS) -> dict:
    """
    Sembolleri paralel cek. Donen: {symbol: data_dict}
    Tek tek hata olsa bile digerlerini etkilemez.
    """
    results = {}
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futs = {ex.submit(fetch_all, s, tfs, ticker_info): s for s in symbols}
        for fut in as_completed(futs):
            sym = futs[fut]
            try:
                results[sym] = fut.result()
            except Exception as e:
                print("[VERI HATASI]", sym, e)
                results[sym] = None
    return results
