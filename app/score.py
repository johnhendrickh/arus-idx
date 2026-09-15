"""score.py — mesin skor 3 pilar. Pure function, deterministic, tanpa API call.

Setiap pilar -> DataFrame [date x symbol] rank 0..1 (NaN bila tidak berlaku).
composite = weighted mean pilar yang tersedia (renormalisasi bobot).
Gate IHSG & floor likuiditas = masker (bukan pilar): skor tetap keluar, tapi
status = 'WAIT (regime)' / 'SKIP (illiquid)'.
"""
import pandas as pd, numpy as np
from app import config as cfg

def momentum_pillar(ohlcv):
    C = pd.DataFrame({t: d.Close for t, d in ohlcv.items()})
    V = pd.DataFrame({t: d.Volume for t, d in ohlcv.items()})
    consensus = sum((C.pct_change(h) > 0).astype(float) for h in cfg.MOM_HORIZONS)
    vol20 = C.pct_change().rolling(cfg.VOL_LOOKBACK).std()
    radj = C.pct_change(cfg.MOM_LOOKBACK) / vol20
    return 0.5*consensus.rank(axis=1, pct=True) + 0.5*radj.rank(axis=1, pct=True)

def fundamental_pillar(ohlcv, fund):
    """ROE & E/P time-series (ffill laporan kuartalan). Penalti growth-trap."""
    C = pd.DataFrame({t: d.Close for t, d in ohlcv.items()})
    ni = fund.pivot_table(index='date', columns='symbol', values='net_income').reindex(
         fund.pivot_table(index='date', columns='symbol', values='net_income').index.union(C.index)).ffill().reindex(C.index)
    eq = fund.pivot_table(index='date', columns='symbol', values='equity').reindex(
         fund.pivot_table(index='date', columns='symbol', values='equity').index.union(C.index)).ffill().reindex(C.index)
    roe = (ni/eq).rank(axis=1, pct=True)
    ep = (ni/C).rank(axis=1, pct=True)
    qual = 0.5*roe + 0.5*ep
    if cfg.GROWTH_PENALTY:
        rev = fund.pivot_table(index='date', columns='symbol', values='total_revenue').reindex(
              fund.pivot_table(index='date', columns='symbol', values='total_revenue').index.union(C.index)).ffill().reindex(C.index)
        g = (rev/rev.shift(252) - 1).rank(axis=1, pct=True)
        qual = qual - 0.25*(g > 0.8)   # top-decile revenue growth: penalti ringan
    return qual.clip(0, 1)

def flow_pillar(ohlcv, broker_map, foreign):
    """Kosong sampai key Sectors turun. Kontrak:
    broker_map[symbol] -> DataFrame[date, broker_code, net_idr, buy_idr, sell_idr]
    foreign           -> DataFrame[date x symbol] net foreign IDR
    Faktor: z-score net-buy top-2 broker / avg 60d, konsistensi hari-berturut,
    konsentrasi pembeli, net foreign 5d z-score. Lihat backtest TODO di backtest.py."""
    return None  # TODO flow_pillar — implementasi setelah data cache broker ada

def regime(ohlcv, index_close):
    ema = index_close.ewm(span=cfg.REGIME_EMA_SPAN, adjust=False).mean()
    return (index_close > ema)

def liquidity_floor(ohlcv):
    C = pd.DataFrame({t: d.Close for t, d in ohlcv.items()})
    V = pd.DataFrame({t: d.Volume for t, d in ohlcv.items()})
    dv = (C*V).rolling(20).mean()
    return dv.rank(axis=1, pct=True) > cfg.LIQ_FLOOR_PCT

def composite(ohlcv, fund, broker_map=None, foreign=None, index_close=None):
    p_m = momentum_pillar(ohlcv)
    p_f = fundamental_pillar(ohlcv, fund) if fund is not None else None
    p_w = flow_pillar(ohlcv, broker_map, foreign) if broker_map else None
    parts, ws = [], []
    for p, k in [(p_m,'momentum'), (p_f,'fundamental'), (p_w,'flow')]:
        if p is not None:
            parts.append(p*cfg.WEIGHTS[k]); ws.append(cfg.WEIGHTS[k])
    score = sum(parts)/sum(ws)
    if index_close is not None:
        score = score.where(regime(ohlcv, index_close), score)  # gate -> status, bukan nol
    return score
