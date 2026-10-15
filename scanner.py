# -*- coding: utf-8 -*-
"""
ANA CALISTIRICI
  python scanner.py --once     : tek tarama (test icin)
  python scanner.py            : surekli dongu, 15 dk'da bir tarar, saat basi ozet maili
  python scanner.py --backtest BTCUSDT ETHUSDT ... : gecmis veride stratejiyi dogrular
"""
import os
import sys
import time
import pandas as pd
from datetime import datetime, timezone

import market_data as md
import signals as sg
import notify
import news
from config import (SYMBOLS, SCAN_INTERVAL_MIN, SCORE_STRONG, SCORE_WATCH,
                    HOURLY_DIGEST, NEWS_ENABLED, BACKTEST_BARS,
                    BACKTEST_HORIZON_BARS, SIGNAL_LOG, SIGNAL_COOLDOWN_MIN)

_last_digest_hour = None


def _recent_signal(symbol: str, direction: str) -> bool:
    """Ayni sembol+yon son SIGNAL_COOLDOWN_MIN dakikada loglandi mi?"""
    if not os.path.exists(SIGNAL_LOG):
        return False
    try:
        df = pd.read_csv(SIGNAL_LOG)
        if df.empty:
            return False
        df["time"] = pd.to_datetime(df["time"], utc=True, errors="coerce")
        cutoff = pd.Timestamp.utcnow() - pd.Timedelta(minutes=SIGNAL_COOLDOWN_MIN)
        recent = df[(df["symbol"] == symbol) & (df["direction"] == direction) & (df["time"] >= cutoff)]
        return not recent.empty
    except Exception:
        return False


def run_scan(verbose=True, explain=False) -> list:
    strong, watch, skipped = [], [], []
    print("Veriler paralel cekiliyor...", flush=True)

    data_map = md.fetch_all_parallel(SYMBOLS)
    for sym in SYMBOLS:
        data = data_map.get(sym)
        if not data:
            skipped.append(sym)
            continue
        try:
            sig = sg.analyze_symbol(data)
        except Exception as e:
            print("[ANALIZ HATASI]", sym, e)
            skipped.append(sym)
            continue
        if sig and not sg.sig_passes(sig):
            sig = None
        if not sig:
            if explain:
                d = sg.diagnose(data)
                print("%-11s ELENDI  -> %s" % (sym, d.get("neden", "?")))
            else:
                skipped.append(sym)
            continue
        # Cooldown: ayni sinyal tekrar mail atmasin
        if _recent_signal(sym, sig["direction"]):
            if verbose:
                print("%-11s skor=%d %s (cooldown, mail atlandi)" % (sym, sig["score"], sig["direction"]))
            continue
        if sig["score"] >= SCORE_STRONG:
            ctx = news.context_for(sym) if NEWS_ENABLED else []
            notify.send_signal_mail(sig, ctx)
            notify.log_signal(sig)
            strong.append(sig)
        elif sig["score"] >= SCORE_WATCH:
            watch.append(sig)
        if verbose:
            print("%-11s skor=%d %s" % (sym, sig["score"], sig["direction"]))
    if strong:
        print("\n=== GUCLU SINYALLER ===")
        for s in strong:
            print(" %s %s | giris~%s | TP1 %s | TP2 %s | skor %d" % (
                s["direction"], s["symbol"], s["entry_zone"], s["tp1"], s["tp2"], s["score"]))
    if watch:
        print("=== izleme listesi (skor %d-%d): %s" % (
            SCORE_WATCH, SCORE_STRONG, ", ".join(f"{w['symbol']}={w['score']}" for w in watch)))
    if skipped and not explain:
        print("=== %d coin elendi: %s" % (len(skipped), ", ".join(skipped)))
        print("    (nedenlerini gormek icin: python scanner.py --once --explain)")
    return strong


def maybe_digest(strong_now):
    global _last_digest_hour
    now = datetime.now(timezone.utc)
    if HOURLY_DIGEST and now.minute < SCAN_INTERVAL_MIN and _last_digest_hour != now.hour:
        _last_digest_hour = now.hour
        notify.send_digest_mail(strong_now, news.get_news() if NEWS_ENABLED else [])


def loop():
    print("Sonsuz tarama basladi. 15 dk aralik. Durdurmak icin Ctrl+C.")
    while True:
        t0 = time.time()
        try:
            strong = run_scan()
            maybe_digest(strong)
        except Exception as e:
            print("[HATA]", e)
        elapsed = time.time() - t0
        time.sleep(max(1, SCAN_INTERVAL_MIN * 60 - elapsed))


def backtest(symbols):
    for sym in symbols:
        print("[v3.5] Backtest:", sym, "...")
        df15 = md.get_klines(sym, "15", BACKTEST_BARS)
        time.sleep(0.3)
        df60 = md.get_klines(sym, "60", BACKTEST_BARS)
        time.sleep(0.3)
        df240 = md.get_klines(sym, "240", BACKTEST_BARS)
        time.sleep(0.3)
        if df15.empty or df60.empty or df240.empty:
            print("  veri yok, atlaniyor")
            continue
        res = sg.backtest_symbol(sym, df15, df60, df240,
                                 horizon_bars=BACKTEST_HORIZON_BARS)
        if res.empty:
            print("  skor>=70 sinyal uretilmedi (yeterli veri/kosul yok)")
            continue
        tp1 = res["tp1"].mean() * 100
        tp2 = res["tp2"].mean() * 100
        print("  sinyal sayisi : %d (son ~%.0f saat 15dk verisi)" % (len(res), len(df15) * 0.25))
        print("  TP1 isabet    : %.0f%%" % tp1)
        print("  TP2 isabet    : %.0f%%" % tp2)
        print("  Ort. MFE/MAE  : %+.2f%% / %+.2f%% (%d bar = %.0f saat pencere)" % (
            res["mfe_pct"].mean(), res["mae_pct"].mean(),
            BACKTEST_HORIZON_BARS, BACKTEST_HORIZON_BARS * 0.25))
        res.to_csv(f"backtest_{sym}.csv", index=False)
        print("  detay: backtest_%s.csv" % sym)


BOT_SURUM = "v3.5"


if __name__ == "__main__":
    print("kripto-sinyal-botu", BOT_SURUM)
    args = sys.argv[1:]
    if args and args[0] == "--backtest":
        backtest(args[1:] or SYMBOLS)
    elif args and args[0] == "--once":
        run_scan(explain="--explain" in args)
    else:
        loop()
