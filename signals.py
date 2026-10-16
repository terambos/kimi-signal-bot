# -*- coding: utf-8 -*-
"""
Sinyal motoru v4.0 (katmanli skor):
- ZORUNLU: 4s trend yonu + QQE momentum donusu + funding asiri degil
- PUAN VEREN: 1s slope, ADX, DI, S/R, hacim, BTC korelasyonu, 15dk ivme
- Skor esigi: SCORE_STRONG (mail), SCORE_WATCH (izleme)
"""
import numpy as np
import pandas as pd

import indicators as ind
from config import (TP1_MIN_PCT, TP2_MIN_PCT, ATR_TP1_MULT, ATR_TP2_MULT,
                    ANOMALY_LOOKBACK, ANOMALY_ATR_MULT, FUNDING_BLOCK,
                    QQE_FRESH_BARS, SCORE_STRONG, LARGE_CAPS,
                    LARGE_CAP_SCORE_BONUS, STOP_PCT, BACKTEST_BARS)


def _pct(a, b):
    return (a - b) / b if b else 0.0


def sig_passes(sig: dict) -> bool:
    if not sig:
        return False
    esik = SCORE_STRONG
    coin = sig["symbol"].replace("USDT", "")
    if coin in LARGE_CAPS:
        esik += LARGE_CAP_SCORE_BONUS
    return sig["score"] >= esik


def analyze_symbol(data: dict, btc_bull: bool | None = None) -> dict | None:
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

    # Manipulasyon filtresi
    bar_range = (df15["high"] - df15["low"]).iloc[-ANOMALY_LOOKBACK:]
    if len(bar_range) and (bar_range.max() > ANOMALY_ATR_MULT * atr15):
        return None

    # Kalman trendler
    k60 = ind.kalman_trend(df60["close"])
    k240 = ind.kalman_trend(df240["close"])
    k15 = ind.kalman_trend(df15["close"])

    k60_slope_pct = float(k60["kalman_slope_pct"].iloc[-1])
    bull_240 = bool(k240["kalman_above"].iloc[-1])
    bear_240 = not bull_240
    bull_60 = bool(k60["kalman_above"].iloc[-1])
    bear_60 = not bull_60

    # ADX
    a60 = ind.adx(df60)
    adx_v = float(a60["adx"].iloc[-1])
    plus, minus = float(a60["plus_di"].iloc[-1]), float(a60["minus_di"].iloc[-1])
    di_bull = plus > minus
    di_bear = minus > plus

    # QQE
    q15 = ind.qqe(df15["close"])
    fresh_up = bool(q15["qqe_fresh_up"].iloc[-1]) and bool(q15["qqe_bull_zone"].iloc[-1])
    fresh_dn = bool(q15["qqe_fresh_dn"].iloc[-1]) and (not bool(q15["qqe_bull_zone"].iloc[-1]))

    # Hacim
    v15 = ind.volume_signals(df15, spike_mult=2.0)
    spike = bool(v15["vol_spike"].iloc[-1])
    vol_ratio = float(v15["vol_ratio"].iloc[-1])
    obv_up = bool(v15["obv_rising"].iloc[-1])

    # Funding
    funding = float(data.get("funding", 0) or 0)

    # OI
    oi_chg = 0.0
    oi_df = data.get("oi_df")
    if oi_df is not None and len(oi_df) >= 5:
        oi_chg = _pct(float(oi_df["openInterest"].iloc[-1]),
                      float(oi_df["openInterest"].iloc[-5]))

    # S/R
    sr = ind.strong_sr(df15)
    supports = sr["supports"]
    resists = sr["resists"]
    pd_low, pd_high = sr["pd_low"], sr["pd_high"]
    week_open = sr["week_open"]

    nearest_sup = supports[0]["price"] if supports else None
    nearest_res = resists[0]["price"] if resists else None

    SR_TOL = 0.004  # %0.4
    sr_dist_sup = abs(last - nearest_sup) / last if nearest_sup else 9
    sr_dist_res = abs(last - nearest_res) / last if nearest_res else 9
    near_support = (nearest_sup is not None and sr_dist_sup < SR_TOL) or abs(last - pd_low) / last < 0.003
    near_resist  = (nearest_res is not None and sr_dist_res < SR_TOL) or abs(last - pd_high) / last < 0.003

    bull_15 = bool(k15["kalman_above"].iloc[-1])
    bear_15 = not bull_15

    # ================= SKORLAMA =================
    def build(direction):
        score, reasons = 0, []
        mandatory_ok = True

        # === ZORUNLU 1: Funding asiri degil ===
        if direction == "LONG" and funding > FUNDING_BLOCK:
            return None
        if direction == "SHORT" and funding < -FUNDING_BLOCK:
            return None

        # === ZORUNLU 2: 4s trend yonu ===
        if direction == "LONG" and not bull_240:
            return None
        if direction == "SHORT" and not bear_240:
            return None
        score += 20
        reasons.append("4s Kalman trend %s" % ("YUKARI" if direction == "LONG" else "ASAGI"))

        # === ZORUNLU 3: QQE momentum donusu ===
        if direction == "LONG" and not fresh_up:
            return None
        if direction == "SHORT" and not fresh_dn:
            return None
        score += 20
        reasons.append("QQE 15dk taze momentum donusu")

        # === PUAN: 1s slope yonu ===
        if direction == "LONG" and k60_slope_pct > 0:
            score += 10; reasons.append("1s egim +%.3f" % k60_slope_pct)
        elif direction == "SHORT" and k60_slope_pct < 0:
            score += 10; reasons.append("1s egim %.3f" % k60_slope_pct)

        # === PUAN: 1s fiyat Kalman ustu/alti ===
        if direction == "LONG" and bull_60:
            score += 5; reasons.append("1s fiyat Kalman ustu")
        elif direction == "SHORT" and bear_60:
            score += 5; reasons.append("1s fiyat Kalman alti")

        # === PUAN: ADX ===
        if adx_v >= 25:
            score += 10; reasons.append("ADX guclu (%.1f)" % adx_v)
        elif adx_v >= 20:
            score += 5; reasons.append("ADX orta (%.1f)" % adx_v)

        # === PUAN: DI baskinlik ===
        if direction == "LONG" and di_bull:
            score += 5; reasons.append("+DI baskin")
        elif direction == "SHORT" and di_bear:
            score += 5; reasons.append("-DI baskin")

        # === PUAN: BTC korelasyon (iptal degil, puan) ===
        if btc_bull is not None and data["symbol"] != "BTCUSDT":
            if (direction == "LONG" and btc_bull) or (direction == "SHORT" and not btc_bull):
                score += 10; reasons.append("BTC trendi yonle uyumlu")

        # === PUAN: Hacim ===
        if spike:
            score += 10; reasons.append("Hacim patlamasi x%.1f" % vol_ratio)
        if (direction == "LONG" and obv_up) or (direction == "SHORT" and not obv_up):
            score += 5; reasons.append("OBV yonle uyumlu")

        # === PUAN: OI ===
        if oi_chg > 0.005:
            score += 5; reasons.append("OI +%.1f%%" % (oi_chg * 100))

        # === PUAN: S/R ===
        if direction == "LONG" and near_support:
            score += 15; reasons.append("Fiyat destek bolgesine yakin")
        elif direction == "SHORT" and near_resist:
            score += 15; reasons.append("Fiyat direnc bolgesine yakin")

        # === PUAN: 15dk ivme + haftalik ===
        if (direction == "LONG" and bull_15) or (direction == "SHORT" and bear_15):
            score += 5; reasons.append("15dk ivme yonle uyumlu")
        if direction == "LONG" and last > week_open:
            score += 5; reasons.append("Haftalik acilis uzerinde")
        elif direction == "SHORT" and last < week_open:
            score += 5; reasons.append("Haftalik acilis altinda")

        # === PUAN: Funding notr ===
        if abs(funding) < 0.0005:
            score += 5; reasons.append("Funding notr")

        # ================= KURULUM =================
        if direction == "LONG":
            base = nearest_sup if near_support else (pd_low if abs(last - pd_low) / last < 0.01 else last)
        else:
            base = nearest_res if near_resist else (pd_high if abs(last - pd_high) / last < 0.01 else last)

        entry = float(last)
        stop_dist = STOP_PCT * entry

        if direction == "LONG":
            stop = entry - stop_dist
            tp1 = entry * (1 + TP1_MIN_PCT)
            tp2 = entry * (1 + TP2_MIN_PCT)
            if nearest_res and tp1 > nearest_res * 0.999:
                reasons.append("Not: TP1 yolunda direnc")
        else:
            stop = entry + stop_dist
            tp1 = entry * (1 - TP1_MIN_PCT)
            tp2 = entry * (1 - TP2_MIN_PCT)
            if nearest_sup and tp1 < nearest_sup * 1.001:
                reasons.append("Not: TP1 yolunda destek")

        zone = float(base) if base else entry

        return {
            "symbol": data["symbol"], "direction": direction,
            "price": round(entry, 8), "entry_zone": round(zone, 8),
            "tp1": round(tp1, 8), "tp2": round(tp2, 8),
            "stop": round(stop, 8),
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
                    df240: pd.DataFrame, horizon_bars: int = 288,
                    btc15: pd.DataFrame | None = None,
                    lookback_bars: int | None = None) -> pd.DataFrame:
    rows = []
    if lookback_bars is None:
        lookback_bars = BACKTEST_BARS
    start = max(120, len(df15) - lookback_bars)

    btc_trend_series = None
    if btc15 is not None and len(btc15) > 60:
        btc_k = ind.kalman_trend(btc15["close"])
        btc_trend_series = btc_k["kalman_above"]

    for i in range(start, len(df15) - horizon_bars - 1):
        t_now = df15.index[i]
        sub = {"df_15": df15.iloc[:i + 1],
               "df_60": df60[df60.index <= t_now],
               "df_240": df240[df240.index <= t_now],
               "symbol": symbol, "funding": 0.0, "oi_df": None}

        btc_bull = None
        if btc_trend_series is not None:
            prior = btc_trend_series[btc_trend_series.index <= t_now]
            if len(prior):
                btc_bull = bool(prior.iloc[-1])

        sig = analyze_symbol(sub, btc_bull=btc_bull)
        if not sig or sig["score"] < SCORE_STRONG:
            continue

        fut_h = df15["high"].iloc[i + 1:i + 1 + horizon_bars].to_numpy()
        fut_l = df15["low"].iloc[i + 1:i + 1 + horizon_bars].to_numpy()
        fut_c = df15["close"].iloc[i + 1:i + 1 + horizon_bars].to_numpy()
        entry = sig["price"]
        stop = sig["stop"]

        tp1_hit = tp2_hit = stop_hit = False
        first_event = None
        exit_price = None

        for j in range(len(fut_h)):
            hi, lo = fut_h[j], fut_l[j]
            if sig["direction"] == "LONG":
                if lo <= stop:
                    stop_hit = True; first_event = "STOP"; exit_price = stop; break
                if hi >= sig["tp1"] and not tp1_hit:
                    tp1_hit = True
                    if first_event is None: first_event = "TP1"; exit_price = sig["tp1"]
                if hi >= sig["tp2"]:
                    tp2_hit = True
                    if first_event is None: first_event = "TP2"
                    exit_price = sig["tp2"]; break
            else:
                if hi >= stop:
                    stop_hit = True; first_event = "STOP"; exit_price = stop; break
                if lo <= sig["tp1"] and not tp1_hit:
                    tp1_hit = True
                    if first_event is None: first_event = "TP1"; exit_price = sig["tp1"]
                if lo <= sig["tp2"]:
                    tp2_hit = True
                    if first_event is None: first_event = "TP2"
                    exit_price = sig["tp2"]; break

        if first_event is None and len(fut_c):
            first_event = "TIMEOUT"
            exit_price = float(fut_c[-1])

        if exit_price is None:
            pnl_pct = 0.0
        elif sig["direction"] == "LONG":
            pnl_pct = (exit_price - entry) / entry * 100
        else:
            pnl_pct = (entry - exit_price) / entry * 100

        rows.append({
            "time": t_now, "dir": sig["direction"], "score": sig["score"],
            "tp1": tp1_hit, "tp2": tp2_hit, "stop": stop_hit,
            "first": first_event,
            "pnl_pct": round(pnl_pct, 3),
        })
    return pd.DataFrame(rows)


def diagnose(data: dict) -> dict:
    df60 = data.get("df_60"); df240 = data.get("df_240"); df15 = data.get("df_15")
    if df60 is None or df240 is None or len(df60) < 60 or len(df240) < 40:
        return {"ok": False, "neden": "yetersiz veri"}
    k240 = ind.kalman_trend(df240["close"])
    q15 = ind.qqe(df15["close"]) if df15 is not None and len(df15) > 20 else None
    bull_240 = bool(k240["kalman_above"].iloc[-1])
    bear_240 = not bull_240
    reasons = []
    if not (bull_240 or bear_240):
        reasons.append("4s trend belirsiz")
    if q15 is not None:
        fresh_up = bool(q15["qqe_fresh_up"].iloc[-1])
        fresh_dn = bool(q15["qqe_fresh_dn"].iloc[-1])
        if not (fresh_up or fresh_dn):
            reasons.append("QQE momentum donusu yok")
    return {"ok": not reasons, "neden": "; ".join(reasons) if reasons else "kosullar uygun"}
