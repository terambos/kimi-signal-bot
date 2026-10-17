# -*- coding: utf-8 -*-
import os

# 35 POPULER COIN
COINS = [
    "ETH", "SOL", "XRP", "SUI", "HYPE", "AVAX", "ARB", "APT", "TIA", "DOGE",
    "1000PEPE", "WIF", "SEI", "INJ", "NEAR", "BNB", "LINK", "OP", "TAO", "ONDO",
    "ADA", "DOT", "LTC", "TRX", "ATOM", "FIL", "UNI", "AAVE", "RNDR", "FET",
    "IMX", "STX", "GRT", "SAND", "MATIC"
]
SYMBOLS = [c + "USDT" for c in COINS]

TIMEFRAME_ENTRY = "15"
TIMEFRAME_TREND = "60"
TIMEFRAME_HTF   = "240"

SCORE_STRONG = 55
SCORE_WATCH  = 45

BYBIT_BASE = "" 

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

SCAN_INTERVAL_MIN = 15
REQUEST_SLEEP = 0.5
MAX_WORKERS = 3 # Ayni anda 3 istek (Yahoo'yu kizdirmamak icin)

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
