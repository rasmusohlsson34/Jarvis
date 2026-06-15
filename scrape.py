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
    status_text = f'7/7 live'
elif live_count == 0:
    dot_color = '#ff1744'
    status_text = f'0/7 live'
else:
    dot_color = '#ffa500'
    status_text = f'{live_count}/7 live'

table_rows = ''
for r in rows:
    bar_pct   = abs(r['pl_pct']) / max_abs_pl * 100 if max_abs_pl else 0
    bar_color = '#00ff88' if r['pl_pct'] >= 0 else '#ff1744'
    dag_str   = f"{sign(r['dag_pct'])}{fmt(abs(r['dag_pct']))}%" if r['dag_pct'] is not None else '-'
    badge     = '<span class="bl">LIVE</span>' if r['status'] == 'LIVE' else '<span class="bf">FB</span>'
    table_rows += f'<tr><td><b>{r["ticker"]}</b>{badge}<br><small>{r["name"]}</small></td><td>{fmt(r["noll"])}</td><td><b>{fmt(r["price"])}</b></td><td class="{cls(r["dag_pct"]) if r["dag_pct"] is not None else "n"}">{dag_str}</td><td class="{cls(r["vs_noll"])}">{sign(r["vs_noll"])}{fmt(abs(r["vs_noll"]))}%</td><td class="{cls(r["pl"])}">{sign(r["pl"])}{fmt_kr(abs(r["pl"]))}</td><td><div class="bt"><div class="bf2" style="width:{bar_pct:.1f}%;background:{bar_color}"></div></div></td></tr>'

html = f"""<!DOCTYPE html>
<html lang="sv">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>J.A.R.V.I.S. - Bankterminalen</title>
<link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@700;900&family=Share+Tech+Mono&display=swap" rel="stylesheet">
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:#050c12;color:#a0c8d8;font-family:'Share Tech Mono',monospace;padding:20px}}
body::before{{content:'';position:fixed;inset:0;background:repeating-linear-gradient(0deg,transparent 2px,rgba(0,229,255,0.015) 2px 4px);pointer-events:none;z-index:100}}
.w{{max-width:1200px;margin:0 auto;position:relative;z-index:1}}
h1{{font-family:'Orbitron',sans-serif;font-size:2.4rem;color:#00e5ff;letter-spacing:.3em;text-shadow:0 0 20px rgba(0,229,255,.5);text-align:center;margin-bottom:6px}}
.sub{{text-align:center;color:rgba(0,229,255,.5);font-size:.8rem;letter-spacing:.15em;text-transform:uppercase;margin-bottom:18px}}
.sb{{display:flex;justify-content:space-between;background:rgba(0,229,255,.04);border:1px solid rgba(0,229,255,.15);padding:8px 14px;margin-bottom:18px;font-size:.78rem}}
.dot{{width:8px;height:8px;border-radius:50%;display:inline-block;background:{dot_color};box-shadow:0 0 6px {dot_color};margin-right:8px}}
.cards{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:20px}}
.card{{background:rgba(0,229,255,.04);border:1px solid rgba(0,229,255,.2);padding:14px}}
.cl{{font-size:.68rem;color:rgba(0,229,255,.5);text-transform:uppercase;letter-spacing:.1em;margin-bottom:6px}}
.cv{{font-size:1.3rem;color:#00e5ff}}
.cs{{font-size:.72rem;margin-top:3px}}
table{{width:100%;border-collapse:collapse;font-size:.8rem}}
th{{padding:8px 10px;text-align:left;color:rgba(0,229,255,.45);font-weight:normal;text-transform:uppercase;font-size:.68rem;border-bottom:1px solid rgba(0,229,255,.25)}}
th:not(:first-child){{text-align:right}}
td{{padding:10px 10px;border-bottom:1px solid rgba(0,229,255,.06)}}
td:not(:first-child){{text-align:right}}
tr:hover td{{background:rgba(0,229,255,.03)}}
.pos{{color:#00ff88}}.neg{{color:#ff1744}}.n{{color:rgba(0,229,255,.4)}}
.bl{{font-size:.58rem;padding:1px 4px;background:rgba(0,255,136,.12);border:1px solid rgba(0,255,136,.35);color:#00ff88;margin-left:5px}}
.bf{{font-size:.58rem;padding:1px 4px;background:rgba(255,165,0,.12);border:1px solid rgba(255,165,0,.35);color:#ffa500;margin-left:5px}}
.bt{{background:rgba(255,255,255,.05);height:5px;width:80px;position:relative}}
.bf2{{height:100%;position:absolute;left:0;top:0;opacity:.7}}
.tr2{{border-top:1px solid rgba(0,229,255,.25)!important}}
.tr2 td{{color:#00e5ff;padding-top:12px}}
small{{font-size:.65rem;color:rgba(0,229,255,.35)}}
.footer{{text-align:center;font-size:.62rem;color:rgba(0,229,255,.25);margin-top:24px;text-transform:uppercase;letter-spacing:.1em}}
@media(max-width:800px){{.cards{{grid-template-columns:repeat(2,1fr)}}h1{{font-size:1.5rem}}}}
</style>
</head>
<body>
<div class="w">
<h1>J.A.R.V.I.S.</h1>
<div class="sub">Bankterminalen &middot; Live Portföljövervakning</div>
<div class="sb">
  <div><span class="dot"></span><span style="color:{dot_color}">{status_text} &middot; Stockholmsbörsen</span></div>
  <div style="color:rgba(0,229,255,.5)">Uppdaterad: {now_str}</div>
</div>
<div class="cards">
  <div class="card"><div class="cl">Investerat</div><div class="cv">699&thinsp;475 kr</div><div class="cs n">Nollpunkt 9 jun 2026</div></div>
  <div class="card"><div class="cl">Portföljvärde</div><div class="cv">{fmt_kr(total_varde)}&thinsp;kr</div><div class="cs"><span class="{cls(total_pl)}">{sign(total_pl)}{fmt_kr(abs(total_pl))} kr</span></div></div>
  <div class="card"><div class="cl">Total P&amp;L</div><div class="cv"><span class="{cls(total_pl)}">{sign(total_pl)}{fmt_kr(abs(total_pl))} kr</span></div><div class="cs"><span class="{cls(total_pl_pct)}">{sign(total_pl_pct)}{fmt(abs(total_pl_pct))}%</span> vs nollpunkt</div></div>
  <div class="card"><div class="cl">Bäst / Sämst</div><div class="cv" style="font-size:1rem"><span class="pos">{best['ticker']} {sign(best['vs_noll'])}{fmt(abs(best['vs_noll']))}%</span></div><div class="cs"><span class="{cls(worst['vs_noll'])}">{worst['ticker']} {sign(worst['vs_noll'])}{fmt(abs(worst['vs_noll']))}%</span></div></div>
</div>
<table>
<thead><tr><th>Aktie</th><th>Nollkurs</th><th>Kurs</th><th>Dag%</th><th>Vs noll%</th><th>P&amp;L (kr)</th><th></th></tr></thead>
<tbody>
{table_rows}
<tr class="tr2"><td><b>TOTALT</b></td><td>{fmt_kr(TOTAL_INV)}&thinsp;kr</td><td><b>{fmt_kr(total_varde)}&thinsp;kr</b></td><td class="n">-</td><td class="{cls(total_pl_pct)}">{sign(total_pl_pct)}{fmt(abs(total_pl_pct))}%</td><td class="{cls(total_pl)}">{sign(total_pl)}{fmt_kr(abs(total_pl))}</td><td></td></tr>
</tbody>
</table>
<div class="footer">Källa: Yahoo Finance &nbsp;&middot;&nbsp; Uppdateras var 15 min mån-fre 09-18</div>
</div>
</body>
</html>"""

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)

print(f"Klar: {live_count}/7 live, portfölj {fmt_kr(total_varde)} kr", file=sys.stderr)
