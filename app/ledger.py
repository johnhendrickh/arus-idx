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
        # symbol di ledger tanpa .JK (BBCA), di ohlcv dengan .JK (BBCA.JK) — normalize
        candidates = [s, s + '.JK']
        match = next((k for k in candidates if k in ohlcv), None)
        if match is None: continue
        c = ohlcv[match].Close
        d = pd.Timestamp(df['date'][i])
        after = c.loc[c.index >= d]     # fallback: baris pertama >= tanggal sinyal (weekend-safe)
        if len(after) > HOLD:
            ref = df['price_ref'][i]
            if pd.isna(ref) or ref == 0:
                # kalau price_ref kosong, fallback ke close hari sinyal
                ref = float(after.iloc[0])
            df.loc[i, 'outcome_fwd20'] = round(float(after.iloc[HOLD]/ref - 1), 4)
    df.to_csv(LEDGER, index=False)

def stats(signal_type=None):
    """Return {n: total, done: resolved_count, hit: hit_rate, med: median_return}.
    n = total rows; done = rows dengan outcome_fwd20 terisi. hit/med = dari done saja."""
    if not os.path.exists(LEDGER): return None
    df = pd.read_csv(LEDGER)
    if signal_type: df = df[df['signal_type'] == signal_type]
    done = df[df['outcome_fwd20'].notna()]
    if not len(done):
        return {'n': len(df), 'done': 0, 'hit': None, 'med': None}
    return {'n': len(df), 'done': int(len(done)),
            'hit': float((done['outcome_fwd20'] > 0).mean()),
            'med': float(done['outcome_fwd20'].median())}
