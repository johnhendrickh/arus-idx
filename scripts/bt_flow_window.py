import sys, os; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.main import load_cache
from app import score as sc, backtest as bt, io_cache
import pandas as pd, numpy as np
ohlcv, bm, fm, idx = load_cache()
pm = sc.momentum_pillar(ohlcv); pf = sc.fundamental_pillar(ohlcv, io_cache.read_fund())
pw = sc.flow_pillar(ohlcv, bm, fm)
reg = sc.regime(ohlcv, idx).reindex(pm.index).ffill()
REG = pd.DataFrame(np.repeat(reg.values[:,None], len(pm.columns), axis=1), index=pm.index, columns=pm.columns)
cut = pd.Series(pm.index >= '2025-03-01', index=pm.index)
CUT = pd.DataFrame(np.repeat(cut.values[:,None], len(pm.columns), axis=1), index=pm.index, columns=pm.columns)
ohlcv2 = {t: d[d.index >= '2025-02-01'] for t, d in ohlcv.items()}
print('== window 2025-03 -> kini, gate ON ==')
bt.run(ohlcv2, {'momentum': pm.where(CUT & REG), 'flow': pw.where(CUT & REG)})
print('== tanpa gate, window sama ==')
bt.run(ohlcv2, {'momentum': pm.where(CUT), 'flow': pw.where(CUT)})
print('== flow + momentum+fundamental combo, window sama, gate ON ==')
bt.run(ohlcv2, {'momentum': pm.where(CUT & REG), 'fundamental': pf.where(CUT & REG), 'flow': pw.where(CUT & REG)})
