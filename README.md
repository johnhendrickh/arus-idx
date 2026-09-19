# ARUS — IDX Flow Intelligence

> **Baca arusnya, bukan tebakannya.**

Screener saham IDX dengan **3 pilar skor** — momentum berkualitas × fundamental × aliran dana bandar & asing (via [Sectors API v2](https://sectors.app)) — lengkap dengan **rapor akurasi**: setiap pilar membawa bukti backtest atau label "belum teruji", bukan janji.

**Untuk siapa:** trader ritel IDX yang tiap hari lihat sinyal beredar di grup Telegram tanpa pernah tahu mana yang benar-benar akurat.

**Problem statement (1 kalimat):**
Trader ritel IDX punya banyak alat sinyal tapi nggak ada yang jujur soal akurasi — ARUS memberi skor 3 pilar (momentum + fundamental + broker/foreign flow dari Sectors) dan menampilkan bukti backtest tiap sinyal, bukan janji.

---

## Kenapa ARUS beda

| Alat sinyal biasa | ARUS |
|---|---|
| "Sinyal beli X!" tanpa bukti | IC, hit-rate, dan jumlah sampel (n) ditampilkan bersama skor |
| Klaim akurasi 90% | Backtest dengan fee + slippage, sub-periode split, kegagalan didokumentasi |
| Bandarmology dari pola harga (tebakan) | Data broker & foreign flow **asli** dari Sectors API |
| Sinyal spam tiap hari | Gate regime IHSG — diam saat market jelek |

## Arsitektur

```
Yahoo Finance (gratis)          Sectors API v2 (kredit, core differentiator)
├── OHLCV harian 5 thn           ├── broker-summary/{sym}/top  — akumulasi bandar per bulan
├── IHSG (regime gate)           ├── foreign-flow/{sym}        — net asing harian
└── fundamental tahunan          └── (riwayat broker: Feb 2025→; itulah mengapa
                                      pilar flow pakai ledger live self-grading)
        └──────────────┬──────────────────────┘
                       ▼
     skor = 50% momentum + 30% fundamental + 20% flow
     (gate: IHSG > EMA50; floor: likuiditas 20-hari)
                       ▼
   ┌───────────────┬────────────────┬──────────────────┐
   screener web     alert Telegram    ledger sinyal live
   (1 halaman)      (16.15 WIB)       (auto-grade +20 hari)
```

## Skor 3 pilar

1. **Momentum berkualitas (50%)** — `0.5×rank(consensus mom20/60/120) + 0.5×rank(mom60/vol20)`. Backtest 5 tahun (2021–2026, fee 0.4% + slip 0.2%, entry T+1): **IC +0.093, t=8.7, top-5 vs bottom-5 menang 24/38 (63%)**.
2. **Fundamental (30%)** — ROE (bobot utama) + E/P bonus + **penalti revenue growth tinggi** (growth-trap terbukti di IDX: growth IC −0.102). Combo dengan momentum: IC +0.114, top>bot 77% (caveat: fundamental tahunan, n≈22 rebalance).
3. **Flow (20%)** — z-score net akumulasi broker top (bulanan) + z-score net foreign 5 hari. **Jujur: versi kalibrasi 19 bulan TIDAK prediktif** (IC +0.026; saat regime ON malah −0.147). Karena itu bobotnya kecil, posisinya *alert kontekstual*, dan tiap sinyal dicatat ke ledger yang mengukur hasilnya sendiri. Rapor flow tumbuh dari data live — bukan klaim.

**Kegagalan yang kami dokumentasikan (bukan disembunyikan):** bandarmology price-only IC +0.010 (noise), RSI dip-buy median −0.8%/trade, porting strategi crypto −14%/yr di IDX. Lengkap di `docs/BACKTEST.md`.

## Cara pakai

```bash
# 0. Siapkan .env (lihat .env.example): SECTORS_API_KEY, ARUS_BOT_TOKEN, ARUS_CHAT_ID
pip install -r requirements.txt

# 1. Unduh data (Yahoo gratis; Sectors ~46 kredit/saham sekali saja, lalu tercache)
python scripts/fetch_yahoo.py                  # harga + IHSG + fundamental
python scripts/fetch_sectors.py BBCA BBRI ...  # broker-top + foreign flow

# 2. Tambah saham pilihanmu sendiri (on-demand, hemat kredit)
python scripts/fetch_one.py MEDC               # validasi ticker → fetch → masuk universe

# 3. Scan & lihat skor
python -m app.main                             # scan CLI + preview alert

# 4. Web screener
python -m app.server                           # → http://localhost:8787
```

Saham tanpa cache = otomatis skip; bulan yang sudah tercache tidak di-fetch ulang (idempotent). Log kredit per-call: `data/fetch.log`. Limit aman: 3 saham baru/hari.

## Struktur repo

```
app/
  config.py     — universe + bobot pilar + parameter gate (semanya di satu tempat)
  io_cache.py   — satu-satunya modul yang menyentuh disk (CSV polos di data/cache/)
  score.py      — 3 pilar + composite + regime gate + liquidity floor
  backtest.py   — harness IC + top-vs-bottom + split sub-periode (wajib)
  ledger.py     — buku sinyal live: record → resolve (+20 hari) → stats
  main.py       — pipeline harian: cache → skor → alert
  alert.py      — Telegram (informasi saja, TIDAK ada aksi trading)
  server.py     — web screener stdlib (http.server, tanpa framework)
scripts/
  fetch_yahoo.py     — OHLCV + IHSG + fundamental (gratis, unlimited)
  fetch_sectors.py   — broker-top + foreign flow (idempotent, log kredit)
  fetch_one.py       — tambah 1 ticker on-demand ke universe
  bt_flow_window.py  — backtest kalibrasi pilar flow
docs/
  BACKTEST.md   — SEMUA bukti: angka menang, angka kalah, sampel n, metode
data/cache/     — CSV cache (di-gitignore; regenerable via scripts)
data/ledger.csv — rapor sinyal live (tumbuh sendiri)
```

## Aturan main kami sendiri

1. **Tiap angka bawa sampel.** Tidak ada klaim tanpa n. IC dihitung per-rebalance, spread median, top-vs-bottom hit-rate.
2. **Yang belum teruji dilabeli belum teruji.** Pilar flow saat ini: "kalibrasi 19 bln tidak prediktif; rapor hidup via ledger." Bukan disembunyikan di footnote.
3. **Bukan rekomendasi.** Gate regime DOWN = semua status WAIT. Tidak ada auto-trade, tidak ada "garansi".
4. **Kredit Sectors dipakai hanya untuk data yang tidak ada di tempat lain** (broker, foreign flow). Harga dari Yahoo — bukan karena pelit, tapi karena kredit habis untuk data komoditas itu pemborosan.

---
*Hackathon Sectors 2026 — Track 03 (Market Intelligence). Dibangun solo. Repo freeze setelah submit sesuai rules §05.*
