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
MAIL_FROM   = os.environ.get("MAIL_FROM", "terambos44@gmail.com")
MAIL_TO     = os.environ.get("MAIL_TO", "terambos44@gmail.com")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "lgdvpdkqjeekwgzp")

MAIL_ON_STRONG = True
HOURLY_DIGEST  = True

TP1_MIN_PCT = 0.008
TP2_MIN_PCT = 0.02
ATR_TP1_MULT = 1.2
ATR_TP2_MULT = 2.5

LARGE_CAPS = ["ETH", "BNB"]
LARGE_CAP_SCORE_BONUS = 10

BACKTEST_BARS = 2000
BACKTEST_HORIZON_BARS = 96

ANOMALY_LOOKBACK = 3
ANOMALY_ATR_MULT = 2.5
FUNDING_BLOCK = 0.00075
QQE_FRESH_BARS = 6

SCAN_INTERVAL_MIN = 15
REQUEST_SLEEP = 0.25

LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
SIGNAL_LOG = os.path.join(LOG_DIR, "sinyal_log.csv")
TRADE_LOG  = os.path.join(LOG_DIR, "trade_gunlugu.csv")

NEWS_ENABLED = True
NEWS_RSS = [
    "https://cointelegraph.com/rss",
    "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "https://decrypt.co/feed",
]
NEWS_CACHE_MIN = 60
