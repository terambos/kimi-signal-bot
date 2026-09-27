# -*- coding: utf-8 -*-
"""
Bybit PUBLIC veri katmani - API key GEREKMEZ.
Proxy uzerinden calisir (GitHub Actions IP engeli icin).
"""
import threading
import time
import warnings
import requests
import pandas as pd
import urllib3

# Proxy MITM sertifikasi icin uyari bastir
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from config import BYBIT_BASE, REQUEST_SLEEP

# Her thread kendi oturumunu kullanir (paralel tarama icin thread-safe)
_local = threading.local()

def _session() -> requests.Session:
    s = getattr(_local, "s", None)
    if s is None:
        s = requests.Session()
        s.headers.update({"User-Agent": "kripto-sinyal-botu/1.0"})
        s.verify = False   # proxy MITM sertifikasi - dogrulama kapali
        _local.s = s
    return s

def _get(path: str, params: dict, max_retry: int = 5) -> dict:
    """Bybit istegi. Rate-limit yerse 5 kez dener (5s,10s,15s,20s,25s)."""
    ses = _session()
    for attempt in range(max_retry):
        try:
            r = ses.get(BYBIT_BASE + path, params=params, timeout=20)
            js = r.json()
            if js.get("retCode") == 0:
                return js
            rc = js.get("retCode")
            if rc in (10006, 10018):   # rate limit
                wait = 5.0 * (attempt + 1)
                print("[RATE-LIMIT] %s rc=%s, %.0fs bekleniyor..." % (path, rc, wait), flush=True)
                time.sleep(wait)
            else:
                time.sleep(2.0 * (attempt + 1))
        except Exception as e:
            print("[HATA] %s: %s" % (path, e), flush=True)
            time.sleep(2.0 * (attempt + 1))
    print("[BASARISIZ] %s - %d deneme sonrasi bos" % (path, max_retry), flush=True)
    return {"retCode": -1, "result": {}}

def get_klines(symbol: str, interval: str, limit: int = 300) -> pd.DataFrame:
    """Bybit kline. Bos donerse 3 kez tekrar dener (rate-limit savunmasi)."""
    rows = []
    for retry in range(3):
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
        if rows:
            break
        print("[KLINE RETRY] %s %s bos, tekrar (%d/3)" % (symbol, interval, retry + 1), flush=True)
        time.sleep(5.0 * (retry + 1))
    if not rows:
        print("[KLINE BASARISIZ] %s %s" % (symbol, interval), flush=True)
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
    NOT: Proxy/rate-limit icin kullanilmiyor."""
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

def fetch_all_parallel(symbols, tfs=("15", "60", "240"), max_workers: int = 2) -> dict:
    """Butun coinleri paralel tarar. get_all_tickers YOK - her coin kendi
    ticker'ini ayri ceker (proxy icin daha hafif)."""
    from concurrent.futures import ThreadPoolExecutor

    def _one(sym):
        try:
            return sym, fetch_all(sym, tfs=tfs, ticker_info=None)
        except Exception as e:
            return sym, {"df_15": None, "error": str(e)}

    results = {}
    done = 0
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        for sym, data in ex.map(_one, symbols):
            results[sym] = data
            done += 1
            print("  [%d/%d] %s OK" % (done, len(symbols), sym), flush=True)
    return results

def fetch_all(symbol: str, tfs: tuple = ("15", "60", "240"), ticker_info: dict | None = None) -> dict:
    """Bir coin icin butun zaman dilimlerini + funding/OI cek."""
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
