#!/usr/bin/env python3
"""JARVIS Bankterminalen — Yahoo Finance API"""

import requests
from datetime import datetime, timezone, timedelta

STOCKS = [
    {"ticker": "NDA-SE",  "name": "Nordea Bank",        "yf": "NDA-SE.ST",  "noll": 175.25, "antal": 570,  "investerat": 99892.50},
    {"ticker": "SHB-A",   "name": "Handelsbanken A",     "yf": "SHB-A.ST",   "noll": 135.15, "antal": 740,  "investerat": 100011.00},
    {"ticker": "SHB-B",   "name": "Handelsbanken B",     "yf": "SHB-B.ST",   "noll": 224.20, "antal": 446,  "investerat": 99993.20},
    {"ticker": "SEB-A",   "name": "SEB A",               "yf": "SEB-A.ST",   "noll": 184.00, "antal": 543,  "investerat": 99912.00},
    {"ticker": "SEB-C",   "name": "SEB C",               "yf": "SEB-C.ST",   "noll": 188.20, "antal": 531,  "investerat": 99934.20},
    {"ticker": "SWED-A",  "name": "Swedbank A",          "yf": "SWED-A.ST",  "noll": 336.10, "antal": 297,  "investerat": 99821.70},
    {"ticker": "AZA",     "name": "Avanza Bank Holding", "yf": "AZA.ST",     "noll": 358.10, "antal": 279,  "investerat": 99909.90},
]

FALLBACK = {
    "NDA-SE": (178.00, 2.12),
    "SHB-A":  (138.35, 2.63),
    "SHB-B":  (230.00, 2.04),
    "SEB-A":  (188.90, 3.14),
    "SEB-C":  (195.00, 2.96),
    "SWED-A": (347.90, 2.69),
    "AZA":    (379.20, 7.70),
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; JARVIS/1.0)",
    "Accept": "application/json",
}

def fetch_stock(stock):
    try:
        url = "https://query1.finance.yahoo.com/v8/finance/chart/" + stock["yf"] + "?interval=1d&range=1d"
        r = requests.get(url, headers=HEADERS, timeout=10)
        r.raise_for_status()
        d = r.json()
        meta = d["chart"]["result"][0]["meta"]
        price = float(meta.get("regularMarketPrice") or meta.get("previousClose") or 0)
        prev = float(meta.get("previousClose") or meta.get("chartPreviousClose") or 0)
        day_pct = ((price - prev) / prev * 100) if prev > 0 else 0.0
        if price > 0:
            print("  " + stock["ticker"] + ": " + str(price) + " SEK [LIVE]")
            return price, day_pct, "LIVE"
    except Exception as e:
        print("  FEL vid " + stock["ticker"] + ": " + str(e))
    fb = FALLBACK[stock["ticker"]]
    print("  " + stock["ticker"] + ": " + str(fb[0]) + " SEK [FALLBACK]")
    return fb[0], fb[1], "FALLBACK"

def sek(n):
    return "{:,.0f}".format(abs(n)).replace(",", " ")

def pct(n, d=2):
    return ("+" if n >= 0 else "") + "{:.{}f}%".format(n, d)

def generate_html(results):
    total_inv    = sum(r["investerat"] for r in results)
    total_varde  = sum(r["varde"]      for r in results)
    total_pl     = total_varde - total_inv
    total_pl_pct = (total_pl / total_inv) * 100
    live_count = sum(1 for r in results if r["status"] == "LIVE")
    best  = max(results, key=lambda r: r["vs_noll_pct"])
    worst = min(results, key=lambda r: r["vs_noll_pct"])
    max_pl = max(abs(r["pl_pct"]) for r in results) or 1
    stockholm = timezone(timedelta(hours=2))
    now      = datetime.now(stockholm)
    upd_time = now.strftime("%H:%M:%S")
    upd_date = now.strftime("%-d %b %Y")
    if live_count == 7:
        dot  = "#00ff88"
        stxt = "7/7 live · Stockholmsbörsen · " + upd_date
    elif live_count == 0:
        dot  = "#ff1744"
        stxt = "0/7 live · FALLBACK · " + upd_date
    else:
        dot  = "#ffa726"
        stxt = str(live_count) + "/7 live · " + upd_date
    pl_cls  = "pos" if total_pl >= 0 else "neg"
    pl_sign = "+" if total_pl >= 0 else "−"
    rows = ""
    for r in results:
        bc   = "badge-live" if r["status"] == "LIVE" else "badge-fallback"
        bt   = "LIVE"       if r["status"] == "LIVE" else "FALLBACK"
        dstr = pct(r["day_pct"]) if r["day_pct"] is not None else "–"
        dcls = ("pos" if r.get("day_pct", 0) >= 0 else "neg") if r["day_pct"] is not None else "neutral"
        vcls = "pos" if r["vs_noll_pct"] >= 0 else "neg"
        pcls = "pos" if r["pl"] >= 0 else "neg"
        bar  = "{:.1f}".format(min(100, abs(r["pl_pct"]) / max_pl * 100))
        bcol = "#00ff88" if r["pl"] >= 0 else "#ff1744"
        psign = "+" if r["pl"] >= 0 else "−"
        pstr = "{:,.2f}".format(r["price"]).replace(",", " ").replace(".", ",")
        nstr = "{:,.2f}".format(r["noll"]).replace(",",  " ").replace(".", ",")
        rows += ("\n    <tr>\n      <td>" + r["ticker"] + " " + bt + "<br>" + r["name"] + "</td>\n      <td>" + nstr + "</td>\n      <td>" + pstr + "</td>\n      <td>" + dstr + "</td>\n      <td>" + pct(r["vs_noll_pct"]) + "</td>\n      <td>" + psign + sek(r["pl"]) + "</td>\n    </tr>")
    tv  = "{:,.0f}".format(total_varde).replace(",", " ")
    ti  = "{:,.0f}".format(total_inv).replace(",",   " ")
    tpl_pct = "{:.2f}".format(abs(total_pl_pct))
    html = "<!DOCTYPE html><html><head><title>JARVIS</title></head><body><h1>JARVIS</h1><p>Total: " + tv + " kr, P&L: " + pl_sign + sek(total_pl) + " kr (" + pl_sign + tpl_pct + "%)</p><table>" + rows + "</table></body></html>"
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)

def main():
    results = []
    for stock in STOCKS:
        print("Hämtar " + stock["ticker"] + "...")
        price, day_pct, status = fetch_stock(stock)
        varde       = price * stock["antal"]
        pl          = varde - stock["investerat"]
        pl_pct      = (pl / stock["investerat"]) * 100
        vs_noll_pct = (price - stock["noll"]) / stock["noll"] * 100
        results.append(dict(stock,
            price=price, day_pct=day_pct, status=status,
            varde=varde, pl=pl, pl_pct=pl_pct, vs_noll_pct=vs_noll_pct,
        ))
    generate_html(results)
    print("index.html klar!")

if __name__ == "__main__":
    main()
