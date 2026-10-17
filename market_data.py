# -*- coding: utf-8 -*-
import time
import random
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
import pandas as pd
import yfinance as yf

from config import REQUEST_SLEEP, MAX_WORKERS

YF_TICKER_OVERRIDES = {
    "1000PEPE": "PEPE24478-USD",
    "HYPE": "HYPE32196-USD",
    "APT": "APT21794-USD", 
    "TAO": "TAO22974-USD",
    "SUI": "SUI20947-USD",
    "RNDR": "RNDR-USD",
    "FET": "FET-USD"
}

def get_klines(symbol: str, interval: str, limit: int = 200) -> pd.DataFrame:
    base = symbol.replace("USDT", "")
    ticker_symbol = YF_TICKER_OVERRIDES.get(base, base + "-USD")
    
    tf_map = {"15": "15m", "60": "1h", "240": "4h"}
    yf_interval = tf_map.get(interval, "15m")
    
    if yf_interval == "15m":
        period = "60d"
    else:
        period = "730d"
    
    try:
        time.sleep(random.uniform(0.5, 1.0)) # Rastgele bekleme
        ticker = yf.Ticker(ticker_symbol)
        df = ticker.history(period=period, interval=yf_interval)
        if df.empty:
            return pd.DataFrame()
        
        df = df.rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"})
        if df.index.tz is None:
            df.index = df.index.tz_localize('UTC')
        else:
            df.index = df.index.tz_convert('UTC')
        df.index.name = "start"
        return df[["open", "high", "low", "close", "volume"]].tail(limit)
    except Exception:
        return pd.DataFrame()

def get_open_interest(symbol: str) -> pd.DataFrame:
    return pd.DataFrame()

def get_ticker(symbol: str) -> dict:
    return {"funding": 0.0, "mark": 0.0, "oi_now": 0.0, "turnover24h": 0.0}

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
    ex = ThreadPoolExecutor(max_workers=max_workers) # Ayni anda 3 istek
    futs = {ex.submit(fetch_all, s, tfs, ticker_info): s for s in symbols}

    # 10 dakika boyunca bekleyecegiz (kesinlikle yetecek)
    done, not_done = wait(futs, timeout=600, return_when=FIRST_COMPLETED)

    if not_done:
        print(f"[KRITIK TIMEOUT] {len(not_done)} coin cekilemedi.")

    for fut in done:
        sym = futs[fut]
        try:
            results[sym] = fut.result(timeout=1)
        except Exception:
            results[sym] = None

    for s in symbols:
        if s not in results:
            results[s] = None
    return results
