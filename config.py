# -*- coding: utf-8 -*-
"""
KONFİGÜRASYON - Buradaki tüm ayarları kendi bilgilerine göre doldur.
"""
import os

# ================== COIN LISTESI ==================
# Buyuk coinler (LARGE_CAPS, skor sarti +10): BTC, ETH, BNB
# Digerleri orta hacimli - backtestte sinyel kalitesi burada yuksek cikti.
# Not: FET kaldirildi (Bybit'ten delist edildi, ASI ile birlesti).
COINS = ["BTC", "ETH", "XRP", "SUI", "HYPE", "AVAX", "ARB", "APT",
         "RENDER", "TIA", "DOGE", "SOL",
         "LINK", "DOT", "NEAR", "INJ", "OP", "SEI",
         "BNB", "SHIB", "TAO", "ENA", "ATOM", "ALGO",
         # --- v3.1 genisleme: populer + orta hacimli (Bybit linear'da mevcut) ---
         "PEPE", "WIF", "BONK",          # meme'ler (yuksek volatilite, sinyel uretimi iyi)
         "JUP", "JTO", "PYTH",           # Solana ekosistemi
         "WLD", "ORDI",                  # yapay zeka / Ordinals
         "AR", "GRT",                    # depolama / indeksleme
         "EIGEN", "ONDO"]                # restaking / RWA
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
MAIL_FROM   = os.environ.get("MAIL_FROM", "terambos44@gmail.com")
MAIL_TO     = os.environ.get("MAIL_TO", "terambos44@gmail.com")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "qqqjererozxrocee")

MAIL_ON_STRONG = True   # GUCLU sinyal cikinca aninda mail at
HOURLY_DIGEST  = True   # Her saat basi ozet mail at

# ================== TP AYARLARI (STOP SENIN - BOT HESAPLAMAZ) ==================
TP1_MIN_PCT = 0.008    # TP1 zemini %0.8 (ATR genelde buyuk oldugundan zemin nadiren devreye girer)
TP2_MIN_PCT = 0.02     # TP2 zemini %2
ATR_TP1_MULT = 1.2     # TP1 = giris + 1.2 x ATR(1h)
ATR_TP2_MULT = 2.5     # TP2 = giris + 2.5 x ATR(1h)

# ================== BUYUK COIN AYRIMI ==================
# Backtest sonucu: BTC/ETH/BNB sinyalleri trend-takipte chop'a takiliyor (0/8 TP1),
# orta coinler 6/6 isabet. Buyuk coinlerde sinyel icin daha yuksek skor sarti:
LARGE_CAPS = ["BTC", "ETH", "BNB"]
LARGE_CAP_SCORE_BONUS = 10   # bu coinlerde SCORE_STRONG + 10 gerekir

# ================== BACKTEST AYARLARI ==================
BACKTEST_BARS = 2000         # 15dk x 2000 = ~21 gunluk veri
BACKTEST_HORIZON_BARS = 96   # sinyel sonrasi 96 bar = 24 saat pencere

# ================== MANIPULASYON / HABER SPIKE FILTRESI ==================
# Son N barda tek mum hareketi ATR'nin X kati ustuysa = ani haber/manipulasyon
# hareketi demektir. Bu durumda sinyal URETME (kovalama, geri donus riski).
ANOMALY_LOOKBACK = 3     # kac bar geriye bakilsin
ANOMALY_ATR_MULT = 2.5   # mum boyu > 2.5 x ATR(15dk) => spike say
# Funding asiriysa kalabalik pozisyon riski: sinyeli engelle
FUNDING_BLOCK = 0.00075  # |funding| > %0.075 => blokla
# QQE donus penceresi: kesisme son 6 barda ise gecerli (daha fazla sinyal)
QQE_FRESH_BARS = 6
# ================== RATE LIMIT ==================
SCAN_INTERVAL_MIN = 15   # tarama araligi (dakika)
REQUEST_SLEEP = 0.25     # Bybit istekleri arasi bekleme (saniye) - rate limit icin

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
