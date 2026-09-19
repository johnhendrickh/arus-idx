"""config.py — satu sumber kebenaran parameter."""
UNIVERSE = ['MEDC', 'BBCA','BBRI','BMRI','BBNI','TLKM','ASII','UNVR','ICBP',
            'ADRO','ANTM','PTBA','ITMG','SMGR','INTP','AKRA','TPIA',
            'BRPT','SILO','BUVA','PGEO']

# gate & floor
REGIME_EMA_SPAN = 100        # ~EMA50 harian (span Yahoo weekly-proxy; kalibrasi saat dev)
LIQ_FLOOR_PCT = 0.2          # skip kuintil likuiditas terbawah

# bobot pilar — hasil kalibrasi Sep 2026: flow mentah tidak prediktif (IC+0.026, n=18;
# saat regime ON malah -0.147). Flow turun jadi 0.20, posisinya alert kontekstual.
WEIGHTS = {'momentum': 0.50, 'fundamental': 0.30, 'flow': 0.20}

# momentum (hasil riset 15 Sep — varian #6 menang)
MOM_HORIZONS = [20, 60, 120]   # consensus "semua arah naik"
MOM_LOOKBACK = 60              # risk-adjusted mom60/vol20
VOL_LOOKBACK = 20

# fundamental
ROE_GATE = 0.5                 # ROE rank > median (naikkan akurasi 63->77% pada tes)
GROWTH_PENALTY = True          # hindari top-revenue-growth (IC -0.10 di tes kita)

# flow (Sectors) — diisi setelah key
BROKER_WINDOW_D = 10           # akumulasi = net top-buyer 10 hari
FOREIGN_WINDOW_D = 5

# biaya backtest
FEES = 0.004                   # 0.15% beli + 0.25% jual + buffer
SLIP = 0.002
HOLD_D = 20

# output
MIN_SAMPLE_LABEL = 15          # n < ini -> "belum teruji"
TELEGRAM_ENABLED = False       # flip manual; alert jangan auto-order apa pun
