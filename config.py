# -*- coding: utf-8 -*-
"""
KONFİGÜRASYON - Buradaki tüm ayarları kendi bilgilerine göre doldur.
"""
import os

# ================== COIN LISTESI ==================
COINS = ["BTC", "ETH", "XRP", "SUI", "HYPE", "AVAX", "ARB", "APT",
         "FET", "RENDER", "TIA", "DOGE", "SOL",
         "LINK", "DOT", "NEAR", "INJ", "OP", "SEI",
         "BNB", "SHIB", "TAO", "ENA", "ATOM", "ALGO"]
SYMBOLS = [c + "USDT" for c in COINS]

# ================== ZAMAN DILIMLERI ==================
TIMEFRAME_ENTRY = "15"    # Giris zamanlamasi (dakika)
TIMEFRAME_TREND = "60"    # Trend (1 saat)
TIMEFRAME_HTF   = "240"   # Ust zaman dilimi (4 saat)

# ================== SINYAL ESIGI ==================
SCORE_STRONG = 70      # 70+ => "GUCLU SINYAL" maili atilir
SCORE_WATCH  = 55      # 55-70 => sadece saatlik ozette listelenir

# ================== BYBIT (PUBLIC VERI - API KEY GEREKMEZ) ==================
# Kline / Funding / Open-Interest verileri ucretsizdir, key istemez.
BYBIT_BASE = "https://api.bybit.com"
# Not: Trade acmak icin kullandigin API anahtarlarini bu dosyaya YAZMA.
# Bu bot sadece okuma yapar (public endpoints).

# ================== MAIL (GMAIL APP PASSWORD) ==================
# Adimlar: myaccount.google.com -> Guvenlik -> 2 Adimli Dogrulama -> Uygulama sifreleri
# Ornegin ad "kriptobot" olustur, verilen 16 haneli sifreyi buraya koy.
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT   = 465
# Lokalde asagidaki tirnak icindeki degerler kullanilir.
# Bulutta (GitHub) bu degerler "Secrets"tan otomatik okunur - kodda yazmaz.
MAIL_FROM   = os.environ.get("MAIL_FROM", "SENIN_GMAIL_ADRESIN@gmail.com")
MAIL_TO     = os.environ.get("MAIL_TO", "SENIN_GMAIL_ADRESIN@gmail.com")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "BURAYA_16_HANELI_UYGULAMA_SIFRESI")

MAIL_ON_STRONG = True   # GUCLU sinyal cikinca aninda mail at
HOURLY_DIGEST  = True   # Her saat basi ozet mail at

# ================== TP AYARLARI (STOP SENIN - BOT HESAPLAMAZ) ==================
TP1_MIN_PCT = 0.04     # TP1 en az %4
TP2_MIN_PCT = 0.09     # TP2 en az %9
ATR_TP1_MULT = 1.5     # TP1 = giris + 1.5 x ATR(1h)
ATR_TP2_MULT = 3.0     # TP2 = giris + 3.0 x ATR(1h)

# ================== RATE LIMIT ==================
SCAN_INTERVAL_MIN = 15   # tarama araligi (dakika)
REQUEST_SLEEP = 0.15     # Bybit istekleri arasi bekleme (saniye) - rate limit icin

# ================== DOSYALAR ==================
LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
SIGNAL_LOG = os.path.join(LOG_DIR, "sinyal_log.csv")
TRADE_LOG  = os.path.join(LOG_DIR, "trade_gunlugu.csv")

# ================== HABER (OPSİYONEL - UCRETSIZ RSS) ==================
NEWS_ENABLED = True
NEWS_RSS = [
    "https://cointelegraph.com/rss",
    "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "https://decrypt.co/feed",
]
NEWS_CACHE_MIN = 60
