# Deployment

ARUS designed portable — repo self-contained, dua cara jalanin, keduanya
gak butuh AI agent atau service khusus. Pilih sesuai infrastruktur.

## Prasyarat

- Linux / macOS
- Python 3.11+ atau Docker
- Sectors API key (https://sectors.app → API key)
- Telegram bot token + chat ID (opsional, kalau mau alert)
- File `.env` di root repo (copy dari `.env.example`)

## Cara 1 — Native Python (recommended untuk dev)

Langsung di host tanpa container. Cocok untuk laptop, VPS kecil, atau
setup cepat tanpa Docker.

```bash
# 1. Clone repo
git clone https://github.com/johnhendrickh/arus-idx.git ~/arus
cd ~/arus

# 2. Setup .env
cp .env.example .env
nano .env   # isi SECTORS_API_KEY, ARUS_BOT_TOKEN, ARUS_CHAT_ID

# 3. Virtualenv + install
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# 4. Run web screener
.venv/bin/python -m app.server
# Dashboard: http://localhost:8787

# 5. Manual fetch + scan (satu kali)
.venv/bin/python scripts/fetch_sectors_prices.py 30
.venv/bin/python scripts/fetch_sectors_daily.py
.venv/bin/python -m app.main
```

### Otomasi harian pakai cron

Tambahkan ke crontab user (`crontab -e`):

```cron
TZ=Asia/Jakarta
# Setiap hari bursa 16:15 WIB — fetch + scan + alert
15 16 * * 1-5 cd ~/arus && .venv/bin/python scripts/fetch_sectors_prices.py 30 && .venv/bin/python scripts/fetch_sectors_daily.py && TZ=Asia/Jakarta .venv/bin/python -m app.main >> ~/arus/data/cron.log 2>&1
```

Guard weekend + bursa libur di-handle script `app/main.py`.

## Cara 2 — Docker Compose (recommended untuk VPS/cloud)

Full containerized, reproducible dari clone sampai jalan.

```bash
# 1. Clone + setup .env
git clone https://github.com/johnhendrickh/arus-idx.git ~/arus
cd ~/arus
cp .env.example .env
nano .env   # isi kredensial

# 2. Build + run
sudo docker compose up -d --build

# 3. Cek status
sudo docker compose ps
sudo docker compose logs -f server

# 4. Akses dashboard
curl http://localhost:8787/api | jq
# Browser: http://localhost:8787

# 5. Update (setelah git pull)
sudo docker compose up -d --build
```

`docker-compose.yml` jalanin satu service: `arus-server` (web screener
port 8787). Cache + ledger di persistent volume `arus-data` — gak hilang
saat container rebuild.

### Cron harian di Docker host

Jalankan cron di **host** (bukan di dalam container) — lebih sederhana:

```cron
TZ=Asia/Jakarta
15 16 * * 1-5 cd ~/arus && sudo docker compose run --rm server python scripts/fetch_sectors_prices.py 30 >> ~/arus/data/cron.log 2>&1
```

Atau pakai `docker exec` kalau mau reuse container:

```cron
15 16 * * 1-5 cd ~/arus && sudo docker exec arus-server python scripts/fetch_sectors_prices.py 30 >> ~/arus/data/cron.log 2>&1
```

## Trade-off

| Aspek | Native Python | Docker |
|---|---|---|
| Setup time | 3 menit | 5 menit |
| Reproducibility | rendah (tergantung host Python) | tinggi (image lock) |
| Resource overhead | none | ~50MB RAM idle |
| Cron di | host crontab | host crontab + `docker exec/run` |
| Portabilitas | perlu Python di host | image self-contained |
| Cocok untuk | dev, laptop | VPS, cloud, demo |

## Healthcheck

```bash
# API endpoint
curl http://localhost:8787/api | jq

# Cek apakah server hidup
curl -f http://localhost:8787/ || echo "DOWN"
```

## Update flow

```bash
# Native
cd ~/arus && git pull && crontab -e   # adjust kalau ada perubahan crontab

# Docker
cd ~/arus && git pull && sudo docker compose up -d --build
```

## TL;DR

```bash
# Paling cepet (5 menit): Docker
git clone https://github.com/johnhendrickh/arus-idx.git ~/arus && cd ~/arus
cp .env.example .env && nano .env
sudo docker compose up -d --build
# Dashboard: http://localhost:8787
```
