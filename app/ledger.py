"""ledger.py — buku catat sinyal live. Tiap alert dicatat, 20 hari kemudian
otomatis diisi hasilnya. Ini rapor yang tumbuh sendiri (fitur honesty)."""
import pandas as pd, os, numpy as np
LEDGER = os.path.join(os.path.dirname(__file__), '..', 'data', 'ledger.csv')
HOLD = 20

def record(date, symbol, signal_type, score, price_ref, note=''):
    df = pd.read_csv(LEDGER) if os.path.exists(LEDGER) else pd.DataFrame(
        columns=['date','symbol','signal_type','score','price_ref','note','outcome_fwd20'])
    df = df[~((df['date'] == str(date)) & (df['symbol'] == symbol) & (df['signal_type'] == signal_type))]
    df = pd.concat([df, pd.DataFrame([{'date': str(date), 'symbol': symbol,
        'signal_type': signal_type, 'score': round(float(score), 3),
        'price_ref': price_ref, 'note': note, 'outcome_fwd20': np.nan}])],
        ignore_index=True)
    df.to_csv(LEDGER, index=False)

def resolve(ohlcv):
    """Isi outcome untuk sinyal yang sudah cukup umur (harga close +20d vs ref)."""
    if not os.path.exists(LEDGER): return
    df = pd.read_csv(LEDGER)
    for i in df.index[df['outcome_fwd20'].isna()]:
        s = df['symbol'][i]
        if s not in ohlcv: continue
        c = ohlcv[s].Close
        d = pd.Timestamp(df['date'][i])
        after = c.loc[c.index >= d]     # fallback: baris pertama >= tanggal sinyal (weekend-safe)
        if len(after) > HOLD:
            df.loc[i, 'outcome_fwd20'] = round(float(after.iloc[HOLD]/df['price_ref'][i] - 1), 4)
    df.to_csv(LEDGER, index=False)

def stats(signal_type=None):
    if not os.path.exists(LEDGER): return None
    df = pd.read_csv(LEDGER)
    if signal_type: df = df[df['signal_type'] == signal_type]
    done = df[df['outcome_fwd20'].notna()]
    if not len(done): return {'n': 0}
    return {'n': len(done), 'hit': float((done['outcome_fwd20'] > 0).mean()),
            'med': float(done['outcome_fwd20'].median())}
