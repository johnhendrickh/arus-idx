"""main.py — pipeline harian: cache -> skor -> tabel + (opsi) alert.
Scan TIDAK memanggil API. Cron: 16.15 WIB setelah close."""
import pandas as pd, numpy as np, sys
from app import config as cfg, io_cache, score as sc, alert

def load_cache():
    ohlcv = {}
    for s in cfg.UNIVERSE:
        df = io_cache.read_ohlcv(s+'.JK')
        if df is not None and len(df) > 200: ohlcv[s+'.JK'] = df
    idx = io_cache.read_ohlcv('_JKSE')
    return ohlcv, (idx.Close if idx is not None else None)

def scan(index_close=None):
    ohlcv, idx_c = load_cache()
    if not ohlcv: sys.exit('cache kosong — jalankan scripts/fetch_yahoo.py dulu')
    fund = io_cache.read_fund()
    s = sc.composite(ohlcv, fund, index_close=idx_c)
    if s is None: sys.exit('semua pilar kosong')
    last = s.iloc[-1].dropna().sort_values(ascending=False)
    floor = sc.liquidity_floor(ohlcv).iloc[-1]
    reg = (sc.regime(ohlcv, idx_c).iloc[-1] if idx_c is not None else True)
    rows = []
    for t, v in last.items():
        if not floor.get(t, True):
            rows.append((t, v, 'SKIP (illiquid)')); continue
        rows.append((t, v, 'OK' if reg else 'WAIT (IHSG<EMA50)'))
    return rows, reg

if __name__ == '__main__':
    rows, reg = scan()
    print(f"ARUS SCAN — {pd.Timestamp.now():%Y-%m-%d %H:%M} WIB | regime IHSG: {'UP' if reg else 'DOWN → mode tunggu'}")
    print('-'*58)
    for t, v, st in rows[:8]:
        print(f'{t.replace(".JK",""):6s} skor {v:.2f}  {st}')
    msg = alert.format_alert(rows, reg)
    print('\n--- alert preview ---\n' + msg)
    if cfg.TELEGRAM_ENABLED: alert.send(msg)
