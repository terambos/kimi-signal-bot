# -*- coding: utf-8 -*-
"""
Bybit PUBLIC veri katmani - API key GEREKMEZ.
Yerel bilgisayarda calisir, IP engeli yoktur.
"""
import time
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED

import requests
import pandas as pd

from config import BYBIT_BASE, REQUEST_SLEEP, MAX_WORKERS

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "Mozilla/5.0"})


def _get(path: str, params: dict) -> dict:
    for attempt in range(3):
        try:
            r = SESSION.get(BYBIT_BASE + path, params=params, timeout=(5, 10))
            js = r.json()
            if js.get("retCode") == 0:
                return js
            
            # HATA AYIKLAMA: Bybit neden reddettigini ekrana yazdir
            print(f"[BYBIT REDDETTI] {params.get('symbol', '?')} | Kod: {js.get('retCode')} | Mesaj: {js.get('retMsg')}")
            time.sleep(1.0)
        except Exception as e:
            print(f"[BAGLANTI HATASI] {params.get('symbol', '?')} | {e}")
            time.sleep(1.0)
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
    return df.sort_values("start").set_index("start")


def get_open_interest(symbol: str, interval: str = "15", limit: int = 30) -> pd.DataFrame:
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
    return df.sort_values("timestamp").set_index("timestamp")[["openInterest"]]


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


def fetch_all(symbol: str, tfs: tuple = ("15", "60", "240"), ticker_info: dict | None = None) -> dict:
    out = {"symbol": symbol}
    for tf in tfs:
        out[f"df_{tf}"] = get_klines(symbol, tf, limit=200)
        time.sleep(REQUEST_SLEEP)
    if ticker_info is not None:
        out.update(ticker_info.get(symbol, {}))
    else:
        out.update(get_ticker(symbol))
    time.sleep(REQUEST_SLEEP)
    out["oi_df"] = get_open_interest(symbol, interval="15", limit=30)
    return out


def fetch_all_parallel(symbols: list, tfs: tuple = ("15", "60", "240"),
                       ticker_info: dict | None = None,
                       max_workers: int = MAX_WORKERS) -> dict:
    results = {}
    ex = ThreadPoolExecutor(max_workers=max_workers)
    futs = {ex.submit(fetch_all, s, tfs, ticker_info): s for s in symbols}

    # Sure 300 saniyeye cikarildi
    done, not_done = wait(futs, timeout=300, return_when=FIRST_COMPLETED)

    if not_done:
        print(f"[KRITIK TIMEOUT] {len(not_done)} coin 300 saniyede cekilemedi, atlaniyor.")

    for fut in done:
        sym = futs[fut]
        try:
            results[sym] = fut.result(timeout=1)
        except Exception as e:
            print(f"[VERI HATASI] {sym}: {e}")
            results[sym] = None

    for fut in not_done:
        fut.cancel()
    ex.shutdown(wait=False, cancel_futures=True)

    for s in symbols:
        if s not in results:
            results[s] = None
    return results
