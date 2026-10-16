# -*- coding: utf-8 -*-
"""Mail bildirimi (Gmail SMTP) + dosya loglama."""
import csv
import os
import smtplib
from datetime import datetime, timezone
from email.mime.text import MIMEText
from email.header import Header

from config import (SMTP_SERVER, SMTP_PORT, MAIL_FROM, MAIL_TO,
                    GMAIL_APP_PASSWORD, LOG_DIR, SIGNAL_LOG, TRADE_LOG,
                    MAIL_ON_STRONG, SCORE_STRONG, STOP_PCT,
                    TP1_MIN_PCT, TP2_MIN_PCT)


def _smtp_send(subject: str, html: str) -> bool:
    if not GMAIL_APP_PASSWORD or not MAIL_FROM:
        print("[MAIL] mail ayarlari bos - konsola yaziyorum.")
        print("=====", subject, "=====")
        return False
    try:
        msg = MIMEText(html, "html", "utf-8")
        msg["Subject"] = Header(subject, "utf-8")
        msg["From"] = MAIL_FROM
        msg["To"] = MAIL_TO
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, timeout=20) as s:
            s.login(MAIL_FROM, GMAIL_APP_PASSWORD)
            s.sendmail(MAIL_FROM, [MAIL_TO], msg.as_string())
        return True
    except Exception as e:
        print("[MAIL HATASI]", e)
        return False


def _pct_str(x: float) -> str:
    return "%+.2f%%" % (x * 100)


def _vol_label(ratio: float) -> str:
    if ratio >= 2.0:
        return "guclu (patlama)"
    if ratio >= 1.2:
        return "orta"
    return "zayif"


def _oi_label(chg_pct: float) -> str:
    if chg_pct >= 0.5:
        return "artiyor (para giriyor)"
    if chg_pct <= -0.5:
        return "azaliyor (pozisyon kapaniyor)"
    return "notr"


def _funding_label(f: float) -> str:
    if f > 0.0005:
        return "asiri long (kalabalik)"
    if f < -0.0005:
        return "asiri short (kalabalik)"
    return "notr"


def send_signal_mail(sig: dict, news_ctx: list) -> None:
    if not MAIL_ON_STRONG:
        return
    subject = "SINYAL %s %s | Skor %d | Giris %s" % (
        sig["direction"], sig["symbol"], sig["score"], sig["price"])

    news_html = ""
    if news_ctx:
        items = "".join("<li>%s</li>" % n for n in news_ctx[:5])
        news_html = "<h4>Baglam (haber akisi):</h4><ul>%s</ul>" % items

    # S/R referans blogu
    entry_zone = sig.get("entry_zone")
    if entry_zone and abs(entry_zone - sig["price"]) / sig["price"] > 0.0005:
        sr_row = '<tr><td>Referans giris bolgesi (S/R)</td><td><b>%s</b></td></tr>' % entry_zone
    else:
        sr_row = '<tr><td>Referans giris bolgesi (S/R)</td><td>yakin S/R yok</td></tr>'

    # TP metinleri (config'ten okunur)
    tp1_text = "min %%%s hedefi" % round(TP1_MIN_PCT * 100, 1)
    tp2_text = "min %%%s hedefi" % round(TP2_MIN_PCT * 100, 1)

    html = """
    <html><body style="font-family:Arial;background:#111;color:#eee;padding:16px">
    <h2 style="color:#f7931a">%s %s &nbsp;|&nbsp; Guven: %d/100</h2>
    <table border="1" cellpadding="8" style="border-collapse:collapse;background:#1c1c1c">
      <tr><td>Guncel fiyat</td><td><b>%s</b></td></tr>
      %s
      <tr><td>TP1</td><td style="color:#7CFC00"><b>%s</b> (%s)</td></tr>
      <tr><td>TP2</td><td style="color:#7CFC00"><b>%s</b> (%s)</td></tr>
      <tr><td>Stop</td><td style="color:#ff6b6b"><b>%s</b> (%s)</td></tr>
      <tr><td>ATR(1s)</td><td>%s &nbsp;|&nbsp; ATR(15dk): %s</td></tr>
      <tr><td>ADX</td><td>%s</td></tr>
      <tr><td>Funding</td><td>%s%% (%s)</td></tr>
      <tr><td>OI degisimi (1s)</td><td>%s%% (%s)</td></tr>
      <tr><td>Hacim orani</td><td>x%s (%s)</td></tr>
    </table>
    <h4>Gerekceler:</h4><ul>%s</ul>
    %s
    <p style="color:#aaa;font-size:12px">
      Stop: giris fiyatindan %%%s uzakta. TP1: %%%s, TP2: %%%s.<br>
      Kaldirac/pozisyon buyuklugunu kendin belirle. Bu bir karar destek aracidir, yatirim tavsiyesi degildir.
    </p>
    </body></html>
    """ % (sig["direction"], sig["symbol"], sig["score"], sig["price"],
           sr_row,
           sig["tp1"], tp1_text,
           sig["tp2"], tp2_text,
           sig["stop"], _pct_str(-STOP_PCT),
           sig["atr1h"], sig["atr15"], sig["adx"],
           round(sig["funding"] * 100, 4), _funding_label(sig["funding"]),
           sig["oi_chg_1h"], _oi_label(sig["oi_chg_1h"]),
           sig["vol_ratio"], _vol_label(sig["vol_ratio"]),
           "".join("<li>%s</li>" % r for r in sig["reasons"]),
           news_html,
           round(STOP_PCT * 100, 1), round(TP1_MIN_PCT * 100, 1), round(TP2_MIN_PCT * 100, 1))

    ok = _smtp_send(subject, html)
    print("[SINYEL MAILI]", "gonderildi" if ok else "(mail ayarli degil)",
          sig["symbol"], sig["direction"], sig["score"])


def send_digest_mail(rows: list, news: list) -> None:
    if not rows:
        subject = "Saatlik Ozet: Guclu sinyal yok"
        body = "<html><body><p>Son taramada skor %d uzeri sinyal yok. Piyasa sakin.</p></body></html>" % SCORE_STRONG
    else:
        subject = "Saatlik Ozet: %d guclu sinyal" % len(rows)
        trs = "".join(
            "<tr><td>%s</td><td>%s</td><td>%d</td><td>%s</td><td>%s</td><td>%s</td></tr>" % (
                r["direction"], r["symbol"], r["score"], r["price"], r["tp1"], r["tp2"])
            for r in rows)
        body = ("<html><body style='font-family:Arial'>"
                "<h3>Son saatin guclu sinyalleri</h3>"
                "<table border='1' cellpadding='6'><tr><th>Yon</th><th>Sembol</th>"
                "<th>Skor</th><th>Fiyat</th><th>TP1</th><th>TP2</th></tr>%s</table>"
                "</body></html>") % trs
    _smtp_send(subject, body)
    print("[DIGEST]", subject)


def log_signal(sig: dict):
    os.makedirs(LOG_DIR, exist_ok=True)
    new = not os.path.exists(SIGNAL_LOG)
    with open(SIGNAL_LOG, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["time", "symbol", "direction", "price", "entry_zone",
                        "tp1", "tp2", "stop", "score", "adx", "funding",
                        "oi_chg_1h", "vol_ratio", "reasons"])
        w.writerow([datetime.now(timezone.utc).isoformat(), sig["symbol"],
                    sig["direction"], sig["price"], sig["entry_zone"], sig["tp1"],
                    sig["tp2"], sig["stop"], sig["score"], sig["adx"], sig["funding"],
                    sig["oi_chg_1h"], sig["vol_ratio"],
                    " | ".join(sig["reasons"])])
