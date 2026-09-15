#!/usr/bin/env python3
"""fetch_yahoo.py — bulk download OHLCV + fundamentals -> cache CSV. Jalankan 1x/hari."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import yfinance as yf, pandas as pd, warnings
warnings.filterwarnings('ignore')
from app import config as cfg, io_cache

def main():
    for s in cfg.UNIVERSE:
        t = s + '.JK'
        df = yf.download(t, start='2020-06-01', auto_adjust=True, progress=False)
        if len(df) > 200:
            df.columns = [c[0] for c in df.columns]
            io_cache.write(df[['Open','High','Low','Close','Volume']], f'{t}.csv')
            print(t, len(df))
    df = yf.download('^JKSE', start='2020-06-01', auto_adjust=True, progress=False)
    df.columns = [c[0] for c in df.columns]
    io_cache.write(df[['Open','High','Low','Close','Volume']], '_JKSE.csv')
    # fundamentals -> satu CSV panjang
    rows = []
    for s in cfg.UNIVERSE:
        t = s + '.JK'
        try:
            tk = yf.Ticker(t)
            ins, bs = tk.income_stmt, tk.balance_sheet
            ni = ins.loc['Net Income Common Stockholders']; rv = ins.loc['Total Revenue']
            eq = bs.loc['Stockholders Equity']
            for d in ni.index:
                rows.append({'symbol': t, 'date': d, 'net_income': ni.get(d),
                             'total_revenue': rv.get(d), 'equity': eq.get(d)})
        except Exception as e:
            print(t, 'fund fail:', e)
    io_cache.write(pd.DataFrame(rows), 'fundamentals.csv')
    print('fundamentals rows:', len(rows))

if __name__ == '__main__':
    main()
