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

**Sectors-first by design: semua data runtime dari Sectors API.**

```
Sectors API v2 (core data source — 100% runtime)
├── /daily/{sym}.JK          — OHLCV + market cap harian (update 30 hari/hari)
├── /index-daily/ihsg        — IHSG (regime gate)
├── /broker-summary/{sym}/top — akumulasi bandar per bulan
└── /foreign-flow/{sym}      — net asing harian
        │
        ├── snapshot historis 5 tahun (statis, hanya utk backtest — lihat catatan)
        └── fundamental tahunan
                       ▼
     skor = 55% momentum + 45% fundamental (+ kolom flow informasional)
     (gate: IHSG > EMA50; floor: likuiditas 20-hari)
                       ▼
   ┌───────────────┬────────────────┬──────────────────┐
   screener web     alert Telegram    ledger sinyal live
   (1 halaman)      (16.15 WIB)       (auto-grade +20 hari)
```

> **Catatan teknis — history backtest:** endpoint harga Sectors melayani data
> per-window 90 hari, sedangkan backtest momentum butuh 5 tahun. Solusinya:
> snapshot history di-bootstrap sekali saat setup, lalu **seluruh pembaruan
> harian 100% dari Sectors API**. Kualitas snapshot sudah diverifikasi terhadap
> data Sectors: 1.519 hari overlap, selisih harga median 0.0 (identik).
> Bukti bahwa Sectors adalah sumber inti: hapus Sectors dari pipeline, dan
> screener, regime gate, pilar flow, plus semua update harga — berhenti total.

## Skor 3 pilar

1. **Momentum berkualitas (55%)** — `0.5×rank(consensus mom20/60/120) + 0.5×rank(mom60/vol20)`. Backtest 5 tahun (2021–2026, fee 0.4% + slip 0.2%, entry T+1): **IC +0.093, t=8.7, top-5 vs bottom-5 menang 24/38 (63%)**.
2. **Fundamental (45%)** — ROE (bobot utama) + E/P bonus + **penalti revenue growth tinggi** (growth-trap terbukti di IDX: growth IC −0.102). Combo dengan momentum: IC +0.114, top>bot 77% (caveat: fundamental tahunan, n≈22 rebalance).
3. **Flow — informasi, bukan sinyal.** Net asing 5 hari + arah akumulasi broker-top bulanan, ditampilkan apa adanya di kolom tersendiri. **Kami menguji flow sebagai sinyal dan hasilnya negatif**: z-score IC +0.021, streak −0.000, divergensi +0.007 (semua noise, n=220); veto OR menandai 20/21 saham saat market jelek; veto AND malah kontrarian (+2.0% untuk saham yang di-flag). Karena itu flow tidak masuk skor dan tidak mem-veto — perannya transparansi: pemakai lihat arus dana asli sambil tahu itu belum terbukti prediktif. Rapor flow ditumbuhkan dari ledger live (tiap sinyal diukur 20 hari), bukan dari klaim.

**Kegagalan yang kami dokumentasikan (bukan disembunyikan):** bandarmology price-only IC +0.010 (noise), RSI dip-buy median −0.8%/trade, porting strategi crypto −14%/yr di IDX. Lengkap di `docs/BACKTEST.md`.

## Cara pakai

```bash
# 0. Siapkan .env (lihat .env.example): SECTORS_API_KEY, ARUS_BOT_TOKEN, ARUS_CHAT_ID
pip install -r requirements.txt

# 1. Unduh data — butuh API key Sectors (lihat .env.example)
python scripts/fetch_sectors_prices.py 30      # harga harian + IHSG (Sectors)
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
  fetch_sectors_prices.py — harga harian + IHSG dari Sectors (runtime utama)
  fetch_sectors.py        — broker-top + foreign flow (idempotent, log kredit)
  fetch_sectors_daily.py  — refresh ringan harian (bulan berjalan + foreign 7d)
  fetch_one.py            — tambah 1 ticker on-demand ke universe
  fetch_yahoo.py          — bootstrap snapshot history backtest (sekali saja, bukan runtime)
  bt_flow_window.py       — backtest kalibrasi pilar flow
docs/
  BACKTEST.md   — SEMUA bukti: angka menang, angka kalah, sampel n, metode
data/cache/     — CSV cache (di-gitignore; regenerable via scripts)
data/ledger.csv — rapor sinyal live (tumbuh sendiri)
```

## Aturan main kami sendiri

1. **Tiap angka bawa sampel.** Tidak ada klaim tanpa n. IC dihitung per-rebalance, spread median, top-vs-bottom hit-rate.
2. **Yang belum teruji dilabeli belum teruji.** Pilar flow saat ini: "kalibrasi 19 bln tidak prediktif; rapor hidup via ledger." Bukan disembunyikan di footnote.
3. **Bukan rekomendasi.** Gate regime DOWN = semua status WAIT. Tidak ada auto-trade, tidak ada "garansi".
4. **Sectors = sumber data inti.** Semua fetch runtime dari Sectors API. Endpoint harga Sectors (window 90 hari) dipakai untuk update harian; snapshot Yahoo hanya untuk bootstrap history backtest — dan itu kami ungkap, bukan sembunyi.

---
*ARUS — peserta Hackathon Sectors 2026, Track 03 (Market Intelligence). Repo ini dibekukan setelah deadline sesuai ketentuan panitia.*
