"""main.py — pipeline harian: cache -> skor -> tabel + (opsi) alert.
Scan TIDAK memanggil API. Cron: 16.15 WIB setelah close."""
import pandas as pd, numpy as np, sys
from app import config as cfg, io_cache, score as sc, alert, ledger

def load_cache():
    ohlcv, broker_map, foreign_map = {}, {}, {}
    for s in cfg.UNIVERSE:
        df = io_cache.read_ohlcv(s+'.JK')
        if df is not None and len(df) > 200: ohlcv[s+'.JK'] = df
        b = io_cache.read_broker(s)
        if b is not None: broker_map[s] = b
        f = io_cache.read_foreign(s)
        if f is not None: foreign_map[s] = f
    idx = io_cache.read_ohlcv('_JKSE')
    return ohlcv, broker_map, foreign_map, (idx.Close if idx is not None else None)

def flow_context(bm, fm):
    """Konteks flow per saham utk tampilan/alert: f5 asing + arah broker bulanan.
    Informasi murni — TIDAK mengubah skor (lihat config.py kenapa)."""
    ctx = {}
    for sym in set(list(bm) + list(fm)):
        line = []
        if sym in fm and fm[sym] is not None and len(fm[sym]):
            f5 = fm[sym]['net_foreign_inflow'].tail(5).sum() / 1e9
            line.append(('asing 5d', f'{f5:+.1f}M IDR' if abs(f5) < 1000 else f'{f5/1000:+.2f}T IDR'))
        if sym in bm and bm[sym] is not None and len(bm[sym]):
            b = bm[sym]
            agg = b[b.side == 'top_buyers'].groupby('month')['net_idr'].sum().sort_index()
            if len(agg) >= 2:
                d = agg.iloc[-1] - agg.iloc[-2]
                line.append(('broker-top', 'akumulasi naik' if d > 0 else 'akumulasi turun'))
        if line:
            ctx[sym] = ', '.join(f'{k}: {v}' for k, v in line)
    return ctx

def scan(index_close=None):
    ohlcv, broker_map, foreign_map, idx_c = load_cache()
    if not ohlcv: sys.exit('cache kosong — jalankan scripts/fetch_sectors_prices.py dulu')
    fund = io_cache.read_fund()
    s = sc.composite(ohlcv, fund, broker_map=broker_map or None,
                     foreign=foreign_map or None, index_close=idx_c)
    if s is None: sys.exit('semua pilar kosong')
    last = s.iloc[-1].dropna().sort_values(ascending=False)
    floor = sc.liquidity_floor(ohlcv).iloc[-1]
    if idx_c is None:
        reg = False   # fail-CLOSED: tanpa data IHSG jangan pernah label OK
    else:
        reg = bool(sc.regime(ohlcv, idx_c).iloc[-1])
    rows = []
    for t, v in last.items():
        if not floor.get(t, True):
            rows.append((t, v, 'SKIP (illiquid)')); continue
        rows.append((t, v, 'OK' if reg else 'WAIT (IHSG<EMA50)'))
    return rows, reg

def scan_full():
    """Scan + konteks flow per saham (utk alert & screener)."""
    ohlcv, broker_map, foreign_map, idx_c = load_cache()
    rows, reg = scan()
    ctx = flow_context(broker_map, foreign_map)
    return rows, reg, ctx

def record_to_ledger(rows, dry_run=False):
    """Catat sinyal flow ke data/ledger.csv. Idempotent per (date, sym, signal_type).
    Hanya rows yang punya flow context yang dicatat (kualitas > kuantitas)."""
    _, broker_map, foreign_map, _ = load_cache()
    ctx = flow_context(broker_map, foreign_map)
    today = pd.Timestamp.now().strftime('%Y-%m-%d')
    recorded = 0
    for t, v, st in rows:
        sym = t.replace('.JK', '')
        if sym not in ctx:
            continue
        ledger.record(today, sym, 'flow_alert', v, None, ctx[sym][:80])
        recorded += 1
    if recorded:
        mode = 'dry-run' if dry_run else 'live alert'
        print(f"--- ledger: recorded {recorded} signals ({mode}) ---")

if __name__ == '__main__':
    rows, reg = scan()
    # margin IHSG vs EMA50 utk konteks alert
    _, _, _, idx_c = load_cache()
    margin = None
    if idx_c is not None:
        ema = idx_c.ewm(span=cfg.REGIME_EMA_SPAN, adjust=False).mean().iloc[-1]
        margin = round(float(idx_c.iloc[-1]/ema - 1)*100, 2)
    print(f"ARUS SCAN — {pd.Timestamp.now():%Y-%m-%d %H:%M} WIB | regime IHSG: {'UP' if reg else 'DOWN → mode tunggu'}"
          + (f' | margin {margin:+.2f}%' if margin is not None else ''))
    print('-'*58)
    for t, v, st in rows[:8]:
        print(f'{t.replace(".JK","")}   skor {v:.2f}  {st}')
    msg = alert.format_alert(rows, reg, margin)
    print('\n--- alert preview ---\n' + msg)
    if cfg.TELEGRAM_ENABLED:
        alert.send(msg)
    record_to_ledger(rows, dry_run=not cfg.TELEGRAM_ENABLED)
