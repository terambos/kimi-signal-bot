# -*- coding: utf-8 -*-
"""Mail bildirimi (Gmail SMTP, ucretsiz) + dosya loglama."""
import csv
import os
import smtplib
from datetime import datetime, timezone
from email.mime.text import MIMEText
from email.header import Header

from config import (SMTP_SERVER, SMTP_PORT, MAIL_FROM, MAIL_TO,
                    GMAIL_APP_PASSWORD, LOG_DIR, SIGNAL_LOG, TRADE_LOG,
                    MAIL_ON_STRONG, SCORE_STRONG)


def _smtp_send(subject: str, html: str) -> bool:
    if "UYGULAMA_SIFRESI" in GMAIL_APP_PASSWORD or "GMAIL_ADRESIN" in MAIL_FROM:
        print("[MAIL] config.py icinde mail ayarlari bos - mail atlaniyor, "
              "konsola yaziyorum.")
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


def send_signal_mail(sig: dict, news_ctx: list) -> None:
    if not MAIL_ON_STRONG:
        return
    subject = "SINYAL %s %s | Skor %d | Giris %s" % (
        sig["direction"], sig["symbol"], sig["score"], sig["price"])
    news_html = ""
    if news_ctx:
        items = "".join("<li>%s</li>" % n for n in news_ctx[:5])
        news_html = "<h4>Baglam (haber akisi):</h4><ul>%s</ul>" % items
    html = """
    <html><body style="font-family:Arial;background:#111;color:#eee;padding:16px">
    <h2 style="color:#f7931a">%s %s &nbsp;|&nbsp; Guven: %d/100</h2>
    <table border="1" cellpadding="8" style="border-collapse:collapse;background:#1c1c1c">
      <tr><td>Guncel fiyat</td><td><b>%s</b></td></tr>
      <tr><td>Referans giris bolgesi (S/R)</td><td><b>%s</b></td></tr>
      <tr><td>TP1</td><td style="color:#7CFC00"><b>%s</b> (min %%4-5 hedefi)</td></tr>
      <tr><td>TP2</td><td style="color:#7CFC00"><b>%s</b> (min %%9-10 hedefi)</td></tr>
      <tr><td>ATR(1s)</td><td>%s &nbsp;|&nbsp; ATR(15dk): %s</td></tr>
      <tr><td>ADX</td><td>%s</td></tr>
      <tr><td>Funding</td><td>%s%%</td></tr>
      <tr><td>OI degisimi (1s)</td><td>%s%%</td></tr>
      <tr><td>Hacim orani</td><td>x%s</td></tr>
    </table>
    <h4>Gerekceler:</h4><ul>%s</ul>
    %s
    <p style="color:#aaa;font-size:12px">Stop-loss bu sistemde hesaplanmaz - riski sen belirle.
    Saatlik tarama: 15dk zaman diliminde calisir. Bu bir karar destek aracidir, yatirim tavsiyesi degildir.</p>
    </body></html>
    """ % (sig["direction"], sig["symbol"], sig["score"], sig["price"],
           sig["entry_zone"], sig["tp1"], sig["tp2"],
           sig["atr1h"], sig["atr15"], sig["adx"], round(sig["funding"] * 100, 4),
           sig["oi_chg_1h"], sig["vol_ratio"],
           "".join("<li>%s</li>" % r for r in sig["reasons"]), news_html)
    ok = _smtp_send(subject, html)
    print("[SINYEL MAILI]", "gonderildi" if ok else "(mail ayarli degil)", sig["symbol"], sig["direction"], sig["score"])


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
                        "tp1", "tp2", "score", "adx", "funding", "oi_chg_1h",
                        "vol_ratio", "reasons"])
        w.writerow([datetime.now(timezone.utc).isoformat(), sig["symbol"],
                    sig["direction"], sig["price"], sig["entry_zone"], sig["tp1"],
                    sig["tp2"], sig["score"], sig["adx"], sig["funding"],
                    sig["oi_chg_1h"], sig["vol_ratio"],
                    " | ".join(sig["reasons"])])
