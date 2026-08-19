FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        nginx \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN python -m pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY . .

RUN python patch_streamlit_meta.py
RUN python patch_analytics_cookie.py

# Normalize Windows/BOM line endings before Linux execution.
RUN python -c "from pathlib import Path; \
files=[Path('/app/start.sh'),Path('/app/nginx.conf')]; \
[(p.write_bytes(p.read_text(encoding='utf-8-sig').replace('\r\n','\n').replace('\r','\n').encode('utf-8'))) for p in files]" \
    && chmod +x /app/start.sh

# Fail the image build immediately if nginx configuration is invalid.
RUN nginx -t -c /app/nginx.conf

EXPOSE 8080

CMD ["sh", "/app/start.sh"]