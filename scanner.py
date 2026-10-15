# -*- coding: utf-8 -*-
"""
ANA CALISTIRICI
  python scanner.py --once     : tek tarama
  python scanner.py            : surekli dongu
  python scanner.py --backtest BTCUSDT ETHUSDT ... : gecmis veride dogrulama
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

    # BTC trendini her zaman hesapla (korelasyon filtresi icin)
    btc_bull = None
    try:
        import indicators as ind
        btc_df60 = md.get_klines("BTCUSDT", "60", 200)
        if not btc_df60.empty:
            btc_k = ind.kalman_trend(btc_df60["close"])
            btc_bull = bool(btc_k["kalman_above"].iloc[-1])
    except Exception as e:
        print("[BTC TREND HATASI]", e)

    for sym in SYMBOLS:
        data = data_map.get(sym)
        if not data:
            skipped.append(sym)
            continue
        try:
            sig = sg.analyze_symbol(data, btc_bull=btc_bull)
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
            print(" %s %s | giris~%s | stop %s | TP1 %s | TP2 %s | skor %d" % (
                s["direction"], s["symbol"], s["entry_zone"], s["stop"],
                s["tp1"], s["tp2"], s["score"]))
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
    horizon_saat = BACKTEST_HORIZON_BARS * 0.25
    for sym in symbols:
        print("[v3.6] Backtest:", sym, "...")
        df15 = md.get_klines(sym, "15", BACKTEST_BARS)
        time.sleep(0.3)
        df60 = md.get_klines(sym, "60", BACKTEST_BARS)
        time.sleep(0.3)
        df240 = md.get_klines(sym, "240", BACKTEST_BARS)
        time.sleep(0.3)
        if df15.empty or df60.empty or df240.empty:
            print("  veri yok, atlaniyor")
            continue

        btc15 = md.get_klines("BTCUSDT", "15", BACKTEST_BARS) if sym != "BTCUSDT" else None

        res = sg.backtest_symbol(sym, df15, df60, df240,
                                 horizon_bars=BACKTEST_HORIZON_BARS,
                                 btc15=btc15,
                                 lookback_bars=BACKTEST_BARS)
        if res.empty:
            print("  skor>=70 sinyal uretilmedi (yeterli veri/kosul yok)")
            continue

        tp1 = res["tp1"].mean() * 100
        tp2 = res["tp2"].mean() * 100
        stop_rate = res["stop"].mean() * 100
        timeout_rate = (res["first"] == "TIMEOUT").mean() * 100
        avg_pnl = res["pnl_pct"].mean()
        total_pnl = res["pnl_pct"].sum()
        win_rate = (res["pnl_pct"] > 0).mean() * 100
        avg_pnl_usd = avg_pnl / 100 * 400   # 400 USD efektif pozisyon

        print("  sinyal sayisi : %d (son ~%.0f saat 15dk verisi)" % (len(res), len(df15) * 0.25))
        print("  TP1 isabet    : %.0f%%" % tp1)
        print("  TP2 isabet    : %.0f%%" % tp2)
        print("  Stop orani    : %.0f%%" % stop_rate)
        print("  Timeout orani : %.0f%% (%.0f saatte kapanmayan)" % (timeout_rate, horizon_saat))
        print("  --- SONUC ---")
        print("  Kazanma orani : %.0f%% (pnl > 0)" % win_rate)
        print("  Ort. PnL      : %+.3f%% (fiyat)" % avg_pnl)
        print("  Toplam PnL    : %+.2f%% (fiyat)" % total_pnl)
        print("  Ort. PnL (400 USD efektif) : %+.2f USD" % avg_pnl_usd)
        print("  Ort. MFE/MAE  : %+.2f%% / %+.2f%% (%d bar = %.0f saat)" % (
            res["mfe_pct"].mean(), res["mae_pct"].mean(),
            BACKTEST_HORIZON_BARS, horizon_saat))
        res.to_csv(f"backtest_{sym}.csv", index=False)
        print("  detay: backtest_%s.csv" % sym)


BOT_SURUM = "v3.6"


if __name__ == "__main__":
    print("kripto-sinyal-botu", BOT_SURUM)
    args = sys.argv[1:]
    if args and args[0] == "--backtest":
        backtest(args[1:] or SYMBOLS)
    elif args and args[0] == "--once":
        run_scan(explain="--explain" in args)
    else:
        loop()
