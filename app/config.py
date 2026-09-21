"""config.py — satu sumber kebenaran parameter.

UNIVERSE = 21 saham blue-chip IDX, dipilih manual berdasarkan:
- Likuiditas: avg daily value IDR > 50M (top quartile IDX 2025-2026)
- Sub-sektor coverage: bank (4), telco (1), consumer (2), mining (4),
  material (2), energy (2), healthcare (1), agro (1), tech (1), misc (3)
- Foreign flow aktif: ada /foreign-flow/ data di Sectors (gak suspension)
- Broker summary stabil: ada /broker-summary/ data bulanan (gak IPO baru)

Universe ini STATIS — dipilih sekali saat setup, gak auto-rebalance.
Alasan: scope hackathon (Track 03 Market Intelligence), coverage > 21
saham = blow budget kredit (900 IDX × 3 kredit = ~2700/hari bursa).

On-demand ticker management:
- `python scripts/fetch_one.py MEDC` — tambah saham baru (~46 kredit
  sekali: 5y history + broker-top 19 bln + foreign 1 thn)
- `python scripts/lookup.py AMRT` — analisis ad-hoc ticker mana pun
  (~2-4 kredit cache-first, gak nyimpan ke universe)
- API limit harian: ARUS_ONDEMAND_LIMIT (default 3 saham/hari)

Pilih 21 diganti kapan? Hanya saat: emiten delisted / suspension > 1 bln,
atau ada saham baru naik kelas jadi blue-chip (re-evaluate per quarter).
"""
UNIVERSE = ['MEDC', 'BBCA','BBRI','BMRI','BBNI','TLKM','ASII','UNVR','ICBP',
            'ADRO','ANTM','PTBA','ITMG','SMGR','INTP','AKRA','TPIA',
            'BRPT','SILO','BUVA','PGEO']

# gate & floor
REGIME_EMA_SPAN = 50         # EMA50 harian (data _JKSE daily; span=harus 50, bukan 100)
REGIME_BUFFER = 0.01         # butuh >1% di atas EMA50 = UP beneran; 0..1% = deadzone (tipis = flip-flop harian)
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
