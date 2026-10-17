# -*- coding: utf-8 -*-
"""
Yahoo Finance veri katmani.
API key GEREKMEZ, IP engeli YOKTUR.
"""
import time
import random
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
import pandas as pd
import yfinance as yf

from config import REQUEST_SLEEP, MAX_WORKERS

# Yahoo sembol eslestirmeleri (Bybit sembolleri -> Yahoo sembolleri)
YF_TICKER_OVERRIDES = {
    "1000PEPE": "PEPE24478-USD", # Dogru PEPE adresi
    "HYPE": "HYPE32196-USD",
    "APT": "APT21794-USD", 
    "TAO": "TAO22974-USD",
    "SUI": "SUI20947-USD"
}

def get_klines(symbol: str, interval: str, limit: int = 200) -> pd.DataFrame:
    base = symbol.replace("USDT", "")
    ticker_symbol = YF_TICKER_OVERRIDES.get(base, base + "-USD")
    
    tf_map = {"15": "15m", "60": "1h", "240": "4h"}
    yf_interval = tf_map.get(interval, "15m")
    
    # Yahoo'nun limitleri
    if yf_interval == "15m":
        period = "60d"
    elif yf_interval == "1h":
        period = "730d"
    else:
        period = "730d"
    
    try:
        # Yahoo'nun rate limitine takilmamak icin rastgele bekleme
        time.sleep(random.uniform(0.5, 1.5))
        
        ticker = yf.Ticker(ticker_symbol)
        df = ticker.history(period=period, interval=yf_interval)
        if df.empty:
            return pd.DataFrame()
        
        df = df.rename(columns={
            "Open": "open", "High": "high", 
            "Low": "low", "Close": "close", "Volume": "volume"
        })
        
        if df.index.tz is None:
            df.index = df.index.tz_localize('UTC')
        else:
            df.index = df.index.tz_convert('UTC')
            
        df.index.name = "start"
        return df[["open", "high", "low", "close", "volume"]].tail(limit)
    except Exception as e:
        print(f"[VERI HATASI] {symbol} ({yf_interval}): {e}")
        return pd.DataFrame()


def get_open_interest(symbol: str) -> pd.DataFrame:
    return pd.DataFrame()


def get_ticker(symbol: str) -> dict:
    base = symbol.replace("USDT", "")
    ticker_symbol = YF_TICKER_OVERRIDES.get(base, base + "-USD")
    try:
        t = yf.Ticker(ticker_symbol)
        df = t.history(period="1d")
        if not df.empty:
            return {"funding": 0.0, "mark": float(df["Close"].iloc[-1]), "oi_now": 0.0, "turnover24h": 0.0}
    except Exception:
        pass
    return {}


def fetch_all(symbol: str, tfs: tuple = ("15", "60", "240"),
              ticker_info: dict | None = None) -> dict:
    out = {"symbol": symbol}
    for tf in tfs:
        out[f"df_{tf}"] = get_klines(symbol, tf, limit=200)
        time.sleep(0.2) # Kisa mola
    
    if ticker_info is not None:
        out.update(ticker_info.get(symbol, {}))
    else:
        out.update(get_ticker(symbol))
        
    time.sleep(0.2)
    out["oi_df"] = None
    return out


def fetch_all_parallel(symbols: list, tfs: tuple = ("15", "60", "240"),
                       ticker_info: dict | None = None,
                       max_workers: int = MAX_WORKERS) -> dict:
    results = {}
    # Yahoo'yi bogmamak icin ayni anda maksimum 5 istek atiyoruz
    ex = ThreadPoolExecutor(max_workers=5) 
    futs = {ex.submit(fetch_all, s, tfs, ticker_info): s for s in symbols}

    # Islem suresi 120 saniyeye cikarildi (Yahoo yavaslatiyor)
    done, not_done = wait(futs, timeout=120, return_when=FIRST_COMPLETED)

    if not_done:
        print(f"[KRITIK TIMEOUT] {len(not_done)} coin 120 saniyede cekilemedi, atlaniyor.")

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
