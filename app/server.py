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
th{color:#8b949e;font-size:12px;text-transform:uppercase;cursor:pointer;user-select:none}
th:hover{color:#e6e6e6}th.sort-asc::after{content:" ▲"}th.sort-desc::after{content:" ▼"}
.score{font-weight:700;font-size:15px}.pill{padding:2px 8px;border-radius:10px;font-size:11px}
.g{background:#1b4332;color:#95d5b2}.r{background:#4a1525;color:#f4a6b8}.m{background:#30363d;color:#c9d1d9}
.foot{margin-top:18px;color:#8b949e;font-size:12px;border-top:1px solid #21262d;padding-top:10px}
.bar{height:8px;border-radius:4px;background:#30363d;width:80px;display:inline-block;vertical-align:middle;position:relative;margin-right:6px}
.fill{height:8px;border-radius:4px;display:block}
.f-hi{background:#2ea043}.f-mid{background:#d29922}.f-lo{background:#da3633}.f-na{background:#30363d}
.pct{font-size:11px;color:#8b949e;vertical-align:middle}
.controls{display:flex;gap:12px;flex-wrap:wrap;align-items:center;margin-bottom:12px;font-size:13px;color:#c9d1d9}
.controls select{background:#161b22;color:#e6e6e6;border:1px solid #30363d;border-radius:6px;padding:4px 8px}
.controls input[type=text]{background:#161b22;color:#e6e6e6;border:1px solid #30363d;border-radius:6px;padding:4px 8px;width:110px}
.controls label{color:#8b949e}
.star{cursor:pointer;font-size:15px;color:#30363d;user-select:none}
.star.on{color:#e3b341}
details{margin:14px 0;color:#c9d1d9;font-size:13px}
details summary{cursor:pointer;color:#58a6ff;font-weight:600}
details .x{background:#161b22;border:1px solid #21262d;border-radius:8px;padding:12px 16px;margin-top:8px;line-height:1.6}
details .x b{color:#e6e6e6}.x .q{color:#79c0ff}.x .a{color:#7ee787}
</style></head><body>
<h1>ARUS</h1>
<div class="sub">Screener IDX — momentum &times; fundamental &times; aliran dana (data: Sectors API). Data per <span id=asof></span> · <a href="#cara-baca" style="color:#58a6ff;text-decoration:none">cara baca halaman ini ↓</a></div>
<div id=regime class="regime"></div>
<div class="controls">
  <label>Urutkan:</label>
  <select id=sort>
    <option value="score">Skor (gabungan)</option>
    <option value="momentum">Momentum</option>
    <option value="fundamental">Fundamental</option>
    <option value="foreign">Asing 5d (IDR)</option>
    <option value="symbol">Saham (A-Z)</option>
  </select>
  <label>Status:</label>
  <select id=stat>
    <option value="">Semua</option>
    <option value="ok">OK saja (likuid)</option>
    <option value="wait">WAIT / SKIP</option>
  </select>
  <label><input type=checkbox id=only-foreign> Hanya asing net-beli 5d</label>
  <input type=text id=q placeholder="cari saham… (BBCA)">
  <label><input type=checkbox id=watch> ★ watchlist</label>
</div>
<table><thead><tr>
<th data-k=symbol>Saham</th><th data-k=score>Skor</th><th data-k=momentum>Momentum</th><th data-k=fundamental>Funda</th><th data-k=foreign>Asing 5d</th><th data-k=status>Status</th><th title="klik ★ untuk watchlist">★</th>
</tr></thead>
<tbody id=tb></tbody></table>
<div class=foot id=ledger></div>
<details id=cara-baca><summary>Cara baca halaman ini — skor itu apa?</summary>
<div class=x>
<b>Skor (0–100) = peringkat gabungan Momentum 55% + Fundamental 45%</b> — bukan harga target, bukan persentase naik. Artinya: <i>di antara 21 saham besar IDX yang kami pantau, saham ini ada di peringkat ke-N</i>. Skor 80 = top 20%; skor 30 = bottom 30%. Saham di atas mengalahkan saham di bawah pada backtest 5 tahun (IC +0.093, top-5 vs bottom-5 menang 63% dari 38 rebalance).
<br><br>
<span class=q>Momentum</span> = konsistensi arah harga 20/60/120 hari, disesuaikan volatilitas. <i>Naik tinggi tapi naik dadak → tidak dinilai.</i>
<br><span class=q>Fundamental</span> = ROE + laba/harga, dengan penalti untuk growth-trap (pertumbuhan revenue tinggi yang sering menipu di IDX).
<br><span class=q>Asing 5d</span> = uang investor asing masuk (+) atau keluar (−) 5 hari terakhir, dari data transaksi Sectors. <b>Kolom informasi, bukan sinyal</b> — kami mengujinya sebagai sinyal dan hasilnya negatif (detail di README), jadi ditampilkan apa adanya.
<br><span class=q>Status</span> = <span class=a>OK</span>: likuid &amp; IHSG di atas EMA50 → boleh dipertimbangkan. <span style="color:#f4a6b8">WAIT</span>: IHSG lemah → tunggu. <span style="color:#c9d1d9">SKIP</span>: likuiditas rendah → hindari.
<br><br>
<b>Regime</b>: semua saham jadi WAIT saat IHSG di bawah EMA50 — momentum saham jarang menang saat indeks jatuh; itu hasil backtest, bukan opini.
</div></details>
<div class=foot>Skor = ranking probabilitas, bukan prediksi pasti. Backtest momentum+fundamental: IC +0.093 (n=38 rebalance, top&gt;bot 63%). Kolom flow = <b>informasi, bukan sinyal</b> — backtest kami menunjukkan flow belum bisa dipercaya sebagai sinyal (detail di README); tiap sinyal flow dicatat ke ledger dan diukur hasilnya setelah 20 hari. Bukan rekomendasi beli/jual.</div>
<script>
let D=null;let WL=new Set(JSON.parse(localStorage.getItem('arus-watchlist')||'[]'));
fetch('/api').then(r=>r.json()).then(d=>{D=d;render();});
function fmtForeign(r){if(r.foreign_5d_idrb==null)return null;const a=Math.abs(r.foreign_5d_idrb);
 const s=a>=1000?(a/1000).toFixed(2)+' T':a.toFixed(0)+' M';return {raw:r.foreign_5d_idrb,txt:(r.foreign_5d_idrb>0?'+':'−')+s+' IDR'};}
function render(){
const d=D;
document.getElementById('asof').textContent=d.asof;
const rg=document.getElementById('regime');rg.textContent=d.regime==='UP'?'IHSG regime: UP — scanning':'IHSG regime: DOWN — mode tunggu, jangan entry';rg.className='regime '+d.regime;
const sort=document.getElementById('sort').value;
const stat=document.getElementById('stat').value;
const onlyF=document.getElementById('only-foreign').checked;
const q=document.getElementById('q').value.trim().toUpperCase();
const onlyW=document.getElementById('watch').checked;
const stOf=r=>!r.liquid?'SKIP':(d.regime==='DOWN'?'WAIT':'OK');
let rows=[...d.rows];
if(stat==='ok')rows=rows.filter(r=>stOf(r)==='OK');
if(stat==='wait')rows=rows.filter(r=>stOf(r)!=='OK');
if(onlyF)rows=rows.filter(r=>r.foreign_5d_idrb!=null&&r.foreign_5d_idrb>0);
if(q)rows=rows.filter(r=>r.symbol.includes(q));
if(onlyW)rows=rows.filter(r=>WL.has(r.symbol));
const key={symbol:r=>r.symbol,score:r=>r.score??-1,momentum:r=>r.momentum??-1,fundamental:r=>r.fundamental??-1,foreign:r=>r.foreign_5d_idrb??-Infinity};
const dir=sort==='symbol'?1:-1;
rows.sort((a,b)=>{const ka=key[sort](a),kb=key[sort](b);return ka===kb?0:(ka>kb?dir:-dir);});
document.querySelectorAll('th').forEach(th=>{th.className=th.dataset.k===sort?(dir===1?'sort-asc':'sort-desc'):'';});
const bar=(v)=>v==null?'<span class="pill m">n/a</span>':`<span class=bar><span class="fill ${v>=0.6?'f-hi':v>=0.4?'f-mid':'f-lo'}" style="width:${Math.round(v*100)}%"></span></span><span class="pct">${Math.round(v*100)}%</span>`;
document.getElementById('tb').innerHTML=rows.map(r=>{
const st=stOf(r);const stc=st==='OK'?'g':(st==='WAIT'?'r':'m');
const f=fmtForeign(r);const fg=f==null?'—':(f.raw>0?`<span class=g>${f.txt}</span>`:`<span class=r>${f.txt}</span>`);
return `<tr><td><b>${r.symbol}</b></td><td class=score>${(r.score*100).toFixed(0)}</td><td>${bar(r.momentum)}</td><td>${bar(r.fundamental)}</td><td>${fg}</td><td><span class="pill ${stc}">${st}</span></td><td><span class="star ${WL.has(r.symbol)?'on':''}" data-s=${r.symbol}>${WL.has(r.symbol)?'★':'☆'}</span></td></tr>`}).join('');
document.getElementById('ledger').innerHTML='Ledger sinyal flow: '+(d.ledger.n>0?`n=${d.ledger.n}, hit ${(d.ledger.hit*100).toFixed(0)}%, median ${(d.ledger.med*100).toFixed(1)}%`:'n=0 — rapor mulai terisi saat cron live aktif');
}
['sort','stat','only-foreign','watch'].forEach(id=>document.getElementById(id).addEventListener('change',render));
document.getElementById('q').addEventListener('input',render);
document.getElementById('tb').addEventListener('click',e=>{
const s=e.target.closest('.star');if(!s)return;
const sym=s.dataset.s;
if(WL.has(sym))WL.delete(sym);else WL.add(sym);
localStorage.setItem('arus-watchlist',JSON.stringify([...WL]));
render();});
</script></body></html>"""

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
