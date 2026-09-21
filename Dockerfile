FROM python:3.11-slim

# Install cron (untuk service cron di compose) + tzdata + curl
RUN apt-get update && apt-get install -y --no-install-recommends \
        cron \
        tzdata \
        curl \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# TZ Asia/Jakarta (WIB)
ENV TZ=Asia/Jakarta
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

WORKDIR /app

# Dependensi Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Repo source
COPY . .

# Cron job: setiap hari bursa 16:15 WIB. docker-compose service 'cron'
# akan mount crontab dari scripts/cron/arus_crontab ke /etc/cron.d/arus.
RUN chmod +x scripts/cron/arus_daily.sh

# Default: server web screener port 8787. Override dengan command cron / cli.
EXPOSE 8787
CMD ["python", "-m", "app.server"]
