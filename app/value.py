"""value.py — harga acuan + edge/stop-loss per saham (informasi, bukan rekomendasi).

Tidak masuk skor (composite di score.py tetap murni rank-based).
Peran: kasih konteks "kalau OK, kira-kira harga saat ini murah/netral/mahal
vs median setahun terakhir, plus target/stop derivatif dari backtest".

Output per symbol (row):
- fair_mid   : median close 252 hari terakhir (proxy "harga acuan")
- fair_low   : fair_mid * 0.92  (band bawah, -8%)
- fair_high  : fair_mid * 1.08  (band atas, +8%)
- pos_band   : "murah" / "netral" / "mahal" (current vs fair_mid)
- target_20d : current * (1 + EDGE_UP)  — backtest top-5 median spread +1.65%/20d
- stop_loss  : min low 252 hari  — pakai 52-week low (252 hari) sebagai floor
- edge_pct   : (target_20d - current) / current  — simple % upside

Pendekatan sengaja simple — bukan DCF / DDM, karena:
- Data fundamental di cache cuma NI/revenue/equity per tahun (no shares outstanding, no EPS precise)
- Close median 252 hari cukup robust sebagai "harga acuan yang dianggap pasar akhir-akhir ini"
- Std-dev band bisa di-tweak per saham volatilitas (saat ini fixed ±8%)

EDGE_UP = 0.0165 (= +1.65%/20d) konsisten dengan backtest combo m+f median spread.
STOP_LOOKBACK = 252 hari (1 tahun bursa).
"""
import pandas as pd, numpy as np

EDGE_UP = 0.0165            # 20-day upside target — backtest combo m+f
STOP_LOOKBACK = 252          # 1 tahun bursa
FAIR_LOOKBACK = 252          # median close 1 tahun
BAND_LOW_PCT = 0.08          # -8% dari fair_mid
BAND_HIGH_PCT = 0.08         # +8% dari fair_mid

# Label user-facing — pakai bahasa kasual, langsung, awam-friendly.
POS_BAND_LOW = 'murah'       # current < fair_low: harga di bawah pita → pasar menilai lebih murah
POS_BAND_MID = 'netral'      # dalam pita
POS_BAND_HIGH = 'mahal'      # current > fair_high: harga di atas pita → pasar menilai lebih mahal


def fair_value(ohlcv):
    """Dict {sym: {fair_mid, fair_low, fair_high, current, pos_band, target_20d, stop_loss, edge_pct}}.
    Return None untuk symbol tanpa cukup history (< 60 bar)."""
    if not ohlcv:
        return {}
    out = {}
    for sym, df in ohlcv.items():
        if df is None or len(df) < 60:
            continue
        close = df['Close']
        current = float(close.iloc[-1])
        # Acuan: median close 252 hari (atau sepanjang data, mana yang ada)
        window = close.tail(min(FAIR_LOOKBACK, len(close)))
        fair_mid = float(window.median())
        fair_low = fair_mid * (1 - BAND_LOW_PCT)
        fair_high = fair_mid * (1 + BAND_HIGH_PCT)
        # Posisi current vs pita fair
        if current < fair_low:
            pos_band = POS_BAND_LOW
        elif current > fair_high:
            pos_band = POS_BAND_HIGH
        else:
            pos_band = POS_BAND_MID
        # Target 20d: backtest combo m+f top-5 median spread
        target_20d = current * (1 + EDGE_UP)
        # Stop-loss: 52-week low
        stop_loss = float(window.min())
        # Edge %
        edge_pct = (target_20d - current) / current
        out[sym] = {
            'fair_mid': round(fair_mid, 0),
            'fair_low': round(fair_low, 0),
            'fair_high': round(fair_high, 0),
            'current': round(current, 0),
            'pos_band': pos_band,
            'target_20d': round(target_20d, 0),
            'stop_loss': round(stop_loss, 0),
            'edge_pct': round(edge_pct * 100, 2),
        }
    return out

