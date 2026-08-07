#!/bin/bash
set -e

# نام ریجن (برای لاگ‌ها) — از Env یا پیش‌فرض
REGION_NAME="${REGION_NAME:-unknown}"

echo "🚀 Starting X-UI + nginx reverse proxy [region: $REGION_NAME]..."

# ── Bootstrap خودکار ─────────────────────────────────────
# فقط سرویس اول (BOOTSTRAP=1) سرویس‌های چند-ریجن را می‌سازد.
# سرویس‌هایی که bootstrap می‌سازد BOOTSTRAP=0 دارند → این بخش اجرا نمی‌شود
# (جلوگیری از حلقه‌ی بی‌نهایت).
if [ "${BOOTSTRAP:-0}" = "1" ]; then
    echo "🌍 Bootstrap mode: creating multi-region services..."
    python3 /app/bootstrap.py || echo "⚠️ bootstrap failed (continuing anyway)"
fi

# nginx همیشه روی پورت ثابت 3000 گوش می‌دهد
export NGINX_PORT=3000

cd /usr/local/x-ui

echo "🔧 Applying panel settings via x-ui CLI..."
./x-ui setting -port 2053 -webBasePath /managepanel/ || true

echo "🔧 Building nginx.conf for fixed port: $NGINX_PORT"
envsubst '${NGINX_PORT}' < /etc/nginx/nginx.conf.template > /etc/nginx/nginx.conf

echo "▶️  Starting x-ui in background..."
./x-ui &
X_UI_PID=$!

sleep 2

echo "▶️  Starting nginx in foreground on port $NGINX_PORT..."
nginx -t
exec nginx -g "daemon off;"
