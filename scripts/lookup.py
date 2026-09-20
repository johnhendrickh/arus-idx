#!/usr/bin/env python3
"""lookup.py — analisis on-demand 1 saham IDX APA PUN di luar universe (fitur #4).
Pakai: python scripts/lookup.py AMRT
Biaya: harga Sectors ~2 kredit (2 window 60 hari) + fundamental Yahoo (gratis).
       Broker/foreign TIDAK diambil (muhal 46 kredit) — kolom flow = n/a.
Output: skor momentum persentil vs universe + fundamental, jujur soal batasnya.
Idempotent: cache 30 hari -> 0 kredit utk lookup yang sama.
"""
import sys, os, datetime as dt
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import dotenv_values
import pandas as pd, numpy as np, yfinance as yf
from app import config as cfg, io_cache, score as sc
from scripts.fetch_sectors_prices import fetch_daily

ENV = dotenv_values(os.path.join(os.path.dirname(__file__), '..', '.env'))

def lookup(symbol, max_spend=3):
    symbol = symbol.upper().replace('.JK', '').strip()
    t = symbol + '.JK'
    # ---- 1. harga: cache dulu, baru Sectors (~1 kredit/window 90d, butuh ~120 bar utk mom120) ----
    spent = 0
    ohl = io_cache.read_ohlcv(t)
    today = dt.date.today()
    # window 90 hari mundur sampai ~185 bar (3 call max, sesuai budget ~4 kredit)
    for days_back in (90, 180, 270):
        if ohl is not None and len(ohl) >= 130: break
        if spent >= max_spend: break
        st = (today - dt.timedelta(days=days_back)).isoformat()
        en = (today - dt.timedelta(days=max(days_back - 90, 0))).isoformat()
        if ohl is not None and len(ohl) and ohl.index[0] <= pd.Timestamp(st):
            continue    # window sudah tercakup cache
        spent += fetch_daily(symbol, st, en)
        ohl = io_cache.read_ohlcv(t)
    if ohl is None or len(ohl) < 130:
        return None, spent, f'{symbol}: data harga tidak cukup ({0 if ohl is None else len(ohl)} bar) — ticker salah/delisted/listing baru'
    # ---- 2. fundamental: Yahoo gratis (ROE, laba) ----
    fund_rows = []
    name = symbol
    try:
        tk = yf.Ticker(t)
        name = tk.info.get('longName') or tk.info.get('shortName') or symbol
        ins, bs = tk.income_stmt, tk.balance_sheet
        ni = ins.loc['Net Income Common Stockholders']; rv = ins.loc['Total Revenue']
        eq = bs.loc['Stockholders Equity']
        for d in ni.index:
            fund_rows.append({'symbol': t, 'date': d, 'net_income': ni.get(d),
                              'total_revenue': rv.get(d), 'equity': eq.get(d)})
    except Exception:
        pass
    fund = pd.DataFrame(fund_rows) if fund_rows else None
    # ---- 3. skor persentil vs universe saat ini ----
    from app.main import load_cache
    uni_ohl, bm, fm, idx = load_cache()          # uni_ohl = dict {ticker: df}
    both = {**uni_ohl, t: ohl}
    p_m = sc.momentum_pillar(both)
    uni_mom = p_m[t].iloc[-1] if pd.notna(p_m[t].iloc[-1]) else None
    f_pct = None
    uni_fund = io_cache.read_fund()
    if fund is not None:
        try:
            allf = pd.concat([uni_fund, fund]) if uni_fund is not None else fund
            p_f = sc.fundamental_pillar(both, allf)
            f_pct = p_f[t].iloc[-1] if pd.notna(p_f[t].iloc[-1]) else None
        except Exception:
            pass
    spark = [round(float(x), 2) for x in ohl['Close'].tail(60).tolist()]
    return {
        'symbol': symbol,
        'bars': len(ohl),
        'momentum_pct': uni_mom,
        'fundamental_pct': f_pct,
        'score': round(0.55*uni_mom + 0.45*f_pct, 3) if (uni_mom is not None and f_pct is not None) else uni_mom,
        'spent': spent,
        'spark': spark,
        'name': name,
        'note': 'skor persentil vs 21 saham universe; broker/asing tidak diambil (biaya 46 kredit) — kolom flow n/a',
    }, spent, None

if __name__ == '__main__':
    if len(sys.argv) < 2: sys.exit('pakai: python scripts/lookup.py TICKER')
    res, spent, err = lookup(sys.argv[1])
    if err: sys.exit(err)
    print(f"{res['symbol']}: skor {res['score']} (momentum {res['momentum_pct']}, fund {res['fundamental_pct']}, {res['bars']} bar) — {res['spent']} kredit")
    print(res['note'])
