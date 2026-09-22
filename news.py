# -*- coding: utf-8 -*-
"""Ucretsiz RSS haber akisi (API key yok). Coin eslestirme + basit guven.
Skora dahil EDILMEZ - sadece sinyal mailinde 'baglam' olarak gosterilir."""
import re
import time
import feedparser

from config import NEWS_RSS, COINS, NEWS_CACHE_MIN

_cache = {"ts": 0.0, "items": []}


def get_news() -> list:
    """Donen liste: {"title":..., "source":..., "coins":[...]}"""
    now = time.time()
    if now - _cache["ts"] < NEWS_CACHE_MIN * 60 and _cache["items"]:
        return _cache["items"]
    items = []
    pat = re.compile(r"\b(%s)\b" % "|".join(re.escape(c) for c in COINS + ["bitcoin", "ethereum"]))
    for url in NEWS_RSS:
        try:
            feed = feedparser.parse(url)
            for e in feed.entries[:15]:
                text = (e.get("title", "") + " " + e.get("summary", "")).lower()
                hits = sorted(set(m.lower() for m in pat.findall(text)))
                alias = {"bitcoin": "BTC", "ethereum": "ETH"}
                coins = sorted({alias.get(h, h.upper()) for h in hits})
                if coins:
                    items.append({"title": e.get("title", ""),
                                  "source": feed.feed.get("title", url),
                                  "coins": coins})
        except Exception:
            continue
    _cache["ts"] = now
    _cache["items"] = items[:40]
    return _cache["items"]


def context_for(symbol: str) -> list:
    coin = symbol.replace("USDT", "")
    return [f'[{i["source"]}] {i["title"]}' for i in get_news() if coin in i.get("coins", [])]
