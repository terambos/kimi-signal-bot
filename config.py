# -*- coding: utf-8 -*-
"""
KONFIGURASYON
"""
import os

COINS = ["ETH", "SOL", "XRP", "SUI", "HYPE",
         "AVAX", "ARB", "APT", "TIA", "DOGE",
         "PEPE", "WIF", "SEI", "INJ", "NEAR",
         "BNB", "LINK", "OP", "TAO", "ONDO"]
SYMBOLS = [c + "USDT" for c in COINS]

TIMEFRAME_ENTRY = "15"
TIMEFRAME_TREND = "60"
TIMEFRAME_HTF   = "240"

SCORE_STRONG = 70
SCORE_WATCH  = 55

BYBIT_BASE = "https://api.bybit.com"

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT   = 465
MAIL_FROM   = os.environ.get("MAIL_FROM", "")
MAIL_TO     = os.environ.get("MAIL_TO", "")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")

MAIL_ON_STRONG = True
HOURLY_DIGEST  = True

# --- STOP ve TP (FIYAT yuzdesi olarak; kaldirac hesabi kullaniciya ait) ---
# 20 USD marjin x 20x = 400 USD efektif pozisyon
# Fiyatta %5 hareket = marjinin %100'u (20 USD)
STOP_PCT     = 0.05      # fiyatta %5 stop  -> marjin biter
TP1_MIN_PCT  = 0.05      # fiyatta %5 TP1   -> +20 USD
TP2_MIN_PCT  = 0.10      # fiyatta %10 TP2  -> +40 USD

# ATR bazli hedefler pratikte devre disi (min degerler her zaman daha buyuk)
ATR_TP1_MULT = 0.1
ATR_TP2_MULT = 0.1

LARGE_CAPS = ["ETH", "BNB"]
LARGE_CAP_SCORE_BONUS = 10

BACKTEST_BARS = 2000
BACKTEST_HORIZON_BARS = 192    # 192 * 15dk = 48 saat (2 gun)

ANOMALY_LOOKBACK = 3
ANOMALY_ATR_MULT = 2.5
FUNDING_BLOCK = 0.00075
QQE_FRESH_BARS = 4

SCAN_INTERVAL_MIN = 15
REQUEST_SLEEP = 0.15
MAX_WORKERS = 8

LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
SIGNAL_LOG = os.path.join(LOG_DIR, "sinyal_log.csv")
TRADE_LOG  = os.path.join(LOG_DIR, "trade_gunlugu.csv")

SIGNAL_COOLDOWN_MIN = 60

NEWS_ENABLED = True
NEWS_RSS = [
    "https://cointelegraph.com/rss",
    "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "https://decrypt.co/feed",
]
NEWS_CACHE_MIN = 60
