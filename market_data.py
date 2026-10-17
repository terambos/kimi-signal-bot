# -*- coding: utf-8 -*-
import time
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
import requests
import pandas as pd
from config import BYBIT_BASE, REQUEST_SLEEP, MAX_WORKERS

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "Mozilla/5.0"})

def _get(path: str, params: dict):
    for attempt in range(3):
        try:
            r = SESSION.get(BYBIT_BASE + path, params=params, timeout=(5, 10))
            if r.status_code == 200:
                return r.json()
            time.sleep(1.0)
        except Exception:
            time.sleep(1.0)
    return []

def get_klines(symbol: str, interval: str, limit: int = 200) -> pd.DataFrame:
    tf_map = {"15": "15m", "60": "1h", "240": "4h"}
    bnb_tf = tf_map.get(interval, interval)
    
    # Binance 1000PEPE yerine 1000PEPEUSDT (USDT paritesi) kullanir
    bnb_symbol = symbol 
    
    js = _get("/api/v3/klines", {
        "symbol": bnb_symbol, "interval": bnb_tf, "limit": min(limit, 1000)
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

def get_open_interest(symbol: str) -> pd.DataFrame:
    return pd.DataFrame()

def get_ticker(symbol: str) -> dict:
    js = _get("/api/v3/ticker/24hr", {"symbol": symbol})
    if not isinstance(js, dict):
        return {}
    return {
        "funding": 0.0,
        "mark": float(js.get("lastPrice", 0) or 0),
        "oi_now": 0.0,
        "turnover24h": float(js.get("quoteVolume", 0) or 0),
    }

def fetch_all(symbol: str, tfs: tuple = ("15", "60", "240"), ticker_info: dict | None = None) -> dict:
    out = {"symbol": symbol}
    for tf in tfs:
        out[f"df_{tf}"] = get_klines(symbol, tf, limit=200)
        time.sleep(REQUEST_SLEEP)
    out.update(get_ticker(symbol))
    out["oi_df"] = None
    return out

def fetch_all_parallel(symbols: list, tfs: tuple = ("15", "60", "240"), ticker_info: dict | None = None, max_workers: int = MAX_WORKERS) -> dict:
    results = {}
    ex = ThreadPoolExecutor(max_workers=max_workers)
    futs = {ex.submit(fetch_all, s, tfs, ticker_info): s for s in symbols}

    done, not_done = wait(futs, timeout=300, return_when=FIRST_COMPLETED)

    if not_done:
        print(f"[KRITIK TIMEOUT] {len(not_done)} coin 300 saniyede cekilemedi.")

    for fut in done:
        sym = futs[fut]
        try:
            results[sym] = fut.result(timeout=1)
        except Exception as e:
            print(f"[VERI HATASI] {sym}: {e}")
            results[sym] = None

    for s in symbols:
        if s not in results:
            results[s] = None
    return results
