# -*- coding: utf-8 -*-
import time
import requests
import pandas as pd
from config import BYBIT_BASE, REQUEST_SLEEP

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "Mozilla/5.0"})

BINANCE_BASE = "https://data-api.binance.vision"
OKX_BASE = "https://www.okx.com"

def _get_bybit(path: str, params: dict) -> dict:
    try:
        r = SESSION.get(BYBIT_BASE + path, params=params, timeout=(5, 10))
        js = r.json()
        if js.get("retCode") == 0:
            return js
    except Exception:
        pass
    return {"retCode": -1, "result": {}}

def _get_binance(path: str, params: dict):
    try:
        r = SESSION.get(BINANCE_BASE + path, params=params, timeout=(5, 10))
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return []

def _get_okx(path: str, params: dict):
    try:
        r = SESSION.get(OKX_BASE + path, params=params, timeout=(5, 10))
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return {}

def get_klines(symbol: str, interval: str, limit: int = 200) -> pd.DataFrame:
    js = _get_bybit("/v5/market/kline", {"category": "linear", "symbol": symbol, "interval": interval, "limit": limit})
    lst = js.get("result", {}).get("list", [])
    if lst:
        df = pd.DataFrame(lst, columns=["start", "open", "high", "low", "close", "volume", "turnover"])
        df["start"] = pd.to_datetime(df["start"].astype("int64"), unit="ms", utc=True)
        for c in ["open", "high", "low", "close", "volume", "turnover"]:
            df[c] = df[c].astype(float)
        return df.sort_values("start").set_index("start")

    print(f"[FALLBACK] {symbol} Bybit'ten cekilemedi, Binance'e geciliyor...")
    tf_map = {"15": "15m", "60": "1h", "240": "4h"}
    js = _get_binance("/api/v3/klines", {"symbol": symbol, "interval": tf_map.get(interval, interval), "limit": limit})
    if isinstance(js, list) and js:
        df = pd.DataFrame(js, columns=["start", "open", "high", "low", "close", "volume", "close_time", "qav", "trades", "tbb", "tbq", "ignore"])
        df["start"] = pd.to_datetime(df["start"].astype("int64"), unit="ms", utc=True)
        for c in ["open", "high", "low", "close", "volume"]:
            df[c] = df[c].astype(float)
        return df.sort_values("start").set_index("start")[["open", "high", "low", "close", "volume"]]

    print(f"[FALLBACK] {symbol} Binance'ten de cekilemedi, OKX'e geciliyor...")
    okx_tf = {"15": "15m", "60": "1H", "240": "4H"}.get(interval, "15m")
    okx_symbol = symbol.replace("USDT", "-USDT-SWAP")
    js = _get_okx("/api/v5/market/candles", {"instId": okx_symbol, "bar": okx_tf, "limit": limit})
    if js and js.get("code") == "0":
        lst = js.get("data", [])
        if lst:
            df = pd.DataFrame(lst, columns=["start", "open", "high", "low", "close", "volume", "volCcy", "volCcyQuote", "confirm"])
            df["start"] = pd.to_datetime(df["start"].astype("int64"), unit="ms", utc=True)
            for c in ["open", "high", "low", "close", "volume"]:
                df[c] = df[c].astype(float)
            return df.sort_values("start").set_index("start")[["open", "high", "low", "close", "volume"]]

    return pd.DataFrame()

def get_open_interest(symbol: str, interval: str = "15", limit: int = 30) -> pd.DataFrame:
    js = _get_bybit("/v5/market/open-interest", {"category": "linear", "symbol": symbol, "intervalTime": interval, "limit": limit})
    lst = js.get("result", {}).get("list", [])
    if not lst:
        return pd.DataFrame()
    df = pd.DataFrame(lst)
    df["timestamp"] = pd.to_datetime(df["timestamp"].astype("int64"), unit="ms", utc=True)
    df["openInterest"] = df["openInterest"].astype(float)
    return df.sort_values("timestamp").set_index("timestamp")[["openInterest"]]

def get_ticker(symbol: str) -> dict:
    js = _get_bybit("/v5/market/tickers", {"category": "linear", "symbol": symbol})
    lst = js.get("result", {}).get("list", [])
    if not lst:
        return {}
    t = lst[0]
    return {"funding": float(t.get("fundingRate", 0) or 0), "mark": float(t.get("markPrice", 0) or 0), "oi_now": float(t.get("openInterest", 0) or 0), "turnover24h": float(t.get("turnover24h", 0) or 0)}

def fetch_all_parallel(symbols: list, tfs: tuple = ("15", "60", "240"), ticker_info: dict | None = None, max_workers: int = 1) -> dict:
    results = {}
    for sym in symbols:
        try:
            out = {"symbol": sym}
            for tf in tfs:
                out[f"df_{tf}"] = get_klines(sym, tf, limit=200)
                time.sleep(0.2)
            out.update(get_ticker(sym))
            time.sleep(0.2)
            out["oi_df"] = get_open_interest(sym, interval="15", limit=30)
            results[sym] = out
        except Exception as e:
            print(f"[VERI HATASI] {sym}: {e}")
            results[sym] = None
    return results
