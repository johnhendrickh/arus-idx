#!/usr/bin/env python3
"""bt_corp_action_test.py — backtest pengaruh corporate action ke harga saham IDX.

DATA SOURCE: yfinance (saham IDX pakai .JK suffix)
- Yahoo Finance mendukung saham Indonesia (.JK)
- yfinance: tidak ada API key, rate limit fair
- Output: statistical analysis dari 5 RI/dividen/split di window 27 Agt–26 Okt 2026

METRIK (per corporate action event):
- H-7 sampai H+5 = 13 hari window
- Close H-7 vs H+5: return bersih
- Volume ratio: post ex / pre ex
- Price adjustment: gap detection

Tidak masuk ARUS score, hanya exploratory backtest.
"""
import yfinance as yf
import pandas as pd
import numpy as np
import datetime as dt
import json, sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import io_cache

def get_window(symbol: str, ex_date: dt.date, days_pre: int = 7, days_post: int = 5) -> pd.DataFrame:
    """Fetch price window around ex_date from yfinance.
    `symbol` is full IDX ticker including .JK suffix (e.g. 'BUVA.JK')."""
    start = ex_date - dt.timedelta(days=days_pre + 1)
    end = ex_date + dt.timedelta(days=days_post + 2)
    ticker = yf.Ticker(symbol)
    df = ticker.history(start=start, end=end, auto_adjust=False)
    if df.empty: return df
    df.index = df.index.date
    df = df[df.index >= ex_date - dt.timedelta(days=days_pre)]
    df = df[df.index <= ex_date + dt.timedelta(days=days_post)]
    return df

def analyze_event(symbol: str, ex_date: dt.date, ca_type: str, details: dict) -> dict:
    """Compute returns + volume change around a single CA event.
    `symbol` is e.g. 'BUVA.JK'."""
    df = get_window(symbol, ex_date)
    if df.empty or len(df) < 3:
        return {'symbol': symbol, 'ex_date': str(ex_date), 'type': ca_type,
                'note': 'yfinance data incomplete'}

    pre_close = df['Close'].iloc[0]
    post_close = df['Close'].iloc[-1]
    ret = (post_close - pre_close) / pre_close

    pre_vol = df['Volume'].iloc[:len(df)//2].mean()
    post_vol = df['Volume'].iloc[len(df)//2:].mean()
    vol_ratio = post_vol / pre_vol if pre_vol > 0 else np.nan

    gap = (df['Open'].iloc[0] - pre_close) / pre_close if len(df) > 1 else 0

    return {
        'symbol': symbol.replace('.JK', ''),
        'ex_date': str(ex_date),
        'type': ca_type,
        'details': details,
        'pre_close': round(float(pre_close), 2),
        'post_close': round(float(post_close), 2),
        'return_pct': round(ret * 100, 2),
        'vol_ratio': round(float(vol_ratio), 2) if not np.isnan(vol_ratio) else None,
        'gap_open_pct': round(float(gap) * 100, 2),
        'n_bars': len(df)
    }

def main():
    ca = json.load(open(io_cache.path('corp_actions.json')))
    today = dt.date.today()

    events = []
    for x in ca.get('right_issue', []):
        sym = x['symbol'] if x['symbol'].endswith('.JK') else x['symbol'] + '.JK'
        events.append({
            'symbol': sym,
            'ex_date': x['ex_date'],
            'type': 'RI',
            'details': f"price {x['price']}, ratio {x['old_ratio']}:{x['new_ratio']}"
        })
    for x in ca.get('upcoming_dividend', []):
        sym = x['symbol'] if x['symbol'].endswith('.JK') else x['symbol'] + '.JK'
        events.append({
            'symbol': sym,
            'ex_date': x['ex_date'],
            'type': 'DIV',
            'details': f"{x['dividend_amount']} IDR"
        })
    for x in ca.get('stock_split', []):
        sym = x['symbol'] if x['symbol'].endswith('.JK') else x['symbol'] + '.JK'
        events.append({
            'symbol': sym,
            'ex_date': x['date'],
            'type': 'SPL',
            'details': x['ratio']
        })

    print(f"=== Analyzing {len(events)} corporate actions from yfinance ===\n")
    results = []
    for e in events:
        ex = dt.date.fromisoformat(e['ex_date'])
        r = analyze_event(e['symbol'], ex, e['type'], e['details'])
        results.append(r)
        print(f"{r['symbol']:>6} {r['type']:>3} {r['ex_date']}  "
              f"return={r.get('return_pct', 'n/a')}%  "
              f"vol_ratio={r.get('vol_ratio', 'n/a')}  "
              f"gap={r.get('gap_open_pct', 'n/a')}%  "
              f"bars={r.get('n_bars', 0)}")

    by_type = {}
    for r in results:
        if 'return_pct' in r and r.get('return_pct') is not None:
            by_type.setdefault(r['type'], []).append(r['return_pct'])

    print(f"\n=== Aggregate by type ===")
    for t, rets in by_type.items():
        avg = np.mean(rets)
        print(f"{t}: avg={avg:.2f}%  n={len(rets)}  rets={rets}")

if __name__ == '__main__':
    main()
