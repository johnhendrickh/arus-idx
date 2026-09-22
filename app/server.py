"""server.py — web screener 1 halaman. Baca cache, tidak pernah manggil API.
Jalankan: python -m app.server"""
from http.server import BaseHTTPRequestHandler, HTTPServer
import json, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.main import load_cache
from app import score as sc, io_cache, ledger, config as cfg, value
import pandas as pd, numpy as np

def build_rows():
    ohlcv, bm, fm, idx = load_cache()
    fund = io_cache.read_fund()
    comp = sc.composite(ohlcv, fund, broker_map=bm or None, foreign=fm or None, index_close=idx)
    last = comp.iloc[-1]
    floor = sc.liquidity_floor(ohlcv).iloc[-1]
    reg_on = bool(sc.regime(ohlcv, idx).iloc[-1]) if idx is not None else False  # fail-CLOSED
    margin = None
    if idx is not None:
        _ema = idx.ewm(span=cfg.REGIME_EMA_SPAN, adjust=False).mean().iloc[-1]
        margin = round(float(idx.iloc[-1]/_ema - 1)*100, 1)
    pm = sc.momentum_pillar(ohlcv).iloc[-1]
    pf = sc.fundamental_pillar(ohlcv, fund).iloc[-1] if fund is not None else None
    # konteks flow per saham (informasi murni, tidak masuk skor)
    # foreign_5d: net (untuk sort + filter), buy/sell (untuk visual pill BELI/JUAL mobile)
    fnotes = {}
    fbuy = {}
    fsell = {}
    for s in fm:
        f = fm[s]
        if f is None or len(f) < 25: continue
        s5 = f.sort_values('date').tail(5)
        fnotes[s + '.JK'] = round(float(s5['net_foreign_inflow'].sum())/1e9, 1)   # IDR miliar
        fbuy[s + '.JK'] = round(float(s5['foreign_buy_idr'].sum())/1e9, 1)
        fsell[s + '.JK'] = round(float(s5['foreign_sell_idr'].sum())/1e9, 1)
    # Fair value + edge per saham (hanya untuk OK rows yg di frontend)
    fv = value.fair_value(ohlcv)
    rows = []
    for t, v in last.dropna().sort_values(ascending=False).items():
        fv_row = fv.get(t)
        rows.append({
            'symbol': t.replace('.JK',''), 'score': round(float(v), 2),
            'momentum': round(float(pm.get(t, np.nan)), 2) if pd.notna(pm.get(t)) else None,
            'fundamental': round(float(pf.get(t, np.nan)), 2) if pf is not None and pd.notna(pf.get(t)) else None,
            'liquid': bool(floor.get(t, False)),
            'foreign_5d_idrb': fnotes.get(t),
            'foreign_buy_5d': fbuy.get(t),
            'foreign_sell_5d': fsell.get(t),
            'fair': fv_row,
        })
    led = ledger.stats('flow_alert') or {'n': 0}
    return {'regime': 'UP' if reg_on else 'DOWN', 'regime_margin_pct': margin, 'asof': str(comp.index[-1].date()),
            'rows': rows, 'ledger': led}

PAGE = """<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ARUS — IDX Flow Screener</title>
<style>
*{box-sizing:border-box}
body{font-family:system-ui,sans-serif;max-width:1100px;margin:16px auto;padding:0 14px;background:#0e1117;color:#e6e6e6}
h1{font-size:22px;margin-bottom:4px}.sub{color:#8b949e;font-size:13px;margin-bottom:16px}
.regime{display:inline-block;padding:5px 12px;border-radius:6px;font-weight:600;margin-bottom:12px;font-size:14px}
.UP{background:#1b4332;color:#95d5b2}.DOWN{background:#4a1525;color:#f4a6b8}
/* table — desktop default, horizontal scroll pada layar sempit */
.tbl-wrap{overflow-x:auto;-webkit-overflow-scrolling:touch;margin-bottom:14px}
table{border-collapse:collapse;width:100%;min-width:760px}
th,td{padding:8px 10px;text-align:left;border-bottom:1px solid #21262d;font-size:13px;white-space:nowrap}
th{color:#8b949e;font-size:11px;text-transform:uppercase;cursor:pointer;user-select:none;font-weight:600}
th:hover{color:#e6e6e6}th.sort-asc::after{content:" ▲"}th.sort-desc::after{content:" ▼"}
.score{font-weight:700;font-size:15px}.pill{padding:2px 8px;border-radius:10px;font-size:11px;display:inline-block}
.g{background:#1b4332;color:#95d5b2}.r{background:#4a1525;color:#f4a6b8}.m{background:#30363d;color:#c9d1d9}
.foot{margin-top:16px;color:#8b949e;font-size:12px;border-top:1px solid #21262d;padding-top:10px}
.bar{height:7px;border-radius:4px;background:#30363d;width:70px;display:inline-block;vertical-align:middle;position:relative;margin-right:6px}
.fill{height:7px;border-radius:4px;display:block}
.f-hi{background:#2ea043}.f-mid{background:#d29922}.f-lo{background:#da3633}.f-na{background:#30363d}
.pct{font-size:11px;color:#8b949e;vertical-align:middle;margin-left:2px}
.controls{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin-bottom:12px;font-size:13px;color:#c9d1d9}
.controls select,.controls input[type=text]{background:#161b22;color:#e6e6e6;border:1px solid #30363d;border-radius:6px;padding:5px 8px;font-size:13px}
.controls input[type=text]{width:130px}
.controls label{color:#8b949e;display:inline-flex;align-items:center;gap:4px}
.star{cursor:pointer;font-size:18px;color:#30363d;user-select:none;-webkit-tap-highlight-color:transparent}
.star.on{color:#e3b341}
details{margin:14px 0;color:#c9d1d9;font-size:13px}
details summary{cursor:pointer;color:#58a6ff;font-weight:600;padding:6px 0}
details .x{background:#161b22;border:1px solid #21262d;border-radius:8px;padding:12px 16px;margin-top:8px;line-height:1.65}
details .x b{color:#e6e6e6}.x .q{color:#79c0ff}.x .a{color:#7ee787}
/* mobile card view — default hidden, shown via @media */
.cards{display:none}
.card{background:#161b22;border:1px solid #21262d;border-radius:10px;padding:12px 14px;margin-bottom:10px}
.card-head{display:flex;justify-content:space-between;align-items:center;margin-bottom:8px}
.card-sym{font-size:18px;font-weight:700}
.card-score{font-size:24px;font-weight:700;line-height:1}
.card-row{display:flex;justify-content:space-between;align-items:center;padding:4px 0;font-size:13px;border-top:1px solid #21262d}
.card-row:first-of-type{border-top:none}
.card-lbl{color:#8b949e;font-size:12px}
.card-val{color:#e6e6e6;font-size:13px;text-align:right}
/* tablet */
@media (max-width:900px){
  body{max-width:100%}
  th,td{padding:6px 8px;font-size:12px}
  .bar{width:55px}
  h1{font-size:20px}
  .regime{font-size:13px}
}
/* mobile — switch from table to cards */
@media (max-width:640px){
  body{padding:0 10px;margin:10px auto}
  h1{font-size:18px}.sub{font-size:12px;margin-bottom:12px}
  .regime{padding:4px 10px;font-size:12px;margin-bottom:10px}
  .controls{gap:8px;font-size:12px}
  .controls input[type=text]{width:90px;font-size:12px}
  .controls select{padding:4px 6px;font-size:12px}
  .tbl-wrap{display:none}
  .cards{display:block}
  .card{padding:10px 12px}
  .card-sym{font-size:16px}
  .card-score{font-size:22px}
  .card-row{padding:3px 0;font-size:12px}
  .card-lbl,.card-val{font-size:12px}
  /* regime pills full-width on small screens */
  .controls > * {flex:1 1 auto;min-width:0}
}
</style></head><body>
<h1>ARUS</h1>
<div class="sub">Screener IDX — momentum &times; fundamental &times; aliran dana (data: Sectors API). Data per <span id=asof></span> · <a href="#cara-baca" style="color:#58a6ff;text-decoration:none">cara baca ↓</a></div>
<div id=regime class="regime"></div>
<div class="controls">
  <label title="klik judul kolom tabel untuk mengurutkan ▲▼">Urut:</label>
  <b id=sortlabel>Skor ▼</b>
  <label>Status:</label>
  <select id=stat>
    <option value="">Semua</option>
    <option value="ok">OK</option>
    <option value="wait">WAIT/SKIP</option>
  </select>
  <label><input type=checkbox id=only-foreign> Asing +5d</label>
  <input type=text id=q placeholder="cari (BBCA)">
  <button id=lookup-btn style="background:#21262d;color:#58a6ff;border:1px solid #30363d;border-radius:6px;padding:5px 10px;cursor:pointer">analisis</button>
  <label><input type=checkbox id=watch> ★</label>
</div>
<div id=lookup-box style="display:none;background:#161b22;border:1px solid #30363d;border-radius:8px;padding:12px 16px;margin-bottom:12px;font-size:13px"></div>
<div class="tbl-wrap"><table><thead><tr>
<th data-k=symbol style="cursor:pointer">Saham</th><th data-k=score style="cursor:pointer">Skor</th><th data-k=momentum style="cursor:pointer">Momentum</th><th data-k=fundamental style="cursor:pointer">Funda</th><th data-k=foreign style="cursor:pointer">Asing 5d</th><th data-k=fair style="cursor:pointer" title="Posisi harga saat ini vs median close 252 hari (±8% pita). murah = di bawah pita bawah, netral = dalam pita, mahal = di atas pita atas. Bukan saran beli/jual, hanya konteks.">Acuan</th><th data-k=target style="cursor:pointer" title="Target +20d (backtest top-5 median spread +1.65%/20d) & Stop-loss (52-week low)">Target / Stop</th><th data-k=status>Status</th><th title="klik ★ untuk watchlist">★</th>
</tr></thead>
<tbody id=tb></tbody></table></div>
<div class="cards" id=cb></div>
<div class=foot id=ledger></div>
<details id=cara-baca><summary>Cara baca halaman ini — skor itu apa?</summary>
<div class=x>
<b>Skor (0–100) = peringkat gabungan Momentum 55% + Fundamental 45%</b> — bukan harga target, bukan persentase naik. Artinya: <i>di antara 21 saham besar IDX yang kami pantau, saham ini ada di peringkat ke-N</i>. Skor 80 = top 20%; skor 30 = bottom 30%. Saham di atas mengalahkan saham di bawah pada backtest 5 tahun (IC +0.093, top-5 vs bottom-5 menang 63% dari 38 rebalance).
<br><br>
<span class=q>Momentum</span> = konsistensi arah harga 20/60/120 hari, disesuaikan volatilitas. <i>Naik tinggi tapi naik dadak → tidak dinilai.</i>
<br><span class=q>Fundamental</span> = ROE + laba/harga, dengan penalti untuk growth-trap (pertumbuhan revenue tinggi yang sering menipu di IDX).
<br><span class=q>Asing 5d</span> = uang investor asing masuk (+) atau keluar (−) 5 hari terakhir, dari data transaksi Sectors. Pill <span class=g>BELI X%</span> / <span class=r>JUAL X%</span> = proporsi gross beli vs jual 5 hari, warna sesuai NET (positif=green, negatif=red). <b>Kolom informasi, bukan sinyal</b> — kami mengujinya sebagai sinyal dan hasilnya negatif (detail di README), jadi ditampilkan apa adanya.
<br><span class=q>Acuan</span> = posisi harga saat ini vs median close 252 hari (±8% pita). <span class=g>murah</span> artinya harga di bawah pita bawah — pasar menilai lebih murah dari setahun ke belakang. <span class=r>mahal</span> sebaliknya. <span class=m>netral</span> = dalam pita. Bukan saran beli/jual, hanya konteks.
<br><span class=q>Target / Stop</span> = Target = harga +20d pakai backtest combo momentum+fundamental median spread +1.65%. Stop = 52-week low. Keduanya bukan prediksi ARUS, hanya turunan dari backtest & data historis.
<br><span class=q>Status</span> = <span class=a>OK</span>: likuid &amp; IHSG di atas EMA50 → boleh dipertimbangkan. <span style="color:#f4a6b8">WAIT</span>: IHSG lemah → tunggu. <span style="color:#c9d1d9">SKIP</span>: likuiditas rendah → hindari.
<br><br>
<b>Regime</b>: semua saham jadi WAIT saat IHSG di bawah EMA50 — momentum saham jarang menang saat indeks jatuh; itu hasil backtest, bukan opini.
</div></details>
<div class=foot>Skor = ranking probabilitas, bukan prediksi pasti. Backtest momentum+fundamental: IC +0.093 (n=38 rebalance, top&gt;bot 63%). Kolom flow = <b>informasi, bukan sinyal</b> — backtest kami menunjukkan flow belum bisa dipercaya sebagai sinyal (detail di README); tiap sinyal flow dicatat ke ledger dan diukur hasilnya setelah 20 hari. Bukan rekomendasi beli/jual.</div>
<script>
let D=null;let WL=new Set(JSON.parse(localStorage.getItem('arus-watchlist')||'[]'));
fetch('/api').then(r=>r.json()).then(d=>{D=d;render();});
function fmtForeign(r){if(r.foreign_5d_idrb==null)return null;const a=Math.abs(r.foreign_5d_idrb);
 const s=a>=1000?(a/1000).toFixed(2)+' T':a.toFixed(0)+' M';
 const buy=r.foreign_buy_5d, sell=r.foreign_sell_5d;
 // pill BELI/JUAL/NETRAL: dominan = arah mana yg lebih besar 5d gross; warna sesuai NET (sign)
 let pill=null;
 if(buy!=null&&sell!=null&&(buy+sell)>0){
   const dom=buy>=sell?'BELI':'JUAL';
   const pct=Math.round(buy/(buy+sell)*100);
   const cls=r.foreign_5d_idrb>0?'g':(r.foreign_5d_idrb<0?'r':'m');
   pill=`<span class="pill ${cls}" title="gross 5d: beli ${buy>=1000?(buy/1000).toFixed(1)+' T':buy.toFixed(0)+' M'} / jual ${sell>=1000?(sell/1000).toFixed(1)+' T':sell.toFixed(0)+' M'}">${dom} ${pct}%</span>`;
 }
 return {raw:r.foreign_5d_idrb,txt:(r.foreign_5d_idrb>0?'+':'−')+s+' IDR',pill:pill};}
let SORTK='score',SORTD=-1;   // klik header: kolom, arah (−1 = desc dulu)
function render(){
const d=D;
document.getElementById('asof').textContent=d.asof;const rg=document.getElementById('regime');const mg=d.regime_margin_pct!=null?` (${d.regime_margin_pct>=0?'+':''}${d.regime_margin_pct}% vs EMA50)`:'';rg.textContent=d.regime==='UP'?`IHSG regime: UP${mg} — scanning`:`IHSG regime: DOWN${mg} — mode tunggu, jangan entry`;rg.className='regime '+d.regime;
const sort=SORTK,sortDir=SORTD;
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
const key={symbol:r=>r.symbol,score:r=>r.score??-1,momentum:r=>r.momentum??-1,fundamental:r=>r.fundamental??-1,foreign:r=>r.foreign_5d_idrb??-Infinity,fair:r=>r.fair?.fair_mid??-1,target:r=>r.fair?.target_20d??-1};
const dir=sort==='symbol'?1:sortDir;
rows.sort((a,b)=>{const ka=key[sort](a),kb=key[sort](b);return ka===kb?0:(ka>kb?dir:-dir);});
const KLBL={symbol:'Saham',score:'Skor',momentum:'Momentum',fundamental:'Funda',foreign:'Asing 5d',fair:'Acuan',target:'Target / Stop'};
document.getElementById('sortlabel').textContent=KLBL[sort]+(dir===1?' ▲':' ▼');
document.querySelectorAll('th').forEach(th=>{th.className=th.dataset.k===sort?(dir===1?'sort-asc':'sort-desc'):'';});
const bar=(v)=>v==null?'<span class="pill m">n/a</span>':`<span class=bar><span class="fill ${v>=0.6?'f-hi':v>=0.4?'f-mid':'f-lo'}" style="width:${Math.round(v*100)}%"></span></span><span class="pct">${Math.round(v*100)}%</span>`;
window.pbar=bar;
const fmtPrice=(n)=>n==null?'—':Math.round(n).toLocaleString('id-ID');
const fmtFair=(r)=>{
  if(!r.fair) return '—';
  const f=r.fair;
  // murah/netral/mahal — warna hijau untuk murah, merah untuk mahal
  const color=f.pos_band==='murah'?'g':(f.pos_band==='mahal'?'r':'m');
  return `<span class=${color} title="current ${fmtPrice(f.current)} vs median 252d ${fmtPrice(f.fair_mid)} (pita ${fmtPrice(f.fair_low)}–${fmtPrice(f.fair_high)})">${f.pos_band}</span><div style="font-size:11px;color:#8b949e">${fmtPrice(f.fair_low)}–${fmtPrice(f.fair_high)}</div>`;
};
const fmtTarget=(r)=>{
  if(!r.fair) return '—';
  const f=r.fair;
  const upCol=f.target_20d>=f.current?'g':'m';
  return `<span class=${upCol} title="Target +20d backtest combo m+f median spread">${fmtPrice(f.target_20d)}</span> <span style="color:#8b949e">/</span> <span class=r title="Stop-loss = 52-week low">${fmtPrice(f.stop_loss)}</span>`;
};
document.getElementById('tb').innerHTML=rows.map(r=>{
const st=stOf(r);const stc=st==='OK'?'g':(st==='WAIT'?'r':'m');
const f=fmtForeign(r);const fg=f==null?'—':(f.raw>0?`<span class=g>${f.txt}</span>`:`<span class=r>${f.txt}</span>`);
return `<tr><td><b>${r.symbol}</b></td><td>${bar(r.score)}</td><td>${bar(r.momentum)}</td><td>${bar(r.fundamental)}</td><td>${fg}${(f&&f.pill)?`<div style="margin-top:4px">${f.pill}</div>`:''}</td><td>${fmtFair(r)}</td><td>${fmtTarget(r)}</td><td><span class="pill ${stc}">${st}</span></td><td><span class="star ${WL.has(r.symbol)?'on':''}" data-s=${r.symbol}>${WL.has(r.symbol)?'★':'☆'}</span></td></tr>`}).join('');
// Mobile card view — same data, stacked layout
document.getElementById('cb').innerHTML=rows.map(r=>{
  const st=stOf(r);const stc=st==='OK'?'g':(st==='WAIT'?'r':'m');
  const f=fmtForeign(r);
  const fv=r.fair;
  const acuanBadge=fv?`<span class="pill ${fv.pos_band==='murah'?'g':(fv.pos_band==='mahal'?'r':'m')}">${fv.pos_band}</span>`:'—';
  const acuanRange=fv?`<span class=card-val>${fmtPrice(fv.fair_low)}–${fmtPrice(fv.fair_high)}</span>`:'—';
  const target=fv?`<span class=card-val>${fmtPrice(fv.target_20d)} <span style="color:#8b949e">/</span> <span class=r>${fmtPrice(fv.stop_loss)}</span></span>`:'—';
  return `<div class="card">
<div class="card-head"><div class="card-sym">${r.symbol}<span class="star ${WL.has(r.symbol)?'on':''}" data-s=${r.symbol} style="margin-left:8px;font-size:16px">${WL.has(r.symbol)?'★':'☆'}</span></div><div class="card-score">${bar(r.score)}<span class="pill ${stc}" style="margin-left:6px">${st}</span></div></div>
<div class="card-row"><span class=card-lbl>Asing 5d</span><span class=card-val>${f?`${f.raw>0?'+':'−'}${f.txt}`:'—'}${f&&f.pill?`<div style="margin-top:4px">${f.pill}</div>`:''}</span></div>
<div class="card-row"><span class=card-lbl>Acuan</span>${acuanRange}</div>
<div class="card-row"><span class=card-lbl>Acuan (status)</span><span class=card-val>${acuanBadge}</span></div>
<div class="card-row"><span class=card-lbl>Target / Stop</span>${target}</div>
<div class="card-row"><span class=card-lbl>Momentum</span><span class=card-val>${bar(r.momentum)}</span></div>
<div class="card-row"><span class=card-lbl>Fundamental</span><span class=card-val>${bar(r.fundamental)}</span></div>
</div>`}).join('');
// wire up stars in card view (table stars handled by static delegation)
function toggleWL(sym){if(WL.has(sym))WL.delete(sym);else WL.add(sym);localStorage.setItem('arus-watchlist',JSON.stringify([...WL]));render();}
document.querySelectorAll('.card .star').forEach(s=>{s.onclick=()=>toggleWL(s.dataset.s);});
document.getElementById('ledger').innerHTML='Ledger sinyal flow: '+(d.ledger.n>0?`n=${d.ledger.n}, hit ${(d.ledger.hit*100).toFixed(0)}%, median ${(d.ledger.med*100).toFixed(1)}%`:'n=0 — rapor mulai terisi saat cron live aktif');
}
['stat','only-foreign','watch'].forEach(id=>document.getElementById(id).addEventListener('change',render));
document.querySelectorAll('th[data-k]').forEach(th=>th.addEventListener('click',()=>{
if(SORTK===th.dataset.k)SORTD=-SORTD;else{SORTK=th.dataset.k;SORTD=th.dataset.k==='symbol'?1:-1;}
render();}));
document.getElementById('q').addEventListener('input',render);
document.getElementById('lookup-btn').addEventListener('click',async()=>{
const sym=document.getElementById('q').value.trim().toUpperCase();
const box=document.getElementById('lookup-box');
if(!sym){box.style.display='none';return;}
box.style.display='block';box.innerHTML='menganalisis '+sym+'… (harga Sectors + fundamental, ~2–4 kredit)';
try{
const r=await fetch('/lookup?s='+encodeURIComponent(sym)).then(r=>r.json());
if(!r.ok){box.innerHTML='<b>'+sym+'</b>: '+r.error;return;}
const x=r.result;
const pct=v=>v==null?'n/a':(v*100).toFixed(0)+'%';
const spark=x.spark||[];
const w=220,h=44;
const mn=Math.min(...spark),mx=Math.max(...spark),rg=(mx-mn)||1;
const pts=spark.map((v,i)=>`${(i/(spark.length-1||1)*w).toFixed(1)},${(h-4-(v-mn)/rg*(h-8)).toFixed(1)}`).join(' ');
const up=spark.length>1&&spark[spark.length-1]>=spark[0];
const col=x.score==null?'#8b949e':(x.score>=0.6?'#3fb950':(x.score>=0.4?'#d29922':'#f85149'));
box.innerHTML=`<div style="display:flex;gap:18px;align-items:center;flex-wrap:wrap">
<div style="flex:1;min-width:200px"><b style="font-size:16px">${x.symbol}</b> <span style="color:#8b949e">${x.name}</span><div style="margin:8px 0;font-size:26px;color:${col}"><b>${x.score!=null?(x.score*100).toFixed(0):'n/a'}</b><span style="font-size:13px;color:#8b949e"> /100</span></div>
<div style="font-size:12px;color:#c9d1d9">momentum ${pct(x.momentum_pct)} ${window.pbar(x.momentum_pct)}</div>
<div style="font-size:12px;color:#c9d1d9;margin-top:4px">fundamental ${pct(x.fundamental_pct)} ${window.pbar(x.fundamental_pct)}</div></div>
<div style="text-align:center"><svg width="${w}" height="${h}" style="display:block"><polyline fill="none" stroke="${up?'#3fb950':'#f85149'}" stroke-width="2" points="${pts}"/></svg><div style="font-size:11px;color:#8b949e">60 hari terakhir${up?' ▲':' ▼'}</div></div>
</div>
<div style="color:#8b949e;margin-top:8px;font-size:12px">${x.bars} bar harga · skor = persentil vs 21 saham universe · ${x.note}. Biaya: ${x.spent} kredit.</div>
<div style="margin-top:10px;display:flex;gap:8px;align-items:center">
<button id="add-btn-${x.symbol}" style="background:#1f6feb;color:#fff;border:0;padding:6px 12px;border-radius:4px;cursor:pointer">+ Tambah ke Universe</button>
<span id="add-status-${x.symbol}" style="font-size:12px;color:#8b949e"></span>
</div>`;
document.getElementById('add-btn-'+x.symbol).onclick=async()=>{
if(!confirm(`Tambah ${x.symbol} ke universe?\n\nBiaya ~46 kredit (sekali, history 5 tahun + broker + foreign).\nLimit harian 3 ticker. Lanjut?`))return;
const btn=document.getElementById('add-btn-'+x.symbol);const st=document.getElementById('add-status-'+x.symbol);
btn.disabled=true;btn.textContent='menambahkan…';
try{
const r=await fetch('/add',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({s:x.symbol})}).then(r=>r.json());
if(r.ok){st.style.color='#3fb950';st.textContent='✓ masuk universe ('+r.spent+' kredit) — refresh untuk lihat di tabel';}
else{st.style.color='#f85149';st.textContent='✗ '+r.error;btn.disabled=false;btn.textContent='+ Tambah ke Universe';}
}catch(e){st.style.color='#f85149';st.textContent='✗ '+e.message;btn.disabled=false;btn.textContent='+ Tambah ke Universe';}};
}catch(e){box.innerHTML='lookup gagal: '+e;}
});
document.getElementById('tb').addEventListener('click',e=>{
const s=e.target.closest('.star');if(!s)return;
toggleWL(s.dataset.s);});
</script></body></html>"""

class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    _lookup_times = []   # timestamp detik terakhir, utk rate limit
    def do_GET(self):
        if self.path == '/api':
            body = json.dumps(build_rows()).encode()
            self.send_response(200); self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body))); self.end_headers(); self.wfile.write(body)
        elif self.path.startswith('/lookup?'):
            import time as _t
            now = _t.time()
            H._lookup_times = [x for x in H._lookup_times if now - x < 60]
            if len(H._lookup_times) >= 5:
                body = json.dumps({'ok': False, 'result': None, 'error': 'terlalu banyak permintaan — maks 5 lookup/menit'}).encode()
                self.send_response(429); self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(body))); self.end_headers(); self.wfile.write(body)
                return
            H._lookup_times.append(now)
            from urllib.parse import parse_qs, urlparse
            sym = (parse_qs(urlparse(self.path).query).get('s') or [''])[0]
            from scripts.lookup import lookup
            try:
                res, spent, err = lookup(sym)
            except Exception as e:
                res, err = None, str(e)[:120]
            body = json.dumps({'ok': err is None, 'result': res, 'error': err}).encode()
            self.send_response(200); self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body))); self.end_headers(); self.wfile.write(body)
        else:
            body = PAGE.encode()
            self.send_response(200); self.send_header('Content-Type', 'text/html')
            self.send_header('Content-Length', str(len(body))); self.end_headers(); self.wfile.write(body)

    def do_POST(self):
        import subprocess, re, datetime as dt
        if self.path == '/add':
            try:
                ln = int(self.headers.get('Content-Length') or 0)
                body = self.rfile.read(ln).decode('utf-8', 'replace')
                req = json.loads(body)
                sym = (req.get('s') or '').upper().strip()
            except Exception:
                sym = ''
            # sanitize — sama dengan lookup
            sym = re.sub(r'[^A-Z0-9]', '', sym.replace('.JK', ''))[:8]
            if not sym:
                self._json(400, {'ok': False, 'error': 'ticker kosong / format salah'}); return
            if sym in cfg.UNIVERSE:
                self._json(200, {'ok': False, 'error': f'{sym} sudah ada di universe', 'spent': 0}); return
            # cek limit harian dari fetch.log
            from scripts.fetch_sectors import LOG
            today = f'{dt.date.today():%Y-%m-%d}'
            n_today = sum(1 for l in open(LOG) if l.startswith(today) and 'add_universe' in l)
            limit = int(os.getenv('ARUS_ONDEMAND_LIMIT', '3'))
            if n_today >= limit:
                self._json(429, {'ok': False, 'error': f'limit harian {limit} ticker tercapai — coba besok', 'spent': 0}); return
            # spawn fetch_one.py — synchronous ~30-90 detik
            try:
                p = subprocess.run([sys.executable, 'scripts/fetch_one.py', sym],
                                   capture_output=True, text=True, timeout=180,
                                   cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                if p.returncode != 0:
                    self._json(500, {'ok': False, 'error': (p.stderr or p.stdout or 'gagal')[-200:], 'spent': 0}); return
                # append ke UNIVERSE
                cfg_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'app', 'config.py')
                with open(cfg_path) as f: src = f.read()
                if f"'{sym}'" not in src:
                    src = src.replace("UNIVERSE = [", f"UNIVERSE = ['{sym}', ", 1)
                    with open(cfg_path, 'w') as f: f.write(src)
                    # reload modul di-process
                    import importlib
                    importlib.reload(cfg)
                # hitung spent dari log
                spent = 0
                with open(LOG) as f: f.seek(0)
                spent_line = [l for l in open(LOG) if l.startswith(today) and 'add_universe' in l]
                spent = len(spent_line) * 46   # estimate; fetch_one tidak return persis
                self._json(200, {'ok': True, 'symbol': sym, 'spent': spent, 'note': 'tambah ke UNIVERSE, fetch harian otomatis besok'})
            except subprocess.TimeoutExpired:
                self._json(504, {'ok': False, 'error': 'timeout (>180s) — coba lagi', 'spent': 0})
            except Exception as e:
                self._json(500, {'ok': False, 'error': str(e)[:200], 'spent': 0})
        else:
            self._json(404, {'ok': False, 'error': 'endpoint tidak dikenal'})

    def _json(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code); self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body))); self.end_headers(); self.wfile.write(body)

if __name__ == '__main__':
    print('ARUS screener: http://localhost:8787')
    HTTPServer(('0.0.0.0', 8787), H).serve_forever()
