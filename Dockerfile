FROM python:3.11-slim

# TZ Asia/Jakarta (WIB) + curl untuk healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
        tzdata \
        curl \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

ENV TZ=Asia/Jakarta
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Default: web screener. Override dengan command lain (`python scripts/fetch_sectors_prices.py`, dll).
EXPOSE 8787
CMD ["python", "-m", "app.server"]
