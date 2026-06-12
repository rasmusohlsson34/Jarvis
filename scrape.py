#!/usr/bin/env python3
"""JARVIS Bankterminalen — Avanza scraper"""

import asyncio
import re
from datetime import datetime, timezone, timedelta
from playwright.async_api import async_playwright

# ── Nollpunkt 9 juni 2026 kl 10:30 ────────────────────────────────────────
STOCKS = [
    {"ticker": "NDA-SE",  "name": "Nordea Bank",         "url": "https://www.avanza.se/aktier/om-aktien.html/5249/nordea-bank",        "noll": 175.25, "antal": 570, "investerat": 99892.50},
    {"ticker": "SHB-A",   "name": "Handelsbanken A",     "url": "https://www.avanza.se/aktier/om-aktien.html/5264/handelsbanken-a",     "noll": 135.15, "antal": 740, "investerat": 100011.00},
    {"ticker": "SHB-B",   "name": "Handelsbanken B",     "url": "https://www.avanza.se/aktier/om-aktien.html/5265/handelsbanken-b",     "noll": 224.20, "antal": 446, "investerat": 99993.20},
    {"ticker": "SEB-A",   "name": "SEB A",               "url": "https://www.avanza.se/aktier/om-aktien.html/5255/seb-a",               "noll": 184.00, "antal": 543, "investerat": 99912.00},
    {"ticker": "SEB-C",   "name": "SEB C",               "url": "https://www.avanza.se/aktier/om-aktien.html/5256/seb-c",               "noll": 188.20, "antal": 531, "investerat": 99934.20},
    {"ticker": "SWED-A",  "name": "Swedbank A",          "url": "https://www.avanza.se/aktier/om-aktien.html/5241/swedbank-a",          "noll": 336.10, "antal": 297, "investerat": 99821.70},
    {"ticker": "AZA",     "name": "Avanza Bank Holding", "url": "https://www.avanza.se/aktier/om-aktien.html/5361/avanza-bank-holding", "noll": 358.10, "antal": 279, "investerat": 99909.90},
]

FALLBACK = {
    "NDA-SE": (177.05, 1.58),
    "SHB-A":  (137.25, 1.82),
    "SHB-B":  (229.00, 1.60),
    "SEB-A":  (188.30, 2.81),
    "SEB-C":  (193.80, 2.32),
    "SWED-A": (346.40, 2.24),
    "AZA":    (372.00, 5.65),
}

# ── Hämta en aktie ────────────────────────────────────────────────────────
async def fetch_stock(page, stock):
    try:
        await page.goto(stock["url"], wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(2000)
        text = await page.inner_text("body")

        price_match = re.search(r'Senast betalt\s*([\d \s]+[,\.]\d{2})\s*SEK', text)
        day_match   = re.search(r'1 d\.\s*([+-]?\d+,\d+)%', text)

        price = None
        day_pct = None

        if price_match:
            raw = price_match.group(1).replace(' ', '').replace(' ', '').replace(',', '.')
            price = float(raw)

        if day_match:
            day_pct = float(day_match.group(1).replace(',', '.'))

        if price:
            return price, day_pct, "LIVE"

    except Exception as e:
        print(f"  FEL vid {stock['ticker']}: {e}")

    fb = FALLBACK[stock["ticker"]]
    return fb[0], fb[1], "FALLBACK"

# ── Huvudloop ────────────────────────────────────────────────────────────
async def main():
    results = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = await context.new_page()

        for stock in STOCKS:
            print(f"Hämtar {stock['ticker']}...")
            price, day_pct, status = await fetch_stock(page, stock)
            varde        = price * stock["antal"]
            pl           = varde - stock["investerat"]
            pl_pct       = (pl / stock["investerat"]) * 100
            vs_noll_pct  = (price - stock["noll"]) / stock["noll"] * 100
            results.append({**stock,
                "price": price, "day_pct": day_pct, "status": status,
                "varde": varde, "pl": pl, "pl_pct": pl_pct, "vs_noll_pct": vs_noll_pct,
            })
            print(f"  → {price} SEK  dag: {day_pct}%  [{status}]")

        await browser.close()

    generate_html(results)
    print("index.html klar!")

# ── Hjälpfunktioner ───────────────────────────────────────────────────────
def fmt_sek(n):
    return f"{abs(n):,.0f}".replace(",", " ")

def fmt_pct(n, dec=2):
    sign = "+" if n >= 0 else ""
    return f"{sign}{n:.{dec}f}%"

# ── HTML-generator ────────────────────────────────────────────────────────
def generate_html(results):
    total_inv   = sum(r["investerat"] for r in results)
    total_varde = sum(r["varde"]      for r in results)
    total_pl    = total_varde - total_inv
    total_pl_pct    = (total_pl / total_inv) * 100
    total_vs_noll   = total_pl_pct

    live_count = sum(1 for r in results if r["status"] == "LIVE")
    best  = max(results, key=lambda r: r["vs_noll_pct"])
    worst = min(results, key=lambda r: r["vs_noll_pct"])
    max_pl = max(abs(r["pl_pct"]) for r in results) or 1

    # Stockholmstid (UTC+2 sommar)
    stockholm = timezone(timedelta(hours=2))
    now = datetime.now(stockholm)
    update_time = now.strftime("%H:%M:%S")
    update_date = now.strftime("%-d %b %Y")

    if live_count == 7:
        dot_color   = "#00ff88"
        status_text = f"7/7 live · Stockholmsbörsen · {update_date}"
    elif live_count == 0:
        dot_color   = "#ff1744"
        status_text = f"0/7 live · FALLBACK · {update_date}"
    else:
        dot_color   = "#ffa726"
        status_text = f"{live_count}/7 live · {update_date}"

    pl_cls  = "pos" if total_pl >= 0 else "neg"
    pl_sign = "+" if total_pl >= 0 else "−"

    # ── Tabellrader ──
    rows = ""
    for r in results:
        bc  = "badge-live" if r["status"] == "LIVE" else "badge-fallback"
        bt  = "LIVE" if r["status"] == "LIVE" else "FALLBACK"
        dstr = fmt_pct(r["day_pct"]) if r["day_pct"] is not None else "–"
        dcls = ("pos" if r.get("day_pct", 0) >= 0 else "neg") if r["day_pct"] is not None else "neutral"
        vcls = "pos" if r["vs_noll_pct"] >= 0 else "neg"
        pcls = "pos" if r["pl"] >= 0 else "neg"
        bar  = min(100, abs(r["pl_pct"]) / max_pl * 100)
        bcol = "#00ff88" if r["pl"] >= 0 else "#ff1744"
        psign = "+" if r["pl"] >= 0 else "−"
        price_str = f"{r['price']:,.2f}".replace(",", " ").replace(".", ",")
        noll_str  = f"{r['noll']:,.2f}".replace(",", " ").replace(".", ",")

        rows += f"""
        <tr>
          <td><div class="ticker-name">{r["ticker"]} <span class="badge {bc}">{bt}</span></div>
              <div class="stock-fullname">{r["name"]}</div></td>
          <td>{noll_str}</td>
          <td><strong style="color:#e0f4ff;">{price_str}</strong></td>
          <td class="{dcls}">{dstr}</td>
          <td class="{vcls}">{fmt_pct(r["vs_noll_pct"])}</td>
          <td class="{pcls}">{psign}{fmt_sek(r["pl"])}</td>
          <td><div class="bar-wrap"><div class="bar-bg"><div class="bar-fill" style="width:{bar:.1f}%;background:{bcol};"></div></div></div></td>
        </tr>"""

    tv_str = f"{total_varde:,.0f}".replace(",", " ")
    ti_str = f"{total_inv:,.0f}".replace(",", " ")

    html = f"""<!DOCTYPE html>
<html lang="sv">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<meta http-equiv="refresh" content="900">
<title>J.A.R.V.I.S. — Bankterminalen</title>
<link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Share+Tech+Mono&display=swap" rel="stylesheet">
<style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
body{{background:#050c12;color:#a0c8d8;font-family:'Share Tech Mono',monospace;min-height:100vh;position:relative;overflow-x:hidden}}
body::before{{content:'';position:fixed;inset:0;background:repeating-linear-gradient(0deg,transparent 2px,rgba(0,229,255,0.015) 2px 4px);pointer-events:none;z-index:1000}}
body::after{{content:'';position:fixed;inset:0;background:radial-gradient(ellipse at center,transparent 60%,rgba(0,0,0,0.6) 100%);pointer-events:none;z-index:999}}
.container{{max-width:1300px;margin:0 auto;padding:24px 20px 40px;position:relative;z-index:1}}
.header{{text-align:center;margin-bottom:20px;border-bottom:1px solid rgba(0,229,255,0.2);padding-bottom:16px}}
.logo{{font-family:'Orbitron',sans-serif;font-size:2.8rem;font-weight:900;color:#00e5ff;letter-spacing:0.3em;text-shadow:0 0 20px rgba(0,229,255,0.5)}}
.subtitle{{font-size:0.85rem;color:rgba(0,229,255,0.6);letter-spacing:0.2em;margin-top:4px;text-transform:uppercase}}
.statusbar{{display:flex;justify-content:space-between;align-items:center;background:rgba(0,229,255,0.04);border:1px solid rgba(0,229,255,0.15);border-radius:4px;padding:8px 16px;margin-bottom:20px;font-size:0.78rem;letter-spacing:0.05em}}
.status-left{{display:flex;align-items:center;gap:8px}}
.status-dot{{width:8px;height:8px;border-radius:50%;background:{dot_color};box-shadow:0 0 6px {dot_color};flex-shrink:0}}
.status-text{{color:{dot_color}}}
.status-right{{color:rgba(0,229,255,0.7)}}
.cards{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:20py}}
.card{{background:rgba(0,229,255,0.04);border:1px solid rgba(0,229,255,0.18);border-radius:6px;padding:14px 16px}}
.card-label{{font-size:0.68rem;color:rgba(0,229,255,0.5);text-transform:uppercase;letter-spacing:0.12em;margin-bottom:6px}}
.card-value{{font-size:1.25rem;color:#00e5ff}}
.card-sub{{font-size:0.75rem;margin-top:2px}}
.pos{{color:#00ff88}}.neg{{color:#ff1744}}.neutral{{color:#a0c8d8}}
.table-wrap{{overflow-x:auto}}
table{{width:100%;border-collapse:collapse;font-size:0.82rem}}
thead tr{{border-bottom:1px solid rgba(0,229,255,0.3)}}
th{{padding:10px 10px 8px;text-align:right;font-size:0.65rem;color:rgba(0,229,255,0.5);text-transform:uppercase;letter-spacing:0.1em;white-space:nowrap}}
th:first-child{{text-align:left}}
td{{padding:11px 10px;text-align:right;border-bottom:1px solid rgba(0,229,255,0.07);vertical-align:middle;white-space:nowrap}}
td:first-child{{text-align:left}}
tbody tr:hover{{background:rgba(0,229,255,0.04)}}
.ticker-name{{font-family:'Orbitron',sans-serif;font-size:0.85rem;font-weight:700;color:#00e5ff;display:flex;align-items:center;gap:8px}}
.badge{{font-family:'Share Tech Mono',monospace;font-size:0.6rem;padding:2px 6px;border-radius:3px;letter-spacing:0.05em}}
.badge-live{{background:rgba(0,255,136,0.15);color:#00ff88;border:1px solid rgba(0,255,136,0.4)}}
.badge-fallback{{background:rgba(255,167,38,0.15);color:#ffa726;border:1px solid rgba(255,167,38,0.4)}}
.stock-fullname{{font-size:0.68rem;color:rgba(0,229,255,0.4);margin-top:2px}}
.bar-wrap{{display:flex;align-items:center;justify-content:flex-end}}
.bar-bg{{width:80px;height:6px;background:rgba(255,255,255,0.06);border-radius:3px;overflow:hidden}}
.bar-fill{{height:100%;border-radius:3px}}
.total-row td{{border-top:1px solid rgba(0,229,255,0.3);border-bottom:none;color:#00e5ff;font-size:0.85rem;padding-top:14px}}
.footer{{margin-top:24px;text-align:center;font-size:0.65rem;color:rgba(0,229,255,0.25);letter-spacing:0.1em;text-transform:uppercase}}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <div class="logo">J.A.R.V.I.S.</div>
    <div class="subtitle">Bankterminalen · Live Portföljövervakning</div>
  </div>
  <div class="statusbar">
    <div class="status-left">
      <div class="status-dot"></div>
      <span class="status-text">{status_text}</span>
    </div>
    <div class="status-right">Senast uppdaterad: {update_date} {update_time} · Auto-refresh om 15 min</div>
  </div>
  <div class="cards">
    <div class="card">
      <div class="card-label">Investerat</div>
      <div class="card-value">{ti_str} kr</div>
      <div class="card-sub neutral">Nollpunkt 9 jun 10:30</div>
    </div>
    <div class="card">
      <div class="card-label">Portföljvärde</div>
      <div class="card-value">{tv_str} kr</div>
      <div class="card-sub neutral">&nbsp;</div>
    </div>
    <div class="card">
      <div class="card-label">Total P&amp;L</div>
      <div class="card-value {pl_cls}">{pl_sign}{fmt_sek(total_pl)} kr</div>
      <div class="card-sub {pl_cls}">{pl_sign}{abs(total_pl_pct):.2f}%</div>
    </div>
    <div class="card">
      <div class="card-label">Bäst / Sämst</div>
      <div class="card-value" style="font-size:1rem;line-height:1.6">
        <span class="pos">{best["ticker"]} {fmt_pct(best["vs_noll_pct"])}</span><br>
        <span style="color:#a0c8d8;font-size:0.85rem">{worst["ticker"]} {fmt_pct(worst["vs_noll_pct"])}</span>
      </div>
    </div>
  </div>
  <div class="table-wrap">
    <table>
      <thead><tr>
        <th>Aktie</th><th>Nollkurs</th><th>Kurs</th><th>Dag %</th><th>Vs noll %</th><th>P&amp;L (SEK)</th><th style="width:90px"></th>
      </tr></thead>
      <tbody>{rows}</tbody>
      <tfoot>
        <tr class="total-row">
          <td><div class="ticker-name">TOTALT</div></td>
          <td style="color:#a0c8d8">{ti_str} kr</td>
          <td style="color:#e0f4ff"><strong>{tv_str} kr</strong></td>
          <td style="color:#a0c8d8">—</td>
          <td class="{pl_cls}">{pl_sign}{abs(total_vs_noll):.2f}%</td>
          <td class="{pl_cls}">{pl_sign}{fmt_sek(total_pl)}</td>
          <td></td>
        </tr>
      </tfoot>
    </table>
  </div>
  <div class="footer">Källa: Avanza · Uppdateras var 15 min mån–fre 09:00–17:30</div>
</div>
</body>
</html>"""

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)


if __name__ == "__main__":
    asyncio.run(main())
