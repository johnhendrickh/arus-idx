# BACKTEST.md — bukti di balik skor (diperbarui per temuan)

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

## Pilar flow (Sectors, kalibrasi Sep 2026 — window Feb 2025→Sep 2026, ~19 bln, n=18-23)
| Setup | IC | top>bot | med spread |
|---|---|---|---|
| `flow_pillar()` mentah (broker-top z + foreign 5d z) | +0.026 (t=0.4) | 33% | -1.9% |
| `flow_pillar()` saat regime ON | **-0.147 (t=-3.1)** | 11% | -5.1% |
| Combo mom+flow | +0.054 | 67% | +1.1% |

## Re-test 2026-09-21 (data Sectors, bt_proxy.py dengan IHSG-proxy 1520 bar)

**Run: 2026-09-21, script @ scripts/bt_proxy.py, IHSG-proxy korelasi 0.933 dengan IHSG asli 62 bar.**

| Setup | IC | top>bot | med spread | n |
|---|---|---|---|---|
| Momentum saja, gate IHSG-proxy ON | +0.008 (t=0.2) | **58%** | **+2.28%** | 12 |
| Momentum saja, tanpa gate | -0.016 (t=-0.3) | 50% | +0.43% | 18 |
| Fundamental saja, gate ON | +0.126 (t=1.2) | 42% | -1.80% | 12 |
| Combo mom+fundamental, gate ON | **+0.113 (t=1.4)** | **67%** | **+1.65%** | 12 |
| Full combo mom+fund+flow, gate ON | +0.089 (t=1.1) | 58% | +0.51% | 12 |

**Kesimpulan:**
- Gate IHSG-proxy bantu momentum: IC -0.016 → +0.008, win 50% → 58%, spread +0.43% → +2.28%.
- Combo momentum + fundamental terbaik: IC +0.113, win 67%, median spread +1.65%/20d rebalance.
- Memasukkan flow ke combo justru turunkan IC ke +0.089 — validasi keputusan "flow = informasi, bukan skor".
- n=12 sample kecil (window 18 bln × rebalance 20d). Kesimpulan statistik belum definitif; backtest sub-periode (2025 vs 2026) belum di-split karena n akan terlalu kecil.

## Re-test kandidat flow baru (bt_flow_v2.py, 2026-09-21)
| Kandidat | Metrik | Hasil |
|---|---|---|
| K1 konfirmasi (top-momentum + dibeli asing) | spread median fwd20 | **-0.73%** (lebih buruk daripada dilepas) |
| K2 persistensi (streak net-buy) | IC | -0.010 (noise) |
| K3 divergensi (harga naik + asing beli vs jual) | spread median | +1.74% |

Tiga kandidat flow tambahan semuanya inkonsisten atau kontradiktif.
Alasan flow_flags (`flow_flags()` di score.py) tetap ada: OR sudah kami uji
terlalu sensitif (20/21 saham ke-flag saat DOWN), AND kontradiktif
(med-spread -5.1%). Flag bukan dipakai sebagai sinyal, hanya konteks.

## Anomali data Sectors yang perlu diketahui

- **Baris hantu vol=0** di hari libur bursa (mis. 2026-08-25): IHSG gak ada
  baris, tapi ~10 cache saham dapat baris phantom `OHLC flat, vol=0`.
  Fix: `read_ohlcv()` di `app/io_cache.py` filter `Volume > 0`.
  Efek: 9 dari 21 saham sebelumnya kehilangan skor momentum → sekarang 21/21 valid.
- **Index endpoint dibatasi 62 bar** (`/index-daily/ihsg/` max 62 apapun window).
  Solusi: `data/cache/_JKSE_proxy.csv` = equal-weight avg daily return semua
  saham cache, 1520 bar, korelasi 0.933 dengan IHSG asli. Dipakai untuk
  backtest saja; runtime cukup IHSG asli 62 bar.

## Aturan pelaporan
- Selalu split 2021-23 vs 2024-26. Selalu tampilkan n.
- n<15 → label "belum teruji" di produk.
- Median, bukan mean (ekor IDX panjang).
- Setiap klaim angka backtest di README harus bisa direproduksi via script yang ada di repo.
