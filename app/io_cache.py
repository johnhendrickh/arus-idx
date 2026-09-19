"""io_cache.py — baca/tulis cache CSV. Satu-satunya modul yang sentuh disk.
Cache-first: produk & backtest TIDAK PERNAH manggil API saat run."""
import pandas as pd, os
CACHE = os.path.join(os.path.dirname(__file__), '..', 'data', 'cache')

def path(name): return os.path.join(CACHE, name)

def read_ohlcv(symbol):
    """CSV standar: Date,Open,High,Low,Close,Volume (index date, tz-naive).
    Baris volume=0 dibuang: baris hantu libur dari Sectors (OHLC flat, vol 0)
    merusak rolling window di grid gabungan (bug 19 Sep: 9/21 saham kehilangan momentum)."""
    p = path(f'{symbol}.csv')
    if not os.path.exists(p): return None
    df = pd.read_csv(p, index_col=0, parse_dates=True)
    df.index = pd.to_datetime(df.index, utc=True).tz_localize(None)
    df = df[['Open','High','Low','Close','Volume']]
    return df[df['Volume'].fillna(0) > 0]

def read_broker(symbol):
    """CSV: date,broker_code,net_idr,buy_idr,sell_idr (per hari/rentang dari Sectors)."""
    p = path(f'broker_{symbol}.csv')
    return pd.read_csv(p, index_col=0, parse_dates=True) if os.path.exists(p) else None

def read_foreign(symbol=None):
    p = path('foreign_daily.csv' if symbol is None else f'foreign_{symbol}.csv')
    return pd.read_csv(p, index_col=0, parse_dates=True) if os.path.exists(p) else None

def read_fund():
    """CSV: symbol,date,net_income,total_revenue,equity (annual/quarterly)."""
    p = path('fundamentals.csv')
    if not os.path.exists(p): return None
    return pd.read_csv(p, parse_dates=['date'])

def write(df, name):
    os.makedirs(CACHE, exist_ok=True)
    df.to_csv(path(name))
