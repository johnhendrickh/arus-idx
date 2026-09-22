"""ledger_resolve.py — cron harian utk isi outcome_fwd20 dari ledger.

Dipanggil setelah 20 hari trading setelah sinyal flow dicatat.
Mengambil harga close +20 hari vs price_ref, hitung return, simpan ke ledger.

Usage:
    python scripts/ledger_resolve.py

Cron (setelah market close, bursa-buka detector safe):
    15 17 * * 1-5  cd ~/idx-signal && .venv/bin/python scripts/ledger_resolve.py >> data/fetch.log 2>&1
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from app import io_cache, ledger

def main():
    if not os.path.exists(ledger.LEDGER):
        print('ledger belum ada — belum ada sinyal flow dicatat.')
        return
    # Kumpulkan OHLCV semua saham di universe (cache sudah di-populate oleh fetch_sectors_prices)
    from app import config as cfg
    ohlcv = {}
    for sym in cfg.UNIVERSE:
        df = io_cache.read_ohlcv(sym + '.JK')
        if df is not None and len(df) > 0:
            ohlcv[sym + '.JK'] = df
    if not ohlcv:
        print('cache kosong — jalankan scripts/fetch_sectors_prices.py dulu')
        return
    # Snapshot size sebelum
    import pandas as pd
    pre = pd.read_csv(ledger.LEDGER)
    n_unresolved = int(pre['outcome_fwd20'].isna().sum()) if 'outcome_fwd20' in pre.columns else 0
    print(f'ledger: {len(pre)} rows, {n_unresolved} unresolved')
    # Resolve
    ledger.resolve(ohlcv)
    # Snapshot size sesudah
    post = pd.read_csv(ledger.LEDGER)
    n_filled = int(post['outcome_fwd20'].notna().sum()) if 'outcome_fwd20' in post.columns else 0
    print(f'ledger: {n_filled}/{len(post)} rows have outcome_fwd20')
    # Stats per signal_type
    for sigtype in post['signal_type'].unique():
        s = ledger.stats(sigtype)
        if s and s.get('n', 0) > 0:
            print(f'  stats({sigtype}): n={s["n"]}, hit={s["hit"]*100:.0f}%, median={s["med"]*100:+.2f}%')

if __name__ == '__main__':
    main()
