#!/usr/bin/env python3
"""fetch_corp_actions.py — ambil aksi korporat (right issue, dividen, split) seluruh IDX.

1 GET /v2/corporate-actions/ = window 2 bulan semua saham. Murah, cache harian.
Output: data/cache/corp_actions.json — dipakai server.py kolom "Aksi Korporat".
"""
import sys, os, json, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import requests
from dotenv import dotenv_values

API = 'https://api.sectors.app/v2'
KEY = os.getenv('SECTORS_API_KEY') or dotenv_values(os.path.join(os.path.dirname(__file__), '..', '.env')).get('SECTORS_API_KEY', '')
OUT = os.path.join(os.path.dirname(__file__), '..', 'data', 'cache', 'corp_actions.json')
LOG = os.path.join(os.path.dirname(__file__), '..', 'data', 'fetch.log')

def log(event, credits):
    line = f"{dt.datetime.now():%Y-%m-%d %H:%M}  {event}  -{credits}"
    open(LOG, 'a').write(line + '\n')

def main():
    if not KEY: sys.exit('set SECTORS_API_KEY di .env')
    r = requests.get(f'{API}/corporate-actions/', headers={'Authorization': KEY}, timeout=30)
    r.raise_for_status()
    d = r.json()
    today = dt.date.today().isoformat()
    # simpan: hanya field yang dipakai, strip tanggal lama (window API ±2 bulan sudah cukup)
    out = {'fetched': today, 'right_issue': d.get('right_issue', []),
           'upcoming_dividend': d.get('upcoming_dividend', []),
           'stock_split': d.get('stock_split', [])}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w') as f:
        json.dump(out, f)
    log(f'corporate-actions window {d.get("start")}..{d.get("end")}', 1)
    n = {k: len(v) for k, v in out.items() if isinstance(v, list)}
    print(f'OK — cached {OUT}: {n}')

if __name__ == '__main__':
    main()
