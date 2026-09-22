# -*- coding: utf-8 -*-
"""
Indikator kutuphanesi - saf pandas/numpy, TA-Lib gerektirmez.
RSI tek basina kullanilmaz; momentum teyidi QQE uzerinden alinir.
"""
import numpy as np
import pandas as pd


# ---------- Temel yardimcilar ----------
def wilder_smooth(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(alpha=1.0 / n, min_periods=n, adjust=False).mean()


def ema(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(span=n, adjust=False).mean()


def atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    h, l, c = df["high"], df["low"], df["close"]
    pc = c.shift(1)
    tr = pd.concat([h - l, (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
    return wilder_smooth(tr, n)


# ---------- Kalman Trend Filtresi ----------
# 1-boyutlu sabit-hiz Kalman: fiyatin "seviye" ve "egim"ini ayrik gurultuden ayirir.
# cikti: kalman_slope (trend yonu/gucu), kalman_slope_norm (normalize)
def kalman_trend(close: pd.Series, q: float = 0.01, r: float = 0.5) -> pd.DataFrame:
    c = close.to_numpy(dtype=float)
    n = len(c)
    level = np.full(n, np.nan)
    slope = np.full(n, np.nan)
    # durum: [seviye, egim]
    x = np.array([c[0], 0.0])
    P = np.eye(2) * 10.0
    F = np.array([[1.0, 1.0], [0.0, 1.0]])
    H = np.array([[1.0, 0.0]])
    Q = np.array([[q, 0.0], [0.0, q]])
    R = np.array([[r]])
    for i in range(n):
        x = F @ x
        P = F @ P @ F.T + Q
        y = c[i] - (H @ x)[0]
        S = (H @ P @ H.T + R)[0, 0]
        K = (P @ H.T) / S
        x = x + K.flatten() * y
        P = (np.eye(2) - np.outer(K, H)) @ P
        level[i], slope[i] = x
    out = pd.DataFrame({"kalman_level": level, "kalman_slope": slope}, index=close.index)
    # normalize egim: fiyatin yuzde kaci kadar egim var (momentum siddeti)
    eps = 1e-9
    out["kalman_slope_pct"] = out["kalman_slope"] / (np.abs(out["kalman_level"]) + eps) * 100.0
    out["kalman_above"] = close.to_numpy(dtype=float) > out["kalman_level"]
    return out


# ---------- QQE Momentum (RSI'nin duzgunlesmis + ATR bantli hali) ----------
def qqe(close: pd.Series, rsi_len: int = 14, smooth: int = 5,
        q_len: int = 14, factor: float = 4.236) -> pd.DataFrame:
    delta = close.diff()
    up = delta.clip(lower=0.0)
    dn = (-delta).clip(lower=0.0)
    ru = wilder_smooth(up, rsi_len)
    rd = wilder_smooth(dn, rsi_len)
    rs = ru / (rd + 1e-9)
    rsi = 100.0 - 100.0 / (1.0 + rs)

    rsi_ma = ema(rsi, smooth)
    rsi_tr = rsi_ma.diff().abs()
    rsi_atr = wilder_smooth(rsi_tr, q_len)
    upper = rsi_ma + factor * rsi_atr
    lower = rsi_ma - factor * rsi_atr

    out = pd.DataFrame({
        "rsi": rsi, "qqe_rsi": rsi_ma, "qqe_upper": upper, "qqe_lower": lower,
    }, index=close.index)
    # Momentum donusu: qqe_rsi alt banti yukari keserse LONG uyaran,
    # ust banti asagi keserse SHORT uyaran. "Taze kesisme" son 3 barda mi?
    cross_up = (out["qqe_rsi"] > out["qqe_lower"]) & (out["qqe_rsi"].shift(1) <= out["qqe_lower"].shift(1))
    cross_dn = (out["qqe_rsi"] < out["qqe_upper"]) & (out["qqe_rsi"].shift(1) >= out["qqe_upper"].shift(1))
    out["qqe_cross_up"] = cross_up
    out["qqe_cross_dn"] = cross_dn
    out["qqe_fresh_up"] = cross_up.rolling(3, min_periods=1).max().astype(bool)
    out["qqe_fresh_dn"] = cross_dn.rolling(3, min_periods=1).max().astype(bool)
    out["qqe_bull_zone"] = out["qqe_rsi"] > 50
    return out


# ---------- Hacim ----------
def volume_signals(df: pd.DataFrame) -> pd.DataFrame:
    vol = df["volume"]
    vol_sma = vol.rolling(20, min_periods=5).mean()
    spike = vol > 1.8 * vol_sma
    obv = (np.sign(df["close"].diff()).fillna(0) * vol).cumsum()
    obv_slope = obv.diff(5)
    out = pd.DataFrame({
        "vol_spike": spike,
        "vol_ratio": vol / (vol_sma + 1e-9),
        "obv_rising": obv_slope > 0,
    }, index=df.index)
    return out


# ---------- ADX (trend siddeti) ----------
def adx(df: pd.DataFrame, n: int = 14) -> pd.DataFrame:
    h, l, c = df["high"], df["low"], df["close"]
    up_move = h.diff()
    dn_move = -l.diff()
    plus_dm = np.where((up_move > dn_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((dn_move > up_move) & (dn_move > 0), dn_move, 0.0)
    pc = c.shift(1)
    tr = pd.concat([h - l, (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
    atr_ = wilder_smooth(tr, n)
    plus_di = 100 * wilder_smooth(pd.Series(plus_dm, index=df.index), n) / (atr_ + 1e-9)
    minus_di = 100 * wilder_smooth(pd.Series(minus_dm, index=df.index), n) / (atr_ + 1e-9)
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di + 1e-9)
    adx_ = wilder_smooth(dx, n)
    return pd.DataFrame({"adx": adx_, "plus_di": plus_di, "minus_di": minus_di}, index=df.index)


# ---------- VWAP (gunluk oturum) ----------
def vwap(df: pd.DataFrame) -> pd.Series:
    tp = (df["high"] + df["low"] + df["close"]) / 3.0
    v = df["volume"]
    day = df.index.floor("D")
    pv = (tp * v).groupby(day).cumsum()
    vv = v.groupby(day).cumsum()
    return pv / (vv + 1e-9)


# ---------- Destek / Direnc ----------
def strong_sr(df: pd.DataFrame, left: int = 3, right: int = 3,
              lookback: int = 96) -> dict:
    """
    Son 'lookback' 15d bar (24s = ~1gun, 96 = ~1gun) icindeki swing high/low'lardan
    en az 2 dokunmus seviyeleri dondurur + onceki gun H/L/C + haftalik acilis.
    """
    d = df.iloc[-lookback:].copy()
    highs = d["high"].to_numpy()
    lows = d["low"].to_numpy()

    def swings(arr, is_high):
        lv = []
        for i in range(left, len(arr) - right):
            w = arr[i - left:i + right + 1]
            if is_high and arr[i] == w.max():
                lv.append(arr[i])
            if not is_high and arr[i] == w.min():
                lv.append(arr[i])
        return lv

    sh = swings(highs, True)
    sl = swings(lows, False)

    def cluster(levels, tol=0.0015):
        cl = []
        for x in levels:
            placed = False
            for c in cl:
                if abs(c["price"] - x) / x < tol:
                    c["touches"] += 1
                    c["price"] = (c["price"] * (c["touches"] - 1) + x) / c["touches"]
                    placed = True
                    break
            if not placed:
                cl.append({"price": x, "touches": 1})
        return [c for c in cl if c["touches"] >= 2]

    res = cluster(sh)
    sup = cluster(sl)
    last = df["close"].iloc[-1]
    prev_day = df.iloc[-96:] if len(df) >= 96 else df
    pd_high = prev_day["high"].max()
    pd_low = prev_day["low"].min()
    # haftalik acilis (UTC pazartesi)
    # haftalik acilis: UTC pazartesi 00:00'dan sonraki ilk bar
    week_key = (df.index - pd.to_timedelta((df.index.dayofweek), unit="D")).floor("D")
    week_open = df.groupby(week_key)["open"].first().iloc[-1]
    return {
        "supports": sorted(sup, key=lambda c: abs(c["price"] - last)),
        "resists": sorted(res, key=lambda c: abs(c["price"] - last)),
        "pd_high": pd_high, "pd_low": pd_low,
        "week_open": week_open, "last": last,
    }
