# IDX Flow Signal (nama kerja: ARUS)

Scanner saham IDX 3-pilar: **momentum berkualitas x fundamental x aliran dana (broker/asing)**.
Pure deterministic code — tanpa AI. Output: skor per saham + alert Telegram.
Bukan auto-trade. Decision support, user eksekusi manual.

## Problem statement
Trader ritel Indonesia mengikuti sinyal teknikal yang sudah terbukti tidak efektif di IDX
(backtest kami: mean-reversion ala bot = -14%/yr 2023+, bandarmology price-only = IC 0.010/noise).
ARUS memberi skor berbasis data yang tidak dilihat semua orang (broker summary & foreign flow
Sectors) plus bukti akurasi tiap sinyal — lengkap dengan jumlah sampelnya.

## Pilar & bobot (divalidasi backtest 2021-2026, Yahoo .JK)
| Pilar | Bobot | Sumber | Status |
|---|---|---|---|
| Momentum berkualitas (consensus 20/60/120 + risk-adj) | 45% | price cache | ✅ jalan sekarang |
| Fundamental (ROE, E/P; penalti growth-trap) | 25% | Yahoo fundamentals → nanti Sectors | ✅ jalan sekarang |
| Flow (akumulasi broker + net foreign) | 30% | **Sectors API v2** | ⏳ tunggu key |

Gate: IHSG < EMA50 → mode defensif. Floor: kuintil likuiditas terbawah di-skip.
Bobot di-renormalisasi otomatis kalau pilar flow belum ada data.

## Arsitektur
```
fetch_sectors.py   bulk 1x -> data/cache/*.csv   (hemat kredit, cache-first)
fetch_yahoo.py     bulk 1x -> data/cache/       (OHLCV + fundamentals)
score.py           engine 3 pilar, pure function
backtest.py        IC, top-vs-bot, per-sub-periode, selalu tampil n
alert.py           format pesan -> Telegram
main.py            scan hari ini: cache -> skor -> print + (opsi) kirim
```

## Aturan produk (hard)
1. Skor tidak pernah ditampilkan tanpa `n` sampel backtest-nya.
2. `n < 15` → label "belum teruji".
3. Tidak ada order placement. Tidak ada koneksi sekuritas.
4. Semua data Sectors di-cache; API tidak dipanggil per-user.

## Hackathon
Track 03 Market Intelligence — derived insight, Sectors API sebagai core.
Repo dibuat 15 Sep 2026 (dalam build period). Submit 30 Sep 23:59 WIB.
