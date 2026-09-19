#!/usr/bin/env python3
"""fetch_sectors_daily.py — refresh ringan tiap hari (bukan bulk history).
Broker-top: hanya bulan berjalan (sudah tercache = skip, hemat kredit).
Foreign: hanya 7 hari terakhir (cap API 90 hari aman).
Output: ringkasan kredit terpakai. Idempotent."""
import sys, os, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.fetch_sectors import fetch_broker_top, fetch_foreign, LOG
from app import config as cfg, io_cache
import pandas as pd

today = dt.date.today()
mon_start = f'{today:%Y-%m}-01'
mon_end = f'{today:%Y-%m}-{min(today.day, 28):02d}'   # end tak boleh melewati hari ini
wk_start = str(today - dt.timedelta(days=7))

spent = 0
for s in cfg.UNIVERSE:
    # broker bulan berjalan
    p = io_cache.path(f'broker_{s}.csv')
    have = False
    if os.path.exists(p):
        have = f'{today:%Y-%m}' in set(pd.read_csv(p).month)
    if not have:
        try:
            spent += fetch_broker_top(s, mon_start, mon_end)
        except Exception as e:
            print(f'broker {s}: {e}')
    # foreign 7 hari terakhir (fetch_foreign dedup per tanggal)
    try:
        spent += fetch_foreign(s, wk_start, str(today))
    except Exception as e:
        print(f'foreign {s}: {e}')
print(f'daily refresh: {spent} kredit terpakai')
