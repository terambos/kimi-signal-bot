# -*- coding: utf-8 -*-
"""
Binance PUBLIC veri katmani - API key GEREKMEZ.
Kline Binance aynasindan (data-api.binance.vision) cekilir.
GitHub Actions IP engeli yoktur, proxy gerekmez.
"""
import time
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED

import requests
import pandas as pd

from config import BYBIT_BASE, REQUEST_SLEEP, MAX_WORKERS

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
})


def _get(path: str, params: dict):
    for attempt in range(3):
        try:
            r = SESSION.get(BYBIT_BASE + path, params=params, timeout=(5, 8))
            if r.status_code == 200:
                return r.json()
            time.sleep(1.0 * (attempt + 1))
        except Exception:
            time.sleep(1.0 * (attempt + 1))
    return []


def get_klines(symbol: str, interval: str, limit: int = 200) -> pd.DataFrame:
    tf_map = {"15": "15m", "60": "1h", "240": "4h"}
    bnb_tf = tf_map.get(interval, interval)

    # Binance'in 1000 limiti var, biz 200 cekiyoruz
    js = _get("/api/v3/klines", {
        "symbol": symbol, "interval": bnb_tf, "limit": min(limit, 1000)
    })
    lst = js if isinstance(js, list) else []
    if not lst:
        return pd.DataFrame()

    df = pd.DataFrame(lst, columns=["start", "open", "high", "low", "close",
                                     "volume", "close_time", "qav", "trades",
                                     "tbb", "tbq", "ignore"])
    df["start"] = pd.to_datetime(df["start"].astype("int64"), unit="ms", utc=True)
    for c in ["open", "high", "low", "close", "volume"]:
        df[c] = df[c].astype(float)
    return df.sort_values("start").set_index("start")[["open", "high", "low", "close", "volume"]]


def get_open_interest(symbol: str, interval: str = "15", limit: int = 30) -> pd.DataFrame:
    # Binance OI su an devre disi (baska endpoint gerekir)
    return pd.DataFrame()


def get_ticker(symbol: str) -> dict:
    js = _get("/api/v3/ticker/24hr", {"symbol": symbol})
    if not isinstance(js, dict):
        return {}
    return {
        "funding": 0.0,   # Binance spot funding yok
        "mark": float(js.get("lastPrice", 0) or 0),
        "oi_now": 0.0,
        "turnover24h": float(js.get("quoteVolume", 0) or 0),
    }


def sleep_between():
    time.sleep(REQUEST_SLEEP)


def fetch_all(symbol: str, tfs: tuple = ("15", "60", "240"),
              ticker_info: dict | None = None) -> dict:
    out = {"symbol": symbol}
    for tf in tfs:
        out[f"df_{tf}"] = get_klines(symbol, tf, limit=200)
        sleep_between()
    if ticker_info is not None:
        out.update(ticker_info.get(symbol, {}))
    else:
        out.update(get_ticker(symbol))
    sleep_between()
    out["oi_df"] = None
    return out


def fetch_all_parallel(symbols: list, tfs: tuple = ("15", "60", "240"),
                       ticker_info: dict | None = None,
                       max_workers: int = MAX_WORKERS) -> dict:
    results = {}
    ex = ThreadPoolExecutor(max_workers=max_workers)
    futs = {ex.submit(fetch_all, s, tfs, ticker_info): s for s in symbols}

    done, not_done = wait(futs, timeout=60, return_when=FIRST_COMPLETED)

    if not_done:
        print(f"[KRITIK TIMEOUT] {len(not_done)} coin 60 saniyede cekilemedi, atlaniyor.")

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
