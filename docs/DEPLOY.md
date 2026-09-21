# DEPLOY.md — 3 cara jalankan ARUS

ARUS designed portable: 1 source repo, 3 cara jalanin. Pilih sesuai
infrastruktur yang ada.

## Prasyarat (semua metode)

- Linux (cron jalan di Linux, di macOS BSD cron — TZ Asia/Jakarta OK)
- Python 3.11+
- Sectors API key (https://sectors.app → API key)
- Telegram bot token + chat ID (opsional, kalau mau alert)
- File `.env` di root repo (lihat `.env.example`)

## Metode 1 — Hermes Agent cron (kayak yg dipake sekarang)

```bash
# Taruh script di ~/.hermes/scripts/ (di luar repo, gak ke-commit)
cp scripts/cron/arus_daily.sh ~/.hermes/scripts/
chmod +x ~/.hermes/scripts/arus_daily.sh

# Cron job: 16:15 WIB = 09:15 UTC (Hermes server UTC, offset +7)
hermes cron create \
  --name "ARUS daily scan" \
  --schedule "15 9 * * 1-5" \
  --script ~/.hermes/scripts/arus_daily.sh \
  --no-agent \
  --deliver origin

# Cek
hermes cron list
hermes cron runs <job_id>
```

`arus_daily.sh` udah handle TZ (`export TZ=Asia/Jakarta`), guard weekend
(`DOW > 5`), guard bursa libur (cek IHSG cache last bar).

**Trade-off:** script di `~/.hermes/scripts/` gak ke-track di git.
Mitigasi: `scripts/cron/arus_daily.sh` di repo adalah source of truth,
sync manual ke `~/.hermes/scripts/` saat update.

## Metode 2 — Native cron (Linux/BSD)

```bash
# Taruh script di /usr/local/bin (system-wide)
sudo cp scripts/cron/arus_daily.sh /usr/local/bin/arus-daily
sudo chmod +x /usr/local/bin/arus-daily

# Set environment vars di /etc/default/arus
sudo tee /etc/default/arus <<EOF
ARUS_REPO_DIR=/opt/arus
ARUS_PYTHON=/opt/arus/.venv/bin/python
EOF

# Crontab
sudo crontab -u arus -e
# Tambah:
TZ=Asia/Jakarta
15 9 * * 1-5 /usr/local/bin/arus-daily >> /var/log/arus/cron.log 2>&1

# Atau pakai file crontab langsung
sudo cp scripts/cron/arus_crontab /etc/cron.d/arus
sudo chmod 0644 /etc/cron.d/arus
```

Cron server baca crontab, `TZ=Asia/Jakarta` set di header biar 16:15 WIB
langsung match. Guard weekend + bursa libur di-handle script.

## Metode 3 — Docker Compose (recommended buat VPS / cloud)

```bash
# 1. Clone repo
git clone https://github.com/johnhendrickh/arus-idx.git /opt/arus
cd /opt/arus

# 2. Setup .env
cp .env.example .env
nano .env   # isi SECTORS_API_KEY, ARUS_BOT_TOKEN, ARUS_CHAT_ID

# 3. Build + run
sudo docker compose up -d --build

# Service yang jalan:
# - arus-server: web screener di :8787
# - arus-cron:    fetch + scan + alert 16:15 WIB
# - volume arus-data: persistent cache & ledger

# Cek
sudo docker compose ps
sudo docker compose logs -f cron       # log cron
sudo docker compose logs -f server     # log web

# Akses dashboard
curl http://localhost:8787/api | jq

# Update (setelah git pull)
sudo docker compose up -d --build
```

**Struktur docker-compose.yml:**
- `server` — `python -m app.server`, port 8787, restart unless-stopped
- `cron` — mount crontab `15 9 * * 1-5`, TZ Asia/Jakarta, log ke `/var/log/arus`
- `arus-data` volume — persistent cache CSV + ledger (regenerable tapi hemat)
- `logs/` bind mount — cron.log + server log ke host

**Image size:** ~180MB (python:3.11-slim + pandas + scipy + requests).
Build cold ~3 menit, incremental ~30 detik.

## Trade-off & catatan

| Aspek | Hermes cron | Native cron | Docker |
|---|---|---|---|
| Setup time | 5 menit | 15 menit | 10 menit |
| Isolation | shared host | shared host | full container |
| Portabilitas | butuh Hermes | Linux only | any host dgn Docker |
| Logs | `~/.hermes/cron/output/<job_id>/` | `/var/log/arus/` | `docker compose logs` |
| Reproducibility | rendah (script di `~/.hermes/`) | sedang (config di /etc) | tinggi (compose file di repo) |
| Resource overhead | none | none | ~50MB RAM idle |
| Hackathon demo | ✅ udah jalan | works | works |

**Pilihan saat ini:** Hermes cron (Metode 1) karena udah live.
Untuk repo publik setelah submit hackathon, default instruksi = Docker
(Metode 3) — full reproducible dari clone sampai jalan.

## Setup cepat — TL;DR

```bash
# Paling cepet (5 menit): Docker
git clone https://github.com/johnhendrickh/arus-idx.git && cd arus-idx
cp .env.example .env && nano .env
sudo docker compose up -d --build
# Dashboard: http://localhost:8787
```

## Update flow

```bash
git pull
sudo docker compose up -d --build    # rebuild image + restart
# ATAU native:
git pull
sudo systemctl restart arus-server   # kalau pakai systemd
```
