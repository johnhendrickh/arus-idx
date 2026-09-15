"""backtest.py — bukti di balik angka. Wajib tampil bareng skor, tidak pernah sendiri.
Metrik per pilar & combo: IC spearman harian, top-vs-bot per rebalance 20d,
SELALU split sub-periode, SELALU cetak n. Referensi hasil: docs/BACKTEST.md."""
import pandas as pd, numpy as np
from scipy.stats import spearmanr
from app import config as cfg, io_cache, score as sc

def forward_returns(ohlcv):
    C = pd.DataFrame({t: d.Close for t, d in ohlcv.items()})
    O = pd.DataFrame({t: d.Open for t, d in ohlcv.items()})
    e = O.shift(-1)*(1+cfg.SLIP)
    return C.shift(-cfg.HOLD_D)/e - 1 - cfg.FEES, C.index

def run(ohlcv, pillars: dict, name=''):
    """pillars: {nama: DataFrame[date x symbol]}; combo otomatis = weighted mean."""
    f20, _ = forward_returns(ohlcv)
    floor = sc.liquidity_floor(ohlcv)
    out = {}
    combos = dict(pillars)
    if len(pillars) > 1:
        ws = {k: cfg.WEIGHTS.get(k, 1/len(pillars)) for k in pillars}
        s = sum(v*ws[k] for k, v in pillars.items())/sum(ws.values())
        combos['COMBO'] = s
    for nm, F in combos.items():
        F = F.where(floor)
        ics, spreads = [], []
        for i in range(130, len(F)-cfg.HOLD_D-1, cfg.HOLD_D):
            d = F.index[i]
            if d not in f20.index: continue
            f = F.loc[d].dropna()
            if len(f) < 8: continue
            e = f20.loc[d].reindex(f.index).dropna(); f = f.loc[e.index]
            if len(f) < 8: continue
            ic = spearmanr(f, e)[0]
            if np.isfinite(ic): ics.append(ic)
            spreads.append(e.loc[f.nlargest(4).index].mean() - e.loc[f.nsmallest(4).index].mean())
        ic, sp = np.array(ics), np.array(spreads)
        out[nm] = dict(ic=ic.mean(), t=ic.mean()/(ic.std()/np.sqrt(len(ic))+1e-12),
                       n_ic=len(ic), win=np.mean(np.array(sp)>0), n=len(sp), med=np.median(sp))
        print(f'{nm:12s} IC={out[nm]["ic"]:+.3f} t={out[nm]["t"]:5.1f} (n={len(ic)}) '
              f'| top>bot {out[nm]["win"]:.0%} (n={len(sp)}) med-spread {out[nm]["med"]:+.2%}')
    return out
