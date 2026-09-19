#!/usr/bin/env python3
"""bt_flow_v2.py — test 3 kandidat logic flow baru vs baseline (nol kredit, cache only).
K1 KONFIRMASI: momentum top-5 dibeli vs dilepas asing (5d) — beda nasib?
K2 PERSISTENSI: streak hari net-buy berturut (akumulasi konsisten)
K3 DIVERGENSI: harga naik + asing jual = warning; harga naik + asing beli = aman
Metode sama dgn bt_flow_window: IC per-rebalance, top5-vs-bot5, fee+slip sudah di entry T+1.
"""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.main import load_cache
from app import score as sc, backtest as bt, io_cache
import pandas as pd, numpy as np

ohlcv, bm, fm, idx = load_cache()
pm = sc.momentum_pillar(ohlcv)
pf = sc.fundamental_pillar(ohlcv, io_cache.read_fund())
reg = sc.regime(ohlcv, idx).reindex(pm.index).ffill()
REG = pd.DataFrame(np.repeat(reg.values[:, None], len(pm.columns), axis=1),
                   index=pm.index, columns=pm.columns)
C = pd.DataFrame({t: d.Close for t, d in ohlcv.items()})

# ---- siapkan matrix net foreign harian
fparts = {}
for t in C.columns:
    sym = t.replace('.JK', '')
    if sym in fm and fm[sym] is not None and len(fm[sym]):
        f = fm[sym]['net_foreign_inflow'].copy()
        f.index = pd.to_datetime(f.index)
        fparts[t] = f
FNET = pd.DataFrame(fparts).reindex(C.index).ffill()

# ---- K1: konfirmasi asing pada momentum top-5
top = pm.rank(axis=1, pct=True) >= 0.75          # momentum top quartile
f5 = FNET.rolling(5).sum()
fbuy = (f5 > 0).where(top)                        # top momentum & dibeli asing
fsell = (f5 < 0).where(top)                       # top momentum & dilepas asing
ret20 = C.pct_change(20).shift(-20)               # forward 20 hari
n1b, n1s = fbuy.sum().sum(), fsell.sum().sum()
k1 = (ret20.where(fbuy).stack().median() - ret20.where(fsell).stack().median())

# ---- K2: persistensi — streak net-buy hari berturut (run-length per kolom)
pos = (FNET > 0)
streak = pd.DataFrame(0.0, index=FNET.index, columns=FNET.columns)
for c in FNET.columns:
    p = pos[c].fillna(False).values
    run = 0
    out = np.zeros(len(p))
    for i, v in enumerate(p):
        run = run + 1 if v else 0
        out[i] = run
    streak[c] = out
K2 = streak.shift(1).clip(0, 10) / 10              # sinyal dari streak kemarin, cap 10 hari
K2 = K2.where(FNET.notna())

# ---- K3: divergensi — rsi-ish harga 20d vs arah asing 5d
mom20 = C.pct_change(20)
div_bad = (mom20 > 0.05) & (f5 < 0)                # harga naik, asing keluar
div_good = (mom20 > 0.05) & (f5 > 0)
k3 = ret20.where(div_good).stack().median() - ret20.where(div_bad).stack().median()

# ---- IC kandidat (metode backtest.run: spearman vs fwd 20d, window penuh + gate ON)
def ic_of(pillar, gate=True):
    p = pillar.where(REG) if gate else pillar
    valid = p.dropna(how='all')
    ics = []
    for d, row in valid.iterrows():
        r = ret20.loc[d].dropna()
        s = row.dropna()
        common = r.index.intersection(s.index)
        if len(common) >= 8:
            ics.append(s[common].rank().corr(r[common].rank()))
    ics = pd.Series(ics).dropna()
    return (ics.mean(), len(ics)) if len(ics) else (np.nan, 0)

print('== baseline (flow lama) ==')
pw = sc.flow_pillar(ohlcv, bm, fm)
print('  IC %.3f (n=%d)' % ic_of(pw))
print('== K1 konfirmasi: top-momentum dibeli vs dilepas asing ==')
print('  n buy=%d sell=%d | spread median fwd20: %+.2f%%' % (n1b, n1s, k1 * 100))
print('== K2 persistensi: streak net-buy (IC) ==')
print('  IC %.3f (n=%d)' % ic_of(K2))
print('  IC (gate ON) %.3f (n=%d)' % ic_of(K2, gate=True))
print('== K3 divergensi: harga naik + asing jual vs beli ==')
print('  spread median fwd20: %+.2f%%' % (k3 * 100))

# ---- combo: momentum saja vs momentum+K2
print('== combo momentum+K2 (gate ON) vs momentum saja ==')
bt.run(ohlcv, {'momentum': pm.where(REG)})
bt.run(ohlcv, {'mom+streak': (0.8 * pm.rank(axis=1, pct=True) + 0.2 * K2).where(REG)})
bt.run(ohlcv, {'mom+streak+fund': (0.5 * pm.rank(axis=1, pct=True) + 0.3 * pf.rank(axis=1, pct=True).fillna(0.5) + 0.2 * K2).where(REG)})
