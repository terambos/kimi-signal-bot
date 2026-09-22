# -*- coding: utf-8 -*-
"""
Sinyal motoru:
- HTF (1s+4s) Kalman trendi anahtar
- QQE momentum donusu tetik
- Hacim spike + OBV teyidi
- Open Interest artisi (akilli para vekili - ucretsiz alternatif)
- Funding asiriysa ters uyar
- Fiyat guclu S/R bolgesine yakin olmali
Cikti: yon, giris bolgesi, TP1/TP2, guven skoru (0-100), gerekceler.
"""
import numpy as np
import pandas as pd

import indicators as ind
from config import TP1_MIN_PCT, TP2_MIN_PCT, ATR_TP1_MULT, ATR_TP2_MULT


def _pct(a, b):
    return (a - b) / b if b else 0.0


def analyze_symbol(data: dict) -> dict | None:
    df15 = data.get("df_15")
    df60 = data.get("df_60")
    df240 = data.get("df_240")
    if df15 is None or df60 is None or df240 is None:
        return None
    if len(df15) < 60 or len(df60) < 60 or len(df240) < 40:
        return None

    last = df15["close"].iloc[-1]
    atr15 = ind.atr(df15).iloc[-1]
    atr60 = ind.atr(df60, 14).iloc[-1]
    if atr60 <= 0 or last <= 0:
        return None

    # ---- HTF trend (Kalman) ----
    k60 = ind.kalman_trend(df60["close"])
    k240 = ind.kalman_trend(df240["close"])
    k15 = ind.kalman_trend(df15["close"])
    bull_htf = bool(k60["kalman_above"].iloc[-1]) and bool(k240["kalman_above"].iloc[-1])
    bear_htf = (not k60["kalman_above"].iloc[-1]) and (not k240["kalman_above"].iloc[-1])

    # ---- ADX filtre ----
    a60 = ind.adx(df60)
    adx_v = float(a60["adx"].iloc[-1])
    plus, minus = float(a60["plus_di"].iloc[-1]), float(a60["minus_di"].iloc[-1])
    trend_ok = adx_v >= 20
    di_bull = plus > minus
    di_bear = minus > plus

    # ---- QQE (momentum donusu) ----
    q15 = ind.qqe(df15["close"])
    fresh_up = bool(q15["qqe_fresh_up"].iloc[-1]) and bool(q15["qqe_bull_zone"].iloc[-1])
    fresh_dn = bool(q15["qqe_fresh_dn"].iloc[-1]) and (not bool(q15["qqe_bull_zone"].iloc[-1]))

    # ---- Hacim ----
    v15 = ind.volume_signals(df15)
    spike = bool(v15["vol_spike"].iloc[-1])
    vol_ratio = float(v15["vol_ratio"].iloc[-1])
    obv_up = bool(v15["obv_rising"].iloc[-1])

    # ---- Funding (ters uyar) ----
    funding = float(data.get("funding", 0) or 0)
    funding_ok_long = funding < 0.0005     # %0.05 ustu finansman = kalabalik long
    funding_ok_short = funding > -0.0005

    # ---- Open Interest (1s degisim) ----
    oi_chg = 0.0
    oi_df = data.get("oi_df")
    if oi_df is not None and len(oi_df) >= 3:
        oi_chg = _pct(oi_df["openInterest"].iloc[-1], oi_df["openInterest"].iloc[-3])

    # ---- S/R ----
    sr = ind.strong_sr(df15)
    supports = sr["supports"]
    resists = sr["resists"]
    pd_low, pd_high = sr["pd_low"], sr["pd_high"]
    week_open = sr["week_open"]

    nearest_sup = supports[0]["price"] if supports else None
    nearest_res = resists[0]["price"] if resists else None

    sr_dist_sup = abs(last - nearest_sup) / last if nearest_sup else 9
    sr_dist_res = abs(last - nearest_res) / last if nearest_res else 9
    near_support = (nearest_sup is not None and sr_dist_sup < 0.0035) or abs(last - pd_low) / last < 0.003
    near_resist = (nearest_res is not None and sr_dist_res < 0.0035) or abs(last - pd_high) / last < 0.003

    # 15dk Kalman yonu (kisa vadeli ivme)
    bull_15 = bool(k15["kalman_above"].iloc[-1])
    bear_15 = not bull_15

    # ================= SKORLAMA =================
    def build(direction):
        score, reasons = 0, []

        # 1) HTF trend hizalanmasi (25)
        if direction == "LONG" and bull_htf and trend_ok and di_bull:
            score += 25; reasons.append("1s+4s Kalman trend yukari, ADX %.0f +DI baskin" % adx_v)
        elif direction == "SHORT" and bear_htf and trend_ok and di_bear:
            score += 25; reasons.append("1s+4s Kalman trend asagi, ADX %.0f -DI baskin" % adx_v)
        else:
            return None  # anahtar kosul: trend yoksa sinyal yok

        # 2) QQE momentum donusu (20)
        if direction == "LONG" and fresh_up:
            score += 20; reasons.append("QQE 15dk alt bandi yukari kesti (taze momentum donusu)")
        elif direction == "SHORT" and fresh_dn:
            score += 20; reasons.append("QQE 15dk ust bandi asagi kesti (taze momentum donusu)")

        # 3) Hacim (15)
        if spike:
            score += 10; reasons.append("Hacim patlamasi x%.1f (20 bar ort.)" % vol_ratio)
        if (direction == "LONG" and obv_up) or (direction == "SHORT" and not obv_up):
            score += 5; reasons.append("OBV egrisi yonle uyumlu")

        # 4) Open Interest (10) - akilli para vekili
        if direction == "LONG" and oi_chg > 0.005:
            score += 10; reasons.append("Acik pozisyon 1s icinde +%.1f%% (para giriyor)" % (oi_chg * 100))
        elif direction == "SHORT" and oi_chg > 0.005:
            score += 6; reasons.append("Acik pozisyon +%.1f%% (short'ta dikkat, kalabaliklasma olabilir)" % (oi_chg * 100))

        # 5) Funding (5)
        if direction == "LONG" and funding_ok_long:
            score += 5; reasons.append("Funding notr (%.4f%%)" % (funding * 100))
        elif direction == "SHORT" and funding_ok_short:
            score += 5; reasons.append("Funding notr (%.4f%%)" % (funding * 100))

        # 6) S/R bolgesi (15)
        if direction == "LONG" and near_support:
            score += 15
            ref = nearest_sup if nearest_sup and sr_dist_sup < abs(last - pd_low) / last else pd_low
            reasons.append("Fiyat guclu destek bolgesine yakin (%.8g)" % ref)
        elif direction == "SHORT" and near_resist:
            score += 15
            ref = nearest_res if nearest_res and sr_dist_res < abs(last - pd_high) / last else pd_high
            reasons.append("Fiyat guclu direnc bolgesine yakin (%.8g)" % ref)

        # 7) 15dk ivme (5) + haftalik acilis ustunde/altinda (5)
        if (direction == "LONG" and bull_15) or (direction == "SHORT" and bear_15):
            score += 5; reasons.append("15dk Kalman ivme yonle uyumlu")
        if direction == "LONG" and last > week_open:
            score += 5
        elif direction == "SHORT" and last < week_open:
            score += 5

        # ================= KURULUM / FIYATLAR =================
        if direction == "LONG":
            base = nearest_sup if near_support else (pd_low if abs(last - pd_low) / last < 0.01 else last)
        else:
            base = nearest_res if near_resist else (pd_high if abs(last - pd_high) / last < 0.01 else last)

        entry = float(last)  # piyasa girisi referansi
        if direction == "LONG":
            tp1 = max(entry * (1 + TP1_MIN_PCT), entry + ATR_TP1_MULT * atr60)
            tp2 = max(entry * (1 + TP2_MIN_PCT), entry + ATR_TP2_MULT * atr60)
            if nearest_res and tp1 > nearest_res * 0.999:
                reasons.append("Not: TP1 yolu uzerinde direnc (%.8g) - kismi kar almayi dusun" % nearest_res)
        else:
            tp1 = min(entry * (1 - TP1_MIN_PCT), entry - ATR_TP1_MULT * atr60)
            tp2 = min(entry * (1 - TP2_MIN_PCT), entry - ATR_TP2_MULT * atr60)
            if nearest_sup and tp1 < nearest_sup * 1.001:
                reasons.append("Not: TP1 yolu uzerinde destek (%.8g) - kismi kar almayi dusun" % nearest_sup)

        # anahtar referans bolge (limit emir bölgesi önerisi)
        zone = float(base) if base else entry

        return {
            "symbol": data["symbol"], "direction": direction,
            "price": round(entry, 8), "entry_zone": round(zone, 8),
            "tp1": round(tp1, 8), "tp2": round(tp2, 8),
            "atr15": round(atr15, 8), "atr1h": round(atr60, 8),
            "score": min(score, 100), "adx": round(adx_v, 1),
            "funding": funding, "oi_chg_1h": round(oi_chg * 100, 2),
            "vol_ratio": round(vol_ratio, 2),
            "reasons": reasons,
        }

    long_sig = build("LONG")
    short_sig = build("SHORT")
    if long_sig and short_sig:
        return long_sig if long_sig["score"] >= short_sig["score"] else short_sig
    return long_sig or short_sig


def backtest_symbol(symbol: str, df15: pd.DataFrame, df60: pd.DataFrame,
                    df240: pd.DataFrame, horizon_bars: int = 16) -> pd.DataFrame:
    """
    Basit dogrulama: sinyal uretilen her bar icin sonraki 'horizon_bars' (15dk) icinde
    TP1/TP2 dokunuldu mu, en kotu geri cekilme ne oldu.
    Not: Gecmis funding/OI olmadigi icin bu parcalar skora dahil DEGIL.
    """
    rows = []
    start = max(120, len(df15) - 2000)
    closes = df15["close"].to_numpy()
    atr60_full = ind.atr(df60, 14).reindex(df15.index, method="ffill")

    for i in range(start, len(df15) - horizon_bars - 1):
        sub = {"df_15": df15.iloc[:i + 1], "df_60": df60[df60.index <= df15.index[i]],
               "df_240": df240[df240.index <= df15.index[i]],
               "symbol": symbol, "funding": 0.0}
        sig = analyze_symbol(sub)
        if not sig or sig["score"] < 70:
            continue
        fut_h = df15["high"].iloc[i + 1:i + 1 + horizon_bars].to_numpy()
        fut_l = df15["low"].iloc[i + 1:i + 1 + horizon_bars].to_numpy()
        entry = sig["price"]
        tp1_hit = np.any(fut_h >= sig["tp1"]) if sig["direction"] == "LONG" else np.any(fut_l <= sig["tp1"])
        tp2_hit = np.any(fut_h >= sig["tp2"]) if sig["direction"] == "LONG" else np.any(fut_l <= sig["tp2"])
        if sig["direction"] == "LONG":
            mae = ((fut_l.min() - entry) / entry) if len(fut_l) else 0
            mfe = ((fut_h.max() - entry) / entry) if len(fut_h) else 0
        else:
            mae = ((entry - fut_h.max()) / entry) if len(fut_h) else 0
            mfe = ((entry - fut_l.min()) / entry) if len(fut_l) else 0
        rows.append({"time": df15.index[i], "dir": sig["direction"], "score": sig["score"],
                     "tp1": tp1_hit, "tp2": tp2_hit, "mae_pct": round(mae * 100, 2),
                     "mfe_pct": round(mfe * 100, 2)})
    return pd.DataFrame(rows)


def diagnose(data: dict) -> dict:
    """Bir coinin neden sinyal uretmedigini gosteren hizli kontrol.
    (analyze_symbol'den bagimsiz, sadece raporlama icin.)"""
    df60 = data.get("df_60"); df240 = data.get("df_240"); df15 = data.get("df_15")
    if df60 is None or df240 is None or len(df60) < 60 or len(df240) < 40:
        return {"ok": False, "neden": "yetersiz veri"}
    k60 = ind.kalman_trend(df60["close"])
    k240 = ind.kalman_trend(df240["close"])
    a60 = ind.adx(df60)
    q15 = ind.qqe(df15["close"]) if df15 is not None and len(df15) > 20 else None
    bull = bool(k60["kalman_above"].iloc[-1]) and bool(k240["kalman_above"].iloc[-1])
    bear = (not k60["kalman_above"].iloc[-1]) and (not k240["kalman_above"].iloc[-1])
    adx_v = float(a60["adx"].iloc[-1])
    reasons = []
    if not (bull or bear):
        t60 = "YUKARI" if k60["kalman_above"].iloc[-1] else "ASAGI"
        t240 = "YUKARI" if k240["kalman_above"].iloc[-1] else "ASAGI"
        reasons.append("1s trend " + t60 + " ama 4s trend " + t240 + " (hizalanma yok)")
    if adx_v < 20:
        reasons.append("ADX dusuk (%.0f < 20), trend siddeti yetersiz" % adx_v)
    if q15 is not None:
        fresh_up = bool(q15["qqe_fresh_up"].iloc[-1])
        fresh_dn = bool(q15["qqe_fresh_dn"].iloc[-1])
        if not (fresh_up or fresh_dn):
            reasons.append("QQE momentum donusu yok (son 3 barda kesisme yok)")
    return {"ok": not reasons, "neden": "; ".join(reasons) if reasons else "kosullar uygun"}
