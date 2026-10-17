# -*- coding: utf-8 -*-
"""
KONFIGURASYON
"""
import os

# 30 POPULER BYBIT FUTURES COINI
COINS = [
    # Mevcut 20'lik listen
    "ETH", "SOL", "XRP", "SUI", "HYPE", "AVAX", "ARB", "APT", "TIA", "DOGE",
    "1000PEPE", "WIF", "SEI", "INJ", "NEAR", "BNB", "LINK", "OP", "TAO", "ONDO",
    # Yeni eklenen 10 coin (Bybit Futures likiditesi yuksek)
    "ADA", "LTC", "TRX", "ENA", "WLD", "AAVE", "UNI", "XLM", "BCH", "ZEC"
]
SYMBOLS = [c + "USDT" for c in COINS]

TIMEFRAME_ENTRY = "15"
TIMEFRAME_TREND = "60"
TIMEFRAME_HTF   = "240"

SCORE_STRONG = 55
SCORE_WATCH  = 45

# Dogrudan Bybit API (Yerelde calisirken proxy gerekmez)
BYBIT_BASE = "https://api.bybit.com"

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT   = 465
MAIL_FROM   = os.environ.get("MAIL_FROM", "")
MAIL_TO     = os.environ.get("MAIL_TO", "")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")

MAIL_ON_STRONG = True
HOURLY_DIGEST  = True

STOP_PCT     = 0.05
TP1_MIN_PCT  = 0.03
TP2_MIN_PCT  = 0.06
TP1_FALLBACK_PCT = 0.05
TP2_FALLBACK_PCT = 0.07
MIN_TP_DISTANCE_PCT = 0.03

ATR_TP1_MULT = 0.1
ATR_TP2_MULT = 0.1

LARGE_CAPS = ["ETH", "BNB"]
LARGE_CAP_SCORE_BONUS = 5

BACKTEST_BARS = 4000
BACKTEST_HORIZON_BARS = 288

ANOMALY_LOOKBACK = 3
ANOMALY_ATR_MULT = 2.5
FUNDING_BLOCK = 0.00075
QQE_FRESH_BARS = 6
ADX_MIN = 20

SCAN_INTERVAL_MIN = 15  # 15 dakikada bir tarar (5 yapmak istersen degistir)
REQUEST_SLEEP = 0.15
MAX_WORKERS = 10

LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
SIGNAL_LOG = os.path.join(LOG_DIR, "sinyal_log.csv")
TRADE_LOG  = os.path.join(LOG_DIR, "trade_gunlugu.csv")

STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "state.json")
SYMBOL_COOLDOWN_MIN = 240

NEWS_ENABLED = True
NEWS_RSS = [
    "https://cointelegraph.com/rss",
    "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "https://decrypt.co/feed",
]
NEWS_CACHE_MIN = 60
