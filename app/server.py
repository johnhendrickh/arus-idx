"""server.py — web screener 1 halaman. Baca cache, tidak pernah manggil API.
Jalankan: python -m app.server"""
from http.server import BaseHTTPRequestHandler, HTTPServer
import json, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.main import load_cache
from app import score as sc, io_cache, ledger, config as cfg
import pandas as pd, numpy as np

def build_rows():
    ohlcv, bm, fm, idx = load_cache()
    fund = io_cache.read_fund()
    comp = sc.composite(ohlcv, fund, broker_map=bm or None, foreign=fm or None, index_close=idx)
    last = comp.iloc[-1]
    floor = sc.liquidity_floor(ohlcv).iloc[-1]
    reg_on = bool(sc.regime(ohlcv, idx).iloc[-1])
    pm = sc.momentum_pillar(ohlcv).iloc[-1]
    pf = sc.fundamental_pillar(ohlcv, fund).iloc[-1] if fund is not None else None
    # konteks flow per saham (informasi murni, tidak masuk skor)
    fnotes = {}
    for s in fm:
        f = fm[s]
        if f is None or len(f) < 25: continue
        f5 = f['net_foreign_inflow'].tail(5).sum()
        fnotes[s + '.JK'] = round(float(f5)/1e9, 1)   # IDR miliar
    rows = []
    for t, v in last.dropna().sort_values(ascending=False).items():
        rows.append({
            'symbol': t.replace('.JK',''), 'score': round(float(v), 2),
            'momentum': round(float(pm.get(t, np.nan)), 2) if pd.notna(pm.get(t)) else None,
            'fundamental': round(float(pf.get(t, np.nan)), 2) if pf is not None and pd.notna(pf.get(t)) else None,
            'liquid': bool(floor.get(t, False)),
            'foreign_5d_idrb': fnotes.get(t),
        })
    led = ledger.stats('flow_alert') or {'n': 0}
    return {'regime': 'UP' if reg_on else 'DOWN', 'asof': str(comp.index[-1].date()),
            'rows': rows, 'ledger': led}

PAGE = """<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ARUS — IDX Flow Screener</title>
<style>
body{font-family:system-ui,sans-serif;max-width:860px;margin:24px auto;padding:0 16px;background:#0e1117;color:#e6e6e6}
h1{font-size:22px;margin-bottom:4px}.sub{color:#8b949e;font-size:13px;margin-bottom:18px}
.regime{display:inline-block;padding:4px 10px;border-radius:6px;font-weight:600;margin-bottom:14px}
.UP{background:#1b4332;color:#95d5b2}.DOWN{background:#4a1525;color:#f4a6b8}
table{border-collapse:collapse;width:100%}th,td{padding:8px 10px;text-align:left;border-bottom:1px solid #21262d}
th{color:#8b949e;font-size:12px;text-transform:uppercase}
.score{font-weight:700;font-size:15px}.pill{padding:2px 8px;border-radius:10px;font-size:11px}
.g{background:#1b4332;color:#95d5b2}.r{background:#4a1525;color:#f4a6b8}.m{background:#30363d;color:#c9d1d9}
.foot{margin-top:18px;color:#8b949e;font-size:12px;border-top:1px solid #21262d;padding-top:10px}
.bar{height:8px;border-radius:4px;background:#30363d;width:80px;display:inline-block;vertical-align:middle;position:relative;margin-right:6px}
.fill{height:8px;border-radius:4px;display:block}
.f-hi{background:#2ea043}.f-mid{background:#d29922}.f-lo{background:#da3633}.f-na{background:#30363d}
.pct{font-size:11px;color:#8b949e;vertical-align:middle}
.pill-hi{color:#95d5b2;font-weight:600}.pill-mid{color:#e3b341;font-weight:600}.pill-lo{color:#f4a6b8;font-weight:600}
</style></head><body>
<h1>ARUS</h1>
<div class="sub">Screener IDX 3 pilar — momentum &times; fundamental &times; aliran dana (Sectors API). Data per <span id=asof></span></div>
<div id=regime class="regime"></div>
<table><thead><tr><th>Saham</th><th>Skor</th><th>Momentum</th><th>Funda</th><th>Asing 5d</th><th>Status</th></tr></thead>
<tbody id=tb></tbody></table>
<div class=foot id=ledger></div>
<div class=foot>Skor = ranking probabilitas, bukan prediksi pasti. Backtest momentum+fundamental: IC +0.093 (n=38 rebalance, top&gt;bot 63%). Kolom flow = <b>informasi, bukan sinyal</b> — backtest kami menunjukkan flow belum bisa dipercaya sebagai sinyal (detail di README); tiap sinyal flow dicatat ke ledger dan diukur hasilnya setelah 20 hari. Bukan rekomendasi beli/jual.</div>
<script>
fetch('/api').then(r=>r.json()).then(d=>{
document.getElementById('asof').textContent=d.asof;
const rg=document.getElementById('regime');rg.textContent=d.regime==='UP'?'IHSG regime: UP — scanning':'IHSG regime: DOWN — mode tunggu, jangan entry';rg.className='regime '+d.regime;
document.getElementById('tb').innerHTML=d.rows.map(r=>{
const st=!r.liquid?'<span class="pill m">SKIP</span>':(d.regime==='DOWN'?'<span class="pill r">WAIT</span>':'<span class="pill g">OK</span>');
const bar=(v)=>v==null?'<span class="pill m">n/a</span>':`<span class=bar><span class="fill ${v>=0.6?'f-hi':v>=0.4?'f-mid':'f-lo'}" style="width:${Math.round(v*100)}%"></span></span><span class="pct">${Math.round(v*100)}%</span>`;
const fg=r.foreign_5d_idrb==null?'—':(r.foreign_5d_idrb>0?`<span class=g>+${r.foreign_5d_idrb}M IDR</span>`:`<span class=r>${r.foreign_5d_idrb}M IDR</span>`);
return `<tr><td><b>${r.symbol}</b></td><td class=score>${r.score.toFixed(2)}</td><td>${bar(r.momentum)}</td><td>${bar(r.fundamental)}</td><td>${fg}</td><td>${st}</td></tr>`}).join('');
document.getElementById('ledger').innerHTML='Ledger sinyal flow: '+(d.ledger.n>0?`n=${d.ledger.n}, hit ${(d.ledger.hit*100).toFixed(0)}%, median ${(d.ledger.med*100).toFixed(1)}%`:'n=0 — rapor mulai terisi saat cron live aktif');
});</script></body></html>"""

class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        if self.path == '/api':
            body = json.dumps(build_rows()).encode()
            self.send_response(200); self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body))); self.end_headers(); self.wfile.write(body)
        else:
            body = PAGE.encode()
            self.send_response(200); self.send_header('Content-Type', 'text/html')
            self.send_header('Content-Length', str(len(body))); self.end_headers(); self.wfile.write(body)

if __name__ == '__main__':
    print('ARUS screener: http://localhost:8787')
    HTTPServer(('0.0.0.0', 8787), H).serve_forever()
