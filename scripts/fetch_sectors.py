#!/usr/bin/env python3
"""fetch_sectors.py — bulk download Sectors -> cache CSV. Idempotent + log kredit.
Budget: broker-top bulanan (kalibrasi) + foreign-flow 1 tahun. Jangan panggil per-user."""
import sys, os, json, time, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pandas as pd, requests
from app import config as cfg, io_cache

API = 'https://api.sectors.app/v2'
from dotenv import dotenv_values
KEY = os.getenv('SECTORS_API_KEY') or dotenv_values(os.path.join(os.path.dirname(__file__), '..', '.env')).get('SECTORS_API_KEY', '')
LOG = os.path.join(os.path.dirname(__file__), '..', 'data', 'fetch.log')
COSTS = {'broker_top': 2, 'foreign': 2}   # update bila docs bilang beda

def log(event, credits):
    line = f"{dt.datetime.now():%Y-%m-%d %H:%M}  {event}  -{credits}"
    open(LOG, 'a').write(line + '\n')
    return credits

def get(path, **params):
    r = requests.get(f'{API}{path}', params=params, headers={'Authorization': KEY}, timeout=30)
    if r.status_code == 429:
        time.sleep(20); return get(path, **params)
    r.raise_for_status()
    return r.json()

def fetch_broker_top(symbol, start, end):
    """Top buyers/sellers per rentang -> CSV broker_{SYM}.csv (append per bulan)."""
    p = io_cache.path(f'broker_{symbol}.csv')
    d = get(f'/broker-summary/{symbol}/top/', start=start, end=end)
    rows = []
    for side in ('top_buyers', 'top_sellers'):
        for b in d.get(side, []):
            rows.append({'month': start[:7], 'side': side, 'broker_code': b['broker_code'],
                         'net_idr': b['net_idr'], 'buy_idr': b.get('buy_idr'),
                         'sell_idr': b.get('sell_idr'), 'foreign_net_idr': b.get('foreign_net_idr')})
    df = pd.DataFrame(rows)
    old = pd.read_csv(p) if os.path.exists(p) else pd.DataFrame()
    both = pd.concat([old[old.month != start[:7]], df]) if len(old) else df
    both = both.reset_index(drop=True).loc[:, ~both.columns.str.startswith('Unnamed')]
    io_cache.write(both, f'broker_{symbol}.csv')
    return COSTS['broker_top']

def fetch_foreign(symbol, start, end):
    """Net foreign harian -> CSV foreign_{SYM}.csv. API cap 90 hari/call -> loop per segmen."""
    p = io_cache.path(f'foreign_{symbol}.csv')
    old = pd.read_csv(p, index_col=0, parse_dates=True) if os.path.exists(p) else None
    segs, spent = [], 0
    d0, d1 = [dt.date.fromisoformat(x) for x in (start, end)]
    while d0 <= d1:
        d2 = min(d0 + dt.timedelta(days=85), d1)
        if old is None or len(old) == 0 or not any((pd.Index(old.index.date) >= d0) & (pd.Index(old.index.date) <= d2)):
            dd = get(f'/foreign-flow/{symbol}/', start=str(d0), end=str(d2)).get('data', [])
            segs.append(pd.DataFrame(dd)); spent += COSTS['foreign']
        d0 = d2 + dt.timedelta(days=1)
    df = pd.concat([s for s in segs if len(s)]) if segs else pd.DataFrame()
    if len(df):
        df['date'] = pd.to_datetime(df['date']); df = df.set_index('date')
    if old is not None and len(df):
        df = pd.concat([old[~old.index.isin(df.index)], df]).sort_index()
    if old is not None and len(old) and not len(df): df = old
    io_cache.write(df if len(df) else (df if old is None else old), f'foreign_{symbol}.csv')
    return spent

def month_ranges(from_y, from_m, until=dt.date.today()):
    y, m = from_y, from_m
    while (y, m) <= (until.year, until.month):
        yield f'{y:04d}-{m:02d}-01', f'{y:04d}-{m:02d}-{28 if m!=2 else 28}'
        m += 1
        if m > 12: y, m = y+1, 1

def main(only=None):
    if not KEY: sys.exit('set SECTORS_API_KEY di .env')
    spent = 0
    syms = [s for s in cfg.UNIVERSE if only is None or s in only]
    for s in syms:
        # kalibrasi broker-top: Feb 2025 -> kini (window data tersedia)
        for st, en in month_ranges(2025, 2):
            p = io_cache.path(f'broker_{s}.csv')
            if os.path.exists(p):
                have = pd.read_csv(p)
                if st[:7] in set(have.month): continue
            try:
                spent += log(f'broker_top {s} {st[:7]}', fetch_broker_top(s, st, en))
            except Exception as e:
                print(f'{s} {st[:7]}: {e}'); break
        # foreign: 1 tahun
        try:
            spent += log(f'foreign {s}', fetch_foreign(s, str(dt.date.today()-dt.timedelta(days=365)), str(dt.date.today())))
        except Exception as e:
            print(f'{s} foreign: {e}')
        print(f'{s} done, spent so far {spent}')
    print(f'TOTAL spent: {spent}')

if __name__ == '__main__':
    main(only=sys.argv[1:] or None)
