"""bt_proxy.py — backtest gate pakai IHSG proxy (equal-weight avg semua saham).
Sectors /index-daily/ endpoint dibatasi 62 bar apapun window-nya; proxy = 1520 bar,
korrealsi 0.933 dengan IHSG asli di 62 bar overlap.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pandas as pd, numpy as np
from app.main import load_cache
from app import score as sc, backtest as bt, io_cache, config as cfg

ohlcv, bm, fm, _idx_short = load_cache()

# IHSG proxy 1520 bar (gantikan 62 bar dari Sectors)
proxy = pd.read_csv(io_cache.path('_JKSE_proxy.csv'), index_col=0, parse_dates=True).Close
proxy.index = pd.to_datetime(proxy.index, utc=True).tz_localize(None)

# Pillar standar (regime pakai proxy panjang, reg_tight pakai IHSG asli 62 bar buat last 3 bulan)
pm = sc.momentum_pillar(ohlcv)
pf = sc.fundamental_pillar(ohlcv, io_cache.read_fund())
pw = sc.flow_pillar(ohlcv, bm, fm)

reg_long = sc.regime(ohlcv, proxy).reindex(pm.index).ffill()
REG = pd.DataFrame(np.repeat(reg_long.values[:,None], len(pm.columns), axis=1),
                   index=pm.index, columns=pm.columns)

cut = pd.Series(pm.index >= '2025-03-01', index=pm.index)
CUT = pd.DataFrame(np.repeat(cut.values[:,None], len(pm.columns), axis=1),
                   index=pm.index, columns=pm.columns)

# Slice ohlcv ke 2025+ buat forward_returns (window test)
ohlcv2 = {t: d[d.index >= '2025-02-01'] for t, d in ohlcv.items()}

print('== backtest 2025-03 -> kini, gate IHSG-proxy ON ==')
bt.run(ohlcv2, {'momentum': pm.where(CUT & REG),
                'flow': pw.where(CUT & REG) if pw is not None else pm.where(CUT & REG)*0})
print('== tanpa gate (gate = always True) ==')
bt.run(ohlcv2, {'momentum': pm.where(CUT), 'flow': pw.where(CUT) if pw is not None else pm.where(CUT)*0})
print('== combo momentum+fundamental (gate ON) ==')
bt.run(ohlcv2, {'momentum': pm.where(CUT & REG),
                'fundamental': pf.where(CUT & REG) if pf is not None else pm.where(CUT & REG)*0})
print('== full combo (gate ON) ==')
if pw is not None and pf is not None:
    bt.run(ohlcv2, {'momentum': pm.where(CUT & REG),
                    'fundamental': pf.where(CUT & REG),
                    'flow': pw.where(CUT & REG)})

# Headline: berapa hari regime UP di window 2025+?
print()
print('regime UP days in 2025+:', int(reg_long.loc['2025-03-01':].sum()), '/', int((pm.index >= '2025-03-01').sum()),
      f'({reg_long.loc["2025-03-01":].mean():.0%})')
