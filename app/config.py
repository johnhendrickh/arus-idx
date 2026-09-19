"""config.py — satu sumber kebenaran parameter."""
UNIVERSE = ['MEDC', 'BBCA','BBRI','BMRI','BBNI','TLKM','ASII','UNVR','ICBP',
            'ADRO','ANTM','PTBA','ITMG','SMGR','INTP','AKRA','TPIA',
            'BRPT','SILO','BUVA','PGEO']

# gate & floor
REGIME_EMA_SPAN = 100        # ~EMA50 harian (span Yahoo weekly-proxy; kalibrasi saat dev)
LIQ_FLOOR_PCT = 0.2          # skip kuintil likuiditas terbawah

# bobot pilar — flow TIDAK masuk skor dan TIDAK jadi veto (bukti docs/BACKTEST.md:
# z-score IC +0.021, streak -0.000, divergensi +0.007 — noise; veto OR terlalu sensitif,
# veto AND malah kontrarian +2.0% — dua-duanya gak bisa dipercaya di window data kita).
# Flow = konteks informasi murni: ditampilkan, dicatat ke ledger, dinilai live.
WEIGHTS = {'momentum': 0.55, 'fundamental': 0.45}

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
TELEGRAM_ENABLED = True        # aktif 19 Sep — /start sudah dikirim, trigger manual verified. Alert tidak pernah meng-order apa pun.
