import requests, json, sys
from datetime import datetime, timezone, timedelta

TOTAL_INV = 699474.50

STOCKS = [
    {'ticker': 'NDA-SE',  'yahoo': 'NDA-SE.ST',  'name': 'Nordea Bank',          'noll': 175.25, 'antal': 570, 'inv': 99892.50},
    {'ticker': 'SHB-A',   'yahoo': 'SHB-A.ST',   'name': 'Handelsbanken A',      'noll': 135.15, 'antal': 740, 'inv': 100011.00},
    {'ticker': 'SHB-B',   'yahoo': 'SHB-B.ST',   'name': 'Handelsbanken B',      'noll': 224.20, 'antal': 446, 'inv': 99993.20},
    {'ticker': 'SEB-A',   'yahoo': 'SEB-A.ST',   'name': 'SEB A',                'noll': 184.00, 'antal': 543, 'inv': 99912.00},
    {'ticker': 'SEB-C',   'yahoo': 'SEB-C.ST',   'name': 'SEB C',                'noll': 188.20, 'antal': 531, 'inv': 99934.20},
    {'ticker': 'SWED-A',  'yahoo': 'SWED-A.ST',  'name': 'Swedbank A',           'noll': 336.10, 'antal': 297, 'inv': 99821.70},
    {'ticker': 'AZA',     'yahoo': 'AZA.ST',     'name': 'Avanza Bank Holding',  'noll': 358.10, 'antal': 279, 'inv': 99909.90},
]

FALLBACK = {
    'NDA-SE': {'price': 177.05, 'dag_pct': 1.58},
    'SHB-A':  {'price': 137.25, 'dag_pct': 1.82},
    'SHB-B':  {'price': 229.00, 'dag_pct': 1.60},
    'SEB-A':  {'price': 188.30, 'dag_pct': 2.81},
    'SEB-C':  {'price': 193.80, 'dag_pct': 2.32},
    'SWED-A': {'price': 346.40, 'dag_pct': 2.24},
    'AZA':    {'price': 372.00, 'dag_pct': 5.65},
}

def fetch_price(stock):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{stock['yahoo']}?interval=1d&range=2d&includePrePost=false"
        hdrs = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
        r = requests.get(url, headers=hdrs, timeout=10)
        data = r.json()
        meta = data['chart']['result'][0]['meta']
        price = meta['regularMarketPrice']
        prev = meta.get('previousClose') or meta.get('chartPreviousClose')
        dag_pct = round((price - prev) / prev * 100, 2) if prev else None
        return {'price': price, 'dag_pct': dag_pct, 'status': 'LIVE'}
    except Exception as e:
        print(f"  FALLBACK {stock['ticker']}: {e}", file=sys.stderr)
        fb = FALLBACK[stock['ticker']]
        return {'price': fb['price'], 'dag_pct': fb['dag_pct'], 'status': 'FALLBACK'}

print("Hamtar kurser...", file=sys.stderr)
rows = []
for s in STOCKS:
    result = fetch_price(s)
    row = {**s, **result}
    row['varde']   = row['price'] * row['antal']
    row['pl']      = row['varde'] - row['inv']
    row['pl_pct']  = row['pl'] / row['inv'] * 100
    row['vs_noll'] = (row['price'] - row['noll']) / row['noll'] * 100
    rows.append(row)
    print(f"  {s['ticker']}: {result['price']} ({result['status']})", file=sys.stderr)

live_count   = sum(1 for r in rows if r['status'] == 'LIVE')
total_varde  = sum(r['varde'] for r in rows)
total_pl     = total_varde - TOTAL_INV
total_pl_pct = total_pl / TOTAL_INV * 100
max_abs_pl   = max(abs(r['pl_pct']) for r in rows)
best  = max(rows, key=lambda r: r['vs_noll'])
worst = min(rows, key=lambda r: r['vs_noll'])

stockholm = timezone(timedelta(hours=2))
now_str = datetime.now(stockholm).strftime('%d %b %Y %H:%M')

def fmt(n, d=2):
    s = f"{abs(n):,.{d}f}".replace(',', 'X').replace('.', ',').replace('X', '\u202f')
    return s

def fmt_kr(n):
    return f"{abs(int(round(n))):,}".replace(',', '\u202f')

def sign(n): return '+' if n >= 0 else '-'
def cls(n): return 'pos' if n >= 0 else 'neg'

if live_count == 7:
    dot_color = '#00ff88'
    status_text = f'7/7 live · Stockholmsbörsen'
elif live_count == 0:
    dot_color = '#ff1744'
    status_text = f'0/7 live · Fallback-priser'
else:
    dot_color = '#ffa500'
    status_text = f'{live_count}/7 live · Blandat'

table_rows = ''
for r in rows:
    bar_pct   = abs(r['pl_pct']) / max_abs_pl * 100 if max_abs_pl else 0
    bar_color = '#00ff88' if r['pl_pct'] >= 0 else '#ff1744'
    dag_str   = f"{sign(r['dag_pct'])}{fmt(abs(r['dag_pct']))}%" if r['dag_pct'] is not None else '\u2013'
    badge     = '<span class="badge badge-live">LIVE</span>' if r['status'] == 'LIVE' else '<span class="badge badge-fb">FB</span>'
    table_rows += f"""
    <tr>
      <td><div class="ticker-name">{r['ticker']}{badge}</div><div class="ticker-full">{r['name']}</div></td>
      <td>{fmt(r['noll'])}</td>
      <td><strong style="color:#e0f4ff">{fmt(r['price'])}</strong></td>
      <td class="{cls(r['dag_pct']) if r['dag_pct'] is not None else 'neu'}">{dag_str}</td>
      <td class="{cls(r['vs_noll'])}">{sign(r['vs_noll'])}{fmt(abs(r['vs_noll']))}%</td>
      <td class="{cls(r['pl'])}">{sign(r['pl'])}{fmt_kr(abs(r['pl']))}</td>
      <td class="bar-cell"><div class="bar-track"><div class="bar-fill" style="width:{bar_pct:.1f}%;background:{bar_color};opacity:0.7;box-shadow:0 0 4px {bar_color}"></div></div></td>
    </tr>"""

html = f"""<!DOCTYPE html>
<html lang="sv">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>J.A.R.V.I.S. - Bankterminalen</title>
<link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Share+Tech+Mono&display=swap" rel="stylesheet">
<style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
body{{background:#050c12;color:#a0c8d8;font-family:'Share Tech Mono',monospace;min-height:100vh;position:relative;overflow-x:hidden}}
body::before{{content:'';position:fixed;inset:0;background:repeating-linear-gradient(0deg,transparent 2px,rgba(0,229,255,0.015) 2px 4px);pointer-events:none;z-index:100}}
body::after{{content:'';position:fixed;inset:0;background:radial-gradient(ellipse at center,transparent 60%,rgba(0,0,0,0.6) 100%);pointer-events:none;z-index:101}}
.container{{max-width:1400px;margin:0 auto;padding:24px 20px 40px;position:relative;z-index:1}}
.header{{text-align:center;margin-bottom:20px;border-bottom:1px solid rgba(0,229,255,0.2);padding-bottom:20px}}
.logo{{font-family:'Orbitron',sans-serif;font-size:2.8rem;font-weight:900;color:#00e5ff;letter-spacing:0.3em;text-shadow:0 0 20px rgba(0,229,255,0.5),0 0 40px rgba(0,229,255,0.2)}}
.subtitle{{font-size:0.85rem;color:rgba(0,229,255,0.6);letter-spacing:0.15em;margin-top:6px;text-transform:uppercase}}
.status-bar{{display:flex;justify-content:space-between;align-items:center;background:rgba(0,229,255,0.04);border:1px solid rgba(0,229,255,0.15);padding:8px 16px;margin-bottom:20px;font-size:0.8rem;letter-spacing:0.08em}}
.status-left{{display:flex;align-items:center;gap:10px}}
.status-dot{{width:8px;height:8px;border-radius:50%;flex-shrink:0;background:{dot_color};box-shadow:0 0 6px {dot_color}}}
.status-right{{color:rgba(0,229,255,0.6)}}
.cards{{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:22px}}
.card{{background:rgba(0,229,255,0.04);border:1px solid rgba(0,229,255,0.2);padding:16px;position:relative;overflow:hidden}}
.card::before{{content:'';position:absolute;top:0;left:0;right:0;height:2px;background:linear-gradient(90deg,transparent,#00e5ff,transparent);opacity:0.5}}
.card-label{{font-size:0.7rem;color:rgba(0,229,255,0.5);letter-spacing:0.12em;text-transform:uppercase;margin-bottom:8px}}
.card-value{{font-size:1.4rem;color:#00e5ff}}
.card-sub{{font-size:0.75rem;margin-top:4px}}
.table-wrap{{overflow-x:auto}}
table{{width:100%;border-collapse:collapse;font-size:0.82rem}}
thead tr{{border-bottom:1px solid rgba(0,229,255,0.3)}}
thead th{{padding:10px 12px;text-align:left;color:rgba(0,229,255,0.5);font-weight:normal;letter-spacing:0.1em;text-transform:uppercase;font-size:0.72rem;white-space:nowrap}}
thead th:not(:first-child){{text-align:right}}
tbody tr{{border-bottom:1px solid rgba(0,229,255,0.07)}}
tbody tr:hover{{background:rgba(0,229,255,0.04)}}
tbody td{{padding:11px 12px;vertical-align:middle}}
tbody td:not(:first-child){{text-align:right}}
.ticker-name{{font-family:'Orbitron',sans-serif;font-size:0.8rem;font-weight:700;color:#00e5ff;letter-spacing:0.05em}}
.ticker-full{{font-size:0.68rem;color:rgba(0,229,255,0.4);margin-top:2px}}
.badge{{display:inline-block;font-size:0.6rem;padding:1px 5px;letter-spacing:0.08em;margin-left:6px;vertical-align:middle}}
.badge-live{{background:rgba(0,255,136,0.15);border:1px solid rgba(0,255,136,0.4);color:#00ff88}}
.badge-fb{{background:rgba(255,165,0,0.15);border:1px solid rgba(255,165,0,0.4);color:#ffa500}}
.pos{{color:#00ff88}}.neg{{color:#ff1744}}.neu{{color:rgba(0,229,255,0.5)}}
.bar-cell{{min-width:90px}}
.bar-track{{background:rgba(255,255,255,0.05);height:6px;width:100%;position:relative}}
.bar-fill{{height:100%;position:absolute;left:0;top:0}}
.totals-row{{border-top:1px solid rgba(0,229,255,0.3)!important;border-bottom:none!important}}
.totals-row td{{color:#00e5ff;padding-top:13px}}
.totals-label{{font-family:'Orbitron',sans-serif;font-size:0.72rem;letter-spacing:0.08em;color:rgba(0,229,255,0.7)}}
.footer{{margin-top:28px;text-align:center;font-size:0.68rem;color:rgba(0,229,255,0.3);letter-spacing:0.1em;text-transform:uppercase;border-top:1px solid rgba(0,229,255,0.1);padding-top:16px}}
@media(max-width:900px){{.cards{{grid-template-columns:repeat(2,1fr)}}.logo{{font-size:1.8rem}}}}
</style>
</head>
<body>
<div class="container">
  <header class="header">
    <div class="logo">J.A.R.V.I.S.</div>
    <div class="subtitle">Bankterminalen &middot; Live Portföljövervakning</div>
  </header>
  <div class="status-bar">
    <div class="status-left">
      <div class="status-dot"></div>
      <span style="color:{dot_color}">{status_text}</span>
    </div>
    <div class="status-right">Uppdaterad: {now_str}</div>
  </div>
  <div class="cards">
    <div class="card">
      <div class="card-label">Investerat</div>
      <div class="card-value">699&thinsp;475 kr</div>
      <div class="card-sub neu">Nollpunkt 9 jun 2026</div>
    </div>
    <div class="card">
      <div class="card-label">Portföljvärde</div>
      <div class="card-value">{fmt_kr(total_varde)}&thinsp;kr</div>
      <div class="card-sub"><span class="{cls(total_pl)}">{sign(total_pl)}{fmt_kr(abs(total_pl))} kr förändring</span></div>
    </div>
    <div class="card">
      <div class="card-label">Total P&amp;L</div>
      <div class="card-value"><span class="{cls(total_pl)}">{sign(total_pl)}{fmt_kr(abs(total_pl))} kr</span></div>
      <div class="card-sub"><span class="{cls(total_pl_pct)}">{sign(total_pl_pct)}{fmt(abs(total_pl_pct))}%</span> vs nollpunkt</div>
    </div>
    <div class="card">
      <div class="card-label">Bäst / Sämst</div>
      <div class="card-value" style="font-size:1.05rem"><span class="pos">{best['ticker']} {sign(best['vs_noll'])}{fmt(abs(best['vs_noll']))}%</span></div>
      <div class="card-sub"><span class="{cls(worst['vs_noll'])}">{worst['ticker']} {sign(worst['vs_noll'])}{fmt(abs(worst['vs_noll']))}%</span></div>
    </div>
  </div>
  <div class="table-wrap">
    <table>
      <thead><tr><th>Aktie</th><th>Nollkurs</th><th>Kurs</th><th>Dag%</th><th>Vs noll%</th><th>P&amp;L (SEK)</th><th class="bar-cell"></th></tr></thead>
      <tbody>
        {table_rows}
        <tr class="totals-row">
          <td><span class="totals-label">TOTALT</span></td>
          <td style="color:#a0c8d8">{fmt_kr(TOTAL_INV)}&thinsp;kr</td>
          <td><strong style="color:#e0f4ff">{fmt_kr(total_varde)}&thinsp;kr</strong></td>
          <td class="neu">–</td>
          <td class="{cls(total_pl_pct)}">{sign(total_pl_pct)}{fmt(abs(total_pl_pct))}%</td>
          <td class="{cls(total_pl)}">{sign(total_pl)}{fmt_kr(abs(total_pl))}</td>
          <td></td>
        </tr>
      </tbody>
    </table>
  </div>
  <footer class="footer">KÄLLA: Yahoo Finance &nbsp;&middot;&nbsp; UPPDATERAS VAR 15 MIN MÅN–FRE 09:00–17:30</footer>
</div>
</body>
</html>"""

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)

print(f"index.html skriven - {live_count}/7 live, portföljvärde {fmt_kr(total_varde)} kr", file=sys.stderr)
