#!/bin/bash
# arus_daily.sh — cron harian ARUS. 100% Sectors API.
# Sumber: Sectors-first by design.
# Cost: ~22-25 kredit/hari bursa, 0 kredit weekend/libur (guard).
#
# Pakai:
#   - Hermes Agent: taruh di ~/.hermes/scripts/ lalu `hermes cron create` (lihat DEPLOY.md)
#   - Native cron: taruh di /usr/local/bin/ lalu `crontab -e` (lihat DEPLOY.md)
#   - Docker: pakai docker-compose up cron (lihat docker-compose.yml)
#
# Env yang dibutuhkan (dari .env atau environment):
#   SECTORS_API_KEY  - Sectors API key
#   ARUS_BOT_TOKEN   - Telegram bot token
#   ARUS_CHAT_ID     - Telegram chat ID tujuan
#   ARUS_REPO_DIR    - path ke repo (default: directory script ini)
#   ARUS_PYTHON      - python interpreter (default: python3 di venv, atau `python3` system)

export TZ=Asia/Jakarta
set -u

# Resolve repo dir & python — flexible untuk cron / Docker
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="${ARUS_REPO_DIR:-$(cd "$SCRIPT_DIR/../.." && pwd)}"
cd "$REPO_DIR"

# Pilih python: ARUS_PYTHON > ~/idx-backtest/.venv/bin/python > python3 system
if [ -n "${ARUS_PYTHON:-}" ]; then
    PY="$ARUS_PYTHON"
elif [ -x "$HOME/idx-backtest/.venv/bin/python" ]; then
    PY="$HOME/idx-backtest/.venv/bin/python"
else
    PY="$(command -v python3)"
fi
[ -z "$PY" ] && { echo "python3 tidak ditemukan — set ARUS_PYTHON atau install python3"; exit 1; }

# Load .env kalau ada (cron gak selalu auto-load)
if [ -f "$REPO_DIR/.env" ]; then
    set -a; . "$REPO_DIR/.env"; set +a
fi

TS() { date '+%Y-%m-%d %H:%M'; }

# Guard 1: weekend — bursa tutup, jangan buang kredit
DOW=$(date +%u)
if [ "$DOW" -gt 5 ]; then
    echo "$(TS) weekend — bursa tutup, skip."
    exit 0
fi

echo "== ARUS cron $(TS) WIB =="

# 1. Sectors: harga harian + IHSG (bursa-buka detector di fetch script handle Senin pagi)
"$PY" scripts/fetch_sectors_prices.py 30 2>&1 | tail -3

# 2. Sectors: broker bulan berjalan + foreign 7 hari (idempotent)
"$PY" scripts/fetch_sectors_daily.py 2>&1 | tail -2

# Guard 2: hari libur bursa (weekday tapi tanpa bar baru) — jangan kirim alert basi
LAST=$("$PY" -c "import pandas as pd; print(pd.read_csv('data/cache/_JKSE.csv', index_col=0, parse_dates=True).index[-1].date())" 2>/dev/null)
TODAY=$(date +%F)
if [ "$LAST" != "$TODAY" ]; then
    echo "$(TS) bursa libur (bar IHSG terakhir: $LAST) — scan & alert diskip."
    exit 0
fi

# 3. Scan + alert
OUT=$("$PY" -m app.main 2>&1)
echo "$OUT" | grep -E "regime|alert" | head -4

if echo "$OUT" | grep -q "NO-ALERT"; then
    echo "$(TS) scan selesai — tidak ada alert hari ini"
else
    echo "--- alert terkirim ---"
fi
