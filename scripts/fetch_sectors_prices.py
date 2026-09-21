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
    """OHLCV utk 1 saham -> append cache. Sectors-first, fallback Yahoo kalau
    Sectors stale >2 hari (umum di hari bursa baru buka setelah weekend/holiday
    — Sectors delay publish ~1-6 jam per endpoint). Yahoo gratis, real-time."""
    sym = f'{symbol}.JK'
    spent = 0
    rows = get(f'/daily/{sym}/', start=start, end=end)
    if rows:
        df = pd.DataFrame(rows)
        df['Date'] = pd.to_datetime(df['date'])
        df = df.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low',
                                'close': 'Close', 'volume': 'Volume'})
        df = df.set_index('Date')[['Open', 'High', 'Low', 'Close', 'Volume']].sort_index()
        last_sectors = df.index[-1].date()
        last_yahoo = _yahoo_last(sym)
        if last_yahoo and last_yahoo > last_sectors:
            print(f'{symbol}: Sectors stale ({last_sectors}), pakai Yahoo ({last_yahoo})')
            ydf = _yahoo_ohlcv(sym, start, end)
            if ydf is not None and not ydf.empty:
                df = pd.concat([df[~df.index.isin(ydf.index)], ydf]).sort_index()
        spent = 1
    else:
        print(f'{symbol}: Sectors kosong, fallback Yahoo')
        df = _yahoo_ohlcv(sym, start, end)
        if df is None or df.empty:
            print(f'{symbol}: Sectors + Yahoo dua-duanya gagal')
            return 0
    p = io_cache.path(f'{sym}.csv')
    if os.path.exists(p):
        old = io_cache.read_ohlcv(sym)
        if old is not None:
            df = pd.concat([old[~old.index.isin(df.index)], df]).sort_index()
            df = df[~df.index.duplicated(keep='last')]
    io_cache.write(df, f'{sym}.csv')
    return spent

def _yahoo_ohlcv(sym, start, end):
    """Yahoo Finance OHLCV + Volume utk fallback IHSG/saham."""
    import yfinance as yf
    t = yf.Ticker(sym)
    df = t.history(start=start, end=str(dt.date.today() + dt.timedelta(days=1)))
    if df.empty: return None
    df.index = pd.to_datetime(df.index).tz_localize(None).normalize()
    return df[['Open', 'High', 'Low', 'Close', 'Volume']]

def _yahoo_last(sym):
    """1 bar terakhir dari Yahoo buat cek staleness Sectors."""
    import yfinance as yf
    t = yf.Ticker(sym)
    df = t.history(period='5d')
    if df.empty: return None
    return pd.to_datetime(df.index[-1]).date()

def fetch_ihsg(days=90):
    """Sectors /index-daily/ihsg/ max 62 bar. Fallback ke Yahoo Finance kalau
    Sectors stale >1 hari (umum di hari bursa baru buka setelah weekend/holiday
    — Sectors delay publish ~1-6 jam). Yahoo real-time."""
    end = dt.date.today()
    start = str(end - dt.timedelta(days=days))
    rows = get('/index-daily/ihsg/', start=start, end=str(end))
    if rows:
        df = pd.DataFrame(rows)
        df['Date'] = pd.to_datetime(df['date'])
        df = df.set_index('Date')[['price']].rename(columns={'price': 'Close'})
        last_sectors = df.index[-1].date()
        last_yahoo = _yahoo_ihsg_last()
        if last_yahoo and last_yahoo > last_sectors:
            print(f'IHSG Sectors stale (last {last_sectors}), pakai Yahoo ({last_yahoo})')
            df = _yahoo_ihsg(start, end).combine_first(df)
    else:
        print('Sectors IHSG kosong, fallback Yahoo')
        df = _yahoo_ihsg(start, end)
    if df is None or df.empty:
        print('IHSG: Sectors + Yahoo dua-duanya gagal')
        return 0
    io_cache.write(df, '_JKSE.csv')
    return 1

def _yahoo_ihsg(start, end):
    import yfinance as yf
    t = yf.Ticker('^JKSE')
    df = t.history(start=start, end=str(dt.date.today() + dt.timedelta(days=1)))
    if df.empty: return None
    df.index = pd.to_datetime(df.index).tz_localize(None).normalize()
    return df[['Close']]

def _yahoo_ihsg_last():
    """Ambil 1 bar terakhir IHSG dari Yahoo buat cek staleness."""
    import yfinance as yf
    t = yf.Ticker('^JKSE')
    df = t.history(period='5d')
    if df.empty: return None
    return pd.to_datetime(df.index[-1]).date()

if __name__ == '__main__':
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    end = dt.date.today()
    start = str(end - dt.timedelta(days=days))
    spent = 0
    for s in cfg.UNIVERSE:
        p = io_cache.path(f'{s}.JK.csv')
        # skip jika cache sudah punya data ≤1 hari lalu (weekend skip aman,
        # karena Mon-Sab bursa cuma 5 hari, Senin pagi setelah weekend: cache
        # lama = Jumat = 3 hari lalu, AMAN refresh)
        if os.path.exists(p):
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
