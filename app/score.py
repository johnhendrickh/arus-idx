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

def flow_pillar(ohlcv, broker_map, foreign_map=None):
    """Pilar flow dari cache Sectors. Bulanan (kalibrasi) + foreign harian (live).
    Faktor: (a) z-score net top-buyer bulanan vs history saham sendiri,
            (b) share net-buyer terhadap total dua sisi,
            (c) z-score net foreign 5d (kalau data hariannya cukup)."""
    import numpy as np
    if not broker_map: return None
    C = pd.DataFrame({t: d.Close for t, d in ohlcv.items()})
    parts = []
    for t in C.columns:
        sym = t.replace('.JK', '')
        if sym not in broker_map or broker_map[sym] is None or len(broker_map[sym]) == 0:
            continue
        b = broker_map[sym]
        agg = (b[b.side == 'top_buyers'].groupby('month')['net_idr'].sum())
        tot = (b.groupby('month')[['buy_idr', 'sell_idr']].sum().sum(axis=1))
        m_z = (agg - agg.mean()) / (agg.std() + 1e-12)
        sh = (agg / (tot + 1e-12))
        m_z = m_z.clip(-3, 3) / 3   # -1..1
        sh = sh.clip(-1, 1)
        s = pd.concat([m_z, sh], axis=1).mean(axis=1)
        s.index = pd.to_datetime(s.index + '-28')
        parts.append(s.rename(t))
    if not parts: return None
    fb = pd.concat(parts, axis=1).sort_index()
    # forward-fill per kolom di grid harian: nilai bulanan berlaku sampai bulan berikut
    F = fb.reindex(C.index.union(fb.index)).ffill().reindex(C.index)
    F = F.where(fb.notna().reindex(C.index.union(fb.index)).ffill().reindex(C.index))
    # komponen foreign 5d z (live), bobot sama dgn broker
    if foreign_map:
        fparts = []
        for t in C.columns:
            sym = t.replace('.JK', '')
            if sym not in foreign_map or foreign_map[sym] is None or len(foreign_map[sym]) == 0:
                continue
            f = foreign_map[sym]['net_foreign_inflow']
            f.index = pd.to_datetime(f.index)
            f5 = f.rolling(5).sum()
            fz = ((f5 - f5.rolling(120, min_periods=30).mean()) /
                  (f5.rolling(120, min_periods=30).std() + 1e-12)).clip(-3, 3) / 3
            fparts.append(fz.rename(t))
        if fparts:
            FF = pd.concat(fparts, axis=1).sort_index().reindex(C.index)
            base = F.notna()            # grid harian hasil ffill bulanan
            F = 0.6*F.fillna(0).add(0.4*FF.fillna(0), fill_value=0)
            F = F.where(base | FF.notna())
    return F.rank(axis=1, pct=True)

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
            parts.append(p.reindex_like(p_m)); ws.append(cfg.WEIGHTS[k])
    # weighted mean nan-aware: saham tanpa data satu pilar tetap dihitung dari pilar lain
    num = pd.DataFrame(0.0, index=p_m.index, columns=p_m.columns)
    den = pd.DataFrame(0.0, index=p_m.index, columns=p_m.columns)
    for p, w in zip(parts, ws):
        num = num.add(p.fillna(0)*w, fill_value=0)
        den = den.add(p.notna().astype(float)*w, fill_value=0)
    score = num.div(den.where(den > 0))
    score = score.where(p_m.notna())   # harga stale (momentum NaN) = tidak diskor, jangan skor flow-only
    if index_close is not None:
        score = score.where(regime(ohlcv, index_close), score)  # gate -> status, bukan nol
    return score
