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
            print("  " + stock["ticker"] + ": " + str(price) + " SEK dag: " + str(round(day_pct, 2)) + "% [LIVE]")
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
    pl_sign = "+" if total_pl >= 0 else "+"

    rows = ""
    for r in results:
        bc   = "badge-live" if r["status"] == "LIVE" else "badge-fallback"
        bt   = "LIVE"       if r["status"] == "LIVE" else "FALLBACK"
        dstr = pct(r["day_pct"]) if r["day_pct"] is not None else "-"
        dcls = ("pos" if r.get("day_pct", 0) >= 0 else "neg") if r["day_pct"] is not None else "neutral"
        vcls = "pos" if r["vs_noll_pct"] >= 0 else "neg"
        pcls = "pos" if r["pl"] >= 0 else "neg"
        bar  = "{:.1f}".format(min(100, abs(r["pl_pct"]) / max_pl * 100))
        bcol = "#00ff88" if r["pl"] >= 0 else "#ff1744"
        psign = "+" if r["pl"] >= 0 else "-"
        pstr = "{:,.2f}".format(r["price"]).replace(",", " ").replace(".", ",")
        nstr = "{:,.2f}".format(r["noll"]).replace(",",  " ").replace(".", ",")
        rows += (
            "\n    <tr>"
            + "\n      <td><div class=\"ticker-name\">" + r["ticker"]
            + " <span class=\"badge " + bc + "\">" + bt + "</span></div>"
            + "\n      <div class=\"stock-fullname\">" + r["name"] + "</div></td>"
            + "\n      <td>" + nstr + "</td>"
            + "\n      <td><strong style=\"color:#e0f4ff;\">" + pstr + "</strong></td>"
            + "\n      <td class=\"" + dcls + "\">" + dstr + "</td>"
            + "\n      <td class=\"" + vcls + "\">" + pct(r["vs_noll_pct"]) + "</td>"
            + "\n      <td class=\"" + pcls + "\">" + psign + sek(r["pl"]) + "</td>"
            + "\n      <td><div class=\"bar-wrap\"><div class=\"bar-bg\">"
            + "<div class=\"bar-fill\" style=\"width:" + bar + "%;background:" + bcol + ";\"></div>"
            + "</div></div></td>"
            + "\n    </tr>"
        )

    tv  = "{:,.0f}".format(total_varde).replace(",", " ")
    ti  = "{:,.0f}".format(total_inv).replace(",",   " ")
    tpl_pct = "{:.2f}".format(abs(total_pl_pct))

    css = (
        "*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}\n"
        "body{background:#050c12;color:#a0c8d8;font-family:'Share Tech Mono',monospace;"
        "min-height:100vh;position:relative;overflow-x:hidden}\n"
        "body::before{content:'';position:fixed;inset:0;"
        "background:repeating-linear-gradient(0deg,transparent 2px,rgba(0,229,255,0.015) 2px 4px);"
        "pointer-events:none;z-index:1000}\n"
        "body::after{content:'';position:fixed;inset:0;"
        "background:radial-gradient(ellipse at center,transparent 60%,rgba(0,0,0,0.6) 100%);"
        "pointer-events:none;z-index:999}\n"
        ".container{max-width:1300px;margin:0 auto;padding:24px 20px 40px;position:relative;z-index:1}\n"
        ".header{text-align:center;margin-bottom:20px;"
        "border-bottom:1px solid rgba(0,229,255,0.2);padding-bottom:16px}\n"
        ".logo{font-family:'Orbitron',sans-serif;font-size:2.8rem;font-weight:900;color:#00e5ff;"
        "letter-spacing:0.3em;text-shadow:0 0 20px rgba(0,229,255,0.5)}\n"
        ".subtitle{font-size:0.85rem;color:rgba(0,229,255,0.6);letter-spacing:0.2em;"
        "margin-top:4px;text-transform:uppercase}\n"
        ".statusbar{display:flex;justify-content:space-between;align-items:center;"
        "background:rgba(0,229,255,0.04);border:1px solid rgba(0,229,255,0.15);"
        "border-radius:4px;padding:8px 16px;margin-bottom:20px;font-size:0.78rem;letter-spacing:0.05em}\n"
        ".status-left{display:flex;align-items:center;gap:8px}\n"
        ".status-dot{width:8px;height:8px;border-radius:50%;background:#00ff88;"
        "box-shadow:0 0 6px #00ff88;flex-shrink:0}\n"
        ".status-text{color:#00ff88}\n"
        ".status-right{color:rgba(0,229,255,0.7)}\n"
        ".cards{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:20px}\n"
        ".card{background:rgba(0,229,255,0.04);border:1px solid rgba(0,229,255,0.18);"
        "border-radius:6px;padding:14px 16px}\n"
        ".card-label{font-size:0.68rem;color:rgba(0,229,255,0.5);text-transform:uppercase;"
        "letter-spacing:0.12em;margin-bottom:6px}\n"
        ".card-value{font-size:1.25rem;color:#00e5ff}\n"
        ".card-sub{font-size:0.75rem;margin-top:2px}\n"
        ".pos{color:#00ff88}.neg{color:#ff1744}.neutral{color:#a0c8d8}\n"
        ".table-wrap{overflow-x:auto}\n"
        "table{width:100%;border-collapse:collapse;font-size:0.82rem}\n"
        "thead tr{border-bottom:1px solid rgba(0,229,255,0.3)}\n"
        "th{padding:10px 10px 8px;text-align:right;font-size:0.65rem;color:rgba(0,229,255,0.5);"
        "text-transform:uppercase;letter-spacing:0.1em;white-space:nowrap}\n"
        "th:first-child{text-align:left}\n"
        "td{padding:11px 10px;text-align:right;"
        "border-bottom:1px solid rgba(0,229,255,0.07);vertical-align:middle;white-space:nowrap}\n"
        "td:first-child{text-align:left}\n"
        "tbody tr:hover{background:rgba(0,229,255,0.04)}\n"
        ".ticker-name{font-family:'Orbitron',sans-serif;font-size:0.85rem;font-weight:700;"
        "color:#00e5ff;display:flex;align-items:center;gap:8px}\n"
        ".badge{font-family:'Share Tech Mono',monospace;font-size:0.6rem;"
        "padding:2px 6px;border-radius:3px;letter-spacing:0.05em}\n"
        ".badge-live{background:rgba(0,255,136,0.15);color:#00ff88;"
        "border:1px solid rgba(0,255,136,0.4)}\n"
        ".badge-fallback{background:rgba(255,167,38,0.15);color:#ffa726;"
        "border:1px solid rgba(255,167,38,0.4)}\n"
        ".stock-fullname{font-size:0.68rem;color:rgba(0,229,255,0.4);margin-top:2px}\n"
        ".bar-wrap{display:flex;align-items:center;justify-content:flex-end}\n"
        ".bar-bg{width:80px;height:6px;background:rgba(255,255,255,0.06);"
        "border-radius:3px;overflow:hidden}\n"
        ".bar-fill{height:100%;border-radius:3px}\n"
        ".total-row td{border-top:1px solid rgba(0,229,255,0.3);border-bottom:none;"
        "color:#00e5ff;font-size:0.85rem;padding-top:14px}\n"
        ".footer{margin-top:24px;text-align:center;font-size:0.65rem;"
        "color:rgba(0,229,255,0.25);letter-spacing:0.1em;text-transform:uppercase}\n"
    )

    html = (
        "<!DOCTYPE html>\n<html lang=\"sv\">\n<head>\n"
        "<meta charset=\"UTF-8\">\n"
        "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1.0\">\n"
        "<meta http-equiv=\"refresh\" content=\"900\">\n"
        "<title>J.A.R.V.I.S. - Bankterminalen</title>\n"
        "<link href=\"https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900"
        "&family=Share+Tech+Mono&display=swap\" rel=\"stylesheet\">\n"
        "<style>\n" + css + "</style>\n</head>\n<body>\n"
        "<div class=\"container\">\n"
        "  <div class=\"header\">\n"
        "    <div class=\"logo\">J.A.R.V.I.S.</div>\n"
        "    <div class=\"subtitle\">Bankterminalen · Live Portföljövervakning</div>\n"
        "  </div>\n"
        "  <div class=\"statusbar\">\n"
        "    <div class=\"status-left\">\n"
        "      <div class=\"status-dot\"></div>\n"
        "      <span class=\"status-text\">" + stxt + "</span>\n"
        "    </div>\n"
        "    <div class=\"status-right\">Senast uppdaterad: " + upd_date + " " + upd_time
        + " · Auto-refresh om 15 min</div>\n"
        "  </div>\n"
        "  <div class=\"cards\">\n"
        "    <div class=\"card\">\n"
        "      <div class=\"card-label\">Investerat</div>\n"
        "      <div class=\"card-value\">" + ti + " kr</div>\n"
        "      <div class=\"card-sub neutral\">Nollpunkt 9 jun 10:30</div>\n"
        "    </div>\n"
        "    <div class=\"card\">\n"
        "      <div class=\"card-label\">Portföljvärde</div>\n"
        "      <div class=\"card-value\">" + tv + " kr</div>\n"
        "      <div class=\"card-sub neutral\">&nbsp;</div>\n"
        "    </div>\n"
        "    <div class=\"card\">\n"
        "      <div class=\"card-label\">Total P&amp;L</div>\n"
        "      <div class=\"card-value " + pl_cls + "\">" + pl_sign + sek(total_pl) + " kr</div>\n"
        "      <div class=\"card-sub " + pl_cls + "\">" + pl_sign + tpl_pct + "%</div>\n"
        "    </div>\n"
        "    <div class=\"card\">\n"
        "      <div class=\"card-label\">Bäst / Sämst</div>\n"
        "      <div class=\"card-value\" style=\"font-size:1rem;line-height:1.6\">\n"
        "        <span class=\"pos\">" + best["ticker"] + " " + pct(best["vs_noll_pct"]) + "</span><br>\n"
        "        <span style=\"color:#a0c8d8;font-size:0.85rem\">"
        + worst["ticker"] + " " + pct(worst["vs_noll_pct"]) + "</span>\n"
        "      </div>\n"
        "    </div>\n"
        "  </div>\n"
        "  <div class=\"table-wrap\">\n"
        "    <table>\n"
        "      <thead><tr>\n"
        "        <th>Aktie</th><th>Nollkurs</th><th>Kurs</th>"
        "<th>Dag %</th><th>Vs noll %</th><th>P&amp;L (SEK)</th>"
        "<th style=\"width:90px\"></th>\n"
        "      </tr></thead>\n"
        "      <tbody>" + rows + "\n      </tbody>\n"
        "      <tfoot>\n"
        "        <tr class=\"total-row\">\n"
        "          <td><div class=\"ticker-name\">TOTALT</div></td>\n"
        "          <td style=\"color:#a0c8d8\">" + ti + " kr</td>\n"
        "          <td style=\"color:#e0f4ff\"><strong>" + tv + " kr</strong></td>\n"
        "          <td style=\"color:#a0c8d8\">-</td>\n"
        "          <td class=\"" + pl_cls + "\">" + pl_sign + tpl_pct + "%</td>\n"
        "          <td class=\"" + pl_cls + "\">" + pl_sign + sek(total_pl) + "</td>\n"
        "          <td></td>\n"
        "        </tr>\n"
        "      </tfoot>\n"
        "    </table>\n"
        "  </div>\n"
        "  <div class=\"footer\">Källa: Yahoo Finance · "
        "Uppdateras var 15 min man-fre 09:00-17:30</div>\n"
        "</div>\n</body>\n</html>"
    )

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
