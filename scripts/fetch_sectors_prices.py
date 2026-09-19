#!/usr/bin/env python3
"""fetch_sectors_prices.py — harga harian dari Sectors API (Sectors-first!).
/daily/{symbol}.JK/  : OHLCV + market cap, window ≤90 hari/call
/index-daily/ihsg/   : IHSG utk regime gate
Menulis ke format cache yang sama dengan Yahoo (kolom identik) supaya
score.py tidak perlu diubah. Idempotent: tanggal duplikat di-dedup.
Backtest 5-tahun tetap dari snapshot Yahoo statis (data/cache/*.csv) —
runtime 100% Sectors."""
import sys, os, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.fetch_sectors import get, LOG
from app import config as cfg, io_cache
import pandas as pd

def fetch_daily(symbol, start, end):
    """OHLCV 90-hari utk 1 saham -> append cache. Return kredit terpakai."""
    sym = f'{symbol}.JK'
    rows = get(f'/daily/{sym}/', start=start, end=end)
    if not rows: return 0
    df = pd.DataFrame(rows)
    df['Date'] = pd.to_datetime(df['date'])
    df = df.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low',
                            'close': 'Close', 'volume': 'Volume'})
    df = df.set_index('Date')[['Open', 'High', 'Low', 'Close', 'Volume']].sort_index()
    p = io_cache.path(f'{sym}.csv')
    if os.path.exists(p):
        old = io_cache.read_ohlcv(sym)
        if old is not None:
            df = pd.concat([old[~old.index.isin(df.index)], df]).sort_index()
            df = df[~df.index.duplicated(keep='last')]
    io_cache.write(df, f'{sym}.csv')
    return 1   # ~1 kredit per call per docs billing

def fetch_ihsg(days=90):
    end = dt.date.today()
    start = str(end - dt.timedelta(days=days))
    rows = get('/index-daily/ihsg/', start=start, end=str(end))
    if not rows: return 0
    df = pd.DataFrame(rows)
    df['Date'] = pd.to_datetime(df['date'])
    df = df.set_index('Date')[['price']].rename(columns={'price': 'Close'})
    io_cache.write(df, '^JKSE.csv')
    return 1

if __name__ == '__main__':
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    end = dt.date.today()
    start = str(end - dt.timedelta(days=days))
    spent = 0
    for s in cfg.UNIVERSE:
        p = io_cache.path(f'{s}.JK.csv')
        # skip jika cache sudah punya data ≤3 hari lalu
        if os.path.exists(p):
            old = io_cache.read_ohlcv(f'{s}.JK')
            if old is not None and (pd.Timestamp(end) - old.index.max()).days <= 3:
                print(f'{s}: fresh, skip')
                continue
        try:
            spent += fetch_daily(s, start, str(end))
            print(f'{s}: ok')
        except Exception as e:
            print(f'{s}: ERR {str(e)[:80]}')
    try:
        spent += fetch_ihsg()
        print('IHSG: ok')
    except Exception as e:
        print(f'IHSG: ERR {str(e)[:80]}')
    open(LOG, 'a').write(f'{dt.datetime.now():%Y-%m-%d %H:%M}  sectors_prices daily -{spent}\n')
    print(f'total: {spent} kredit')
