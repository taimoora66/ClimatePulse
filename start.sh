#!/bin/sh
set -eu

STREAMLIT_PORT=8501

echo "Starting ORBIDENSE Streamlit upstream..."

python -m streamlit run app.py \
  --server.address=127.0.0.1 \
  --server.port=${STREAMLIT_PORT} \
  --server.headless=true \
  --browser.gatherUsageStats=false &

STREAMLIT_PID=$!

echo "Waiting for Streamlit health endpoint..."

if ! python - <<'PY'
import sys
import time
import urllib.request

url = "http://127.0.0.1:8501/_stcore/health"

for attempt in range(90):
    try:
        with urllib.request.urlopen(url, timeout=1.5) as response:
            if response.status == 200:
                print("Streamlit upstream is healthy.")
                sys.exit(0)
    except Exception:
        pass

    time.sleep(1)

print("ERROR: Streamlit did not become healthy within 90 seconds.", file=sys.stderr)
sys.exit(1)
PY
then
    kill "${STREAMLIT_PID}" 2>/dev/null || true
    exit 1
fi

echo "Starting SEO gateway on port 8080..."

exec nginx -c /app/nginx.conf -g 'daemon off;'
