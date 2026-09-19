# BACKTEST.md — bukti di balik skor (diisi per temuan, dengan tanggal run)

## Engine price-only (Yahoo .JK, 20 saham, 2021→Sep 2026, fee 0.4% + slip 0.2%)
Run: 2026-09-15, script @ ~/idx-backtest (eksperimen pra-repo; dipindah ke app/backtest.py)

| Setup | metrik | hasil |
|---|---|---|
| Composite bot crypto (mean-rev) | port full TP/SL 2023+ | **-14%/yr, DD -49%** — GAGAL |
| Bandarmology price-only (Wyckoff) | IC | +0.010 (t=0.8) — noise |
| Close-strength 20d | IC | -0.027 (t=-3.1) — sinyal TERBALIK |
| Revenue growth top | IC | **-0.102 (t=-6.2)** — growth-trap, di-penalti |
| #6 momentum (consensus+vol-adj) | IC / top>bot | +0.093 (t=8.7) / 63%, n=38 |
| #6 + ROE/E-P 30% | IC / top>bot | +0.121–0.123 (t≈9) / 73-77%, n=22 (window funda 2 thn) |
| regime gate IHSG>EMA50 | efek | +0.77→+2.66 spread saat UP; 2026 Mar-Sep OFF terus |

## Yang HARUS di-test ulang pakai data Sectors (setelah key)
1. z-score net-buy top broker 10d → f20 (IC, split periode)
2. konsistensi broker sama >=5 hari berturut
3. net foreign 5d z-score
4. combo 3 pilar vs 2 pilar (naik tidak IC-nya?)
5. riwayat broker-summary bisa mundur berapa tahun (n efektif dipangkas!)

## Pilar flow (Sectors, kalibrasi Sep 2026 — window Feb 2025→Sep 2026, 19 bln, n=18)
| Setup | IC | top>bot | med spread |
|---|---|---|---|
| Flow mentah (broker-top z + foreign 5d z) | +0.026 (t=0.4) | 33% | -1.9% |
| Flow saat regime ON | **-0.147 (t=-3.1)** | 11% | -5.1% |
| Combo mom+flow | +0.054 | 67% | +1.1% |

Kesimpulan: flow mentah TIDAK prediktif dalam window teruji. Keputusan:
bobot flow 0.30 → 0.20, diposisikan sebagai alert kontekstual ("dicatat ke ledger"),
bukan klaim akurasi. Angka akan ditinjau ulang saat ledger hidup >20 sinyal.
Credit terpakai total: 846/1000 (log: data/fetch.log).

## Aturan pelaporan
- Selalu split 2021-23 vs 2024-26. Selalu tampilkan n.
- n<15 → label "belum teruji" di produk.
- Median, bukan mean (ekor IDX panjang).
