#!/usr/bin/env python3
"""fetch_one.py — tambah 1 saham ke universe on-demand (fitur #2).
Pakai: python scripts/fetch_one.py MEDC
Idempotent: bulan yang sudah di cache tidak di-fetch ulang (hemat kredit).
Biaya sekali per saham: broker-top ~19 bln (38k) + foreign 1 thn (8k) = ~46 kredit.
Batas harian ARUS_ONDEMAND_LIMIT (default 3) — anti kena spam."""
import sys, os, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import dotenv_values
import pandas as pd, yfinance as yf
from app import io_cache
from scripts.fetch_sectors import fetch_broker_top, fetch_foreign

KEY = dotenv_values(os.path.join(os.path.dirname(__file__), '..', '.env'))
LIMIT = int(KEY.get('ARUS_ONDEMAND_LIMIT', '3'))

def count_today():
    from scripts.fetch_sectors import LOG
    if not os.path.exists(LOG): return 0
    today = f'{dt.date.today():%Y-%m-%d}'
    return sum(1 for l in open(LOG) if 'add_universe' in l and l.startswith(today))

def main(symbol):
    symbol = symbol.upper().replace('.JK', '')
    from scripts.fetch_sectors import LOG
    if count_today() >= LIMIT:
        sys.exit(f'limit harian {LIMIT} saham tercapai — coba besok (proteksi kredit)')
    # 1. harga via Yahoo (gratis) — verifikasi ticker valid
    t = yf.Ticker(symbol + '.JK')
    df = t.history(period='5y')
    if df.empty or len(df) < 200:
        sys.exit(f'{symbol}.JK: data harga tidak cukup ({len(df)} bar) — ticker salah atau delisted')
    df.index = pd.to_datetime(df.index).tz_localize(None).normalize()   # yf .JK tz-aware -> tanggal polos
    io_cache.write(df, symbol + '.JK.csv')
    # 2. Sectors: broker-top sepanjang riwayat tersedia + foreign 1 thn
    spent = 0
    try:
        from scripts.fetch_sectors import month_ranges
        for st, en in month_ranges(2025, 2):
            if st[:7] == f'{dt.date.today():%Y-%m}': break   # bulan berjalan: API 400, skip
            p = io_cache.path(f'broker_{symbol}.csv')
            if os.path.exists(p) and st[:7] in set(pd.read_csv(p).month):
                continue
            try:
                spent += fetch_broker_top(symbol, st, en)
            except Exception:
                break   # riwayat lebih pendek dari 2025-02 — berhenti, simpan yang ada
    except Exception as e:
        print(f'  broker {symbol}: {e} (lanjut foreign)')
    try:
        spent += fetch_foreign(symbol, str(dt.date.today()-dt.timedelta(days=365)), str(dt.date.today()))
    except Exception as e:
        print(f'  foreign {symbol}: {e}')
    # 3. update universe di config
    cfgp = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'app', 'config.py')
    src = open(cfgp).read()
    if symbol not in src:
        src = src.replace('UNIVERSE = [', f"UNIVERSE = ['{symbol}', ", 1)
        open(cfgp, 'w').write(src)
    from scripts.fetch_sectors import LOG
    open(LOG, 'a').write(f"{dt.datetime.now():%Y-%m-%d %H:%M}  add_universe {symbol}  -{spent}\n")
    print(f'{symbol}: masuk universe. Harga 5y ok, Sectors spent {spent} kredit.')

if __name__ == '__main__':
    if len(sys.argv) < 2: sys.exit('pakai: python scripts/fetch_one.py TICKER')
    main(sys.argv[1])
