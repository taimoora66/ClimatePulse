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
        gettext-base \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN python -m pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY . .

RUN python patch_streamlit_meta.py

RUN sed -i 's/\r$//' /app/start.sh /app/nginx.conf.template \
    && chmod +x /app/start.sh

EXPOSE 8080

CMD ["sh", "/app/start.sh"]