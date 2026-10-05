# -*- coding: utf-8 -*-
"""
KONFIGÜRASYON - GitHub Actions için (20 coin, proxy'siz)
"""
import os

# ================== COIN LISTESI (20 coin - BTC hariç) ==================
COINS = ["ETH", "SOL", "XRP", "SUI", "HYPE",
         "AVAX", "ARB", "APT", "TIA", "DOGE",
         "PEPE", "WIF", "SEI", "INJ", "NEAR",
         "BNB", "LINK", "OP", "TAO", "ONDO"]
SYMBOLS = [c + "USDT" for c in COINS]

# ================== ZAMAN DILIMLERI ==================
TIMEFRAME_ENTRY = "15"
TIMEFRAME_TREND = "60"
TIMEFRAME_HTF   = "240"

# ================== SINYAL ESIGI ==================
SCORE_STRONG = 70
SCORE_WATCH  = 55

# ================== BYBIT (PUBLIC VERI - API KEY GEREKMEZ) ==================
BYBIT_BASE = "https://api.bybit.com"

# ================== MAIL (GMAIL APP PASSWORD) ==================
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT   = 465
MAIL_FROM   = os.environ.get("MAIL_FROM", "SENIN_GMAIL_ADRESIN@gmail.com")
MAIL_TO     = os.environ.get("MAIL_TO", "SENIN_GMAIL_ADRESIN@gmail.com")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "BURAYA_16_HANELI_UYGULAMA_SIFRESI")

MAIL_ON_STRONG = True
HOURLY_DIGEST  = True

# ================== TP AYARLARI ==================
TP1_MIN_PCT = 0.008
TP2_MIN_PCT = 0.02
ATR_TP1_MULT = 1.2
ATR_TP2_MULT = 2.5

# ================== BUYUK COIN AYRIMI ==================
# BTC hariç tutulduğu için liste güncellendi
LARGE_CAPS = ["ETH", "BNB"]
LARGE_CAP_SCORE_BONUS = 10

# ================== BACKTEST AYARLARI ==================
BACKTEST_BARS = 2000
BACKTEST_HORIZON_BARS = 96

# ================== MANIPULASYON / HABER SPIKE FILTRESI ==================
ANOMALY_LOOKBACK = 3
ANOMALY_ATR_MULT = 2.5
FUNDING_BLOCK = 0.00075
QQE_FRESH_BARS = 6

# ================== RATE LIMIT ==================
SCAN_INTERVAL_MIN = 15
REQUEST_SLEEP = 0.25

# ================== DOSYALAR ==================
LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
SIGNAL_LOG = os.path.join(LOG_DIR, "sinyal_log.csv")
TRADE_LOG  = os.path.join(LOG_DIR, "trade_gunlugu.csv")

# ================== HABER ==================
NEWS_ENABLED = True
NEWS_RSS = [
    "https://cointelegraph.com/rss",
    "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "https://decrypt.co/feed",
]
NEWS_CACHE_MIN = 60
