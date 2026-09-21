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
    """OHLCV utk 1 saham -> append cache. Sectors-first, 100% Sectors API.
    Kalau Sectors stale, cache tidak di-update (cron skip alert via guard-2).
    """
    sym = f'{symbol}.JK'
    rows = get(f'/daily/{sym}/', start=start, end=end)
    if not rows:
        print(f'{symbol}: Sectors kosong')
        return 0
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
    return 1   # 1 kredit per call

def fetch_ihsg(days=90):
    """Sectors /index-daily/ihsg/ max 62 bar. 100% Sectors API."""
    end = dt.date.today()
    start = str(end - dt.timedelta(days=days))
    rows = get('/index-daily/ihsg/', start=start, end=str(end))
    if not rows:
        print('IHSG: Sectors kosong')
        return 0
    df = pd.DataFrame(rows)
    df['Date'] = pd.to_datetime(df['date'])
    df = df.set_index('Date')[['price']].rename(columns={'price': 'Close'})
    io_cache.write(df, '_JKSE.csv')
    return 1


def _ihsg_last_bar():
    """Return date of last IHSG bar in cache, or None. Dipakai cron buat cek
    apakah bursa buka / Sectors sudah publish bar hari ini."""
    p = io_cache.path('_JKSE.csv')
    if not os.path.exists(p): return None
    try:
        df = pd.read_csv(p, index_col=0, parse_dates=True)
        return df.index[-1].date()
    except Exception:
        return None

if __name__ == '__main__':
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    end = dt.date.today()
    start = str(end - dt.timedelta(days=days))
    spent = 0
    # Bursa-buka detector: kalau IHSG cache ≠ hari ini, bursa mungkin sudah
    # buka tapi Sectors belum publish → force fetch saham walaupun "fresh"
    # (Senin pagi setelah weekend: cache Jumat = 3 hari lalu, Sectors perlu
    # waktu publish Senin). Hemat kredit weekday normal (Sen-Jum cache 1 hari).
    ihsg_today = _ihsg_last_bar() == end
    for s in cfg.UNIVERSE:
        p = io_cache.path(f'{s}.JK.csv')
        if os.path.exists(p) and ihsg_today:
            old = io_cache.read_ohlcv(f'{s}.JK')
            if old is not None and (pd.Timestamp(end) - old.index.max()).days <= 1:
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
