#!/bin/bash
# ============================================================
# 3x-ui Multi-Region — One-Click Setup
# ============================================================
# کل فرایند راه‌اندازی 4 سرویس 3x-ui چند-ریجن روی Railway را یکجا اجرا می‌کند:
#
#   1) deploy.py               → ساخت سرویس‌ها (ریجن + دامنه + ولوم)
#   2) xui-node-connector.py   → اتصال نودها به پنل مرکزی
#   3) xui-reality-inbound.py  → ساخت اینباند VLESS+Reality روی همه پنل‌ها
#   4) xui-tcp-proxy-setup.py  → TCP proxy + روتیت به دامنه خوب + Host ها
#
# استفاده:
#   export RAILWAY_TOKEN="توکن_اکانت"
#   export WORKSPACE_ID="..." PROJECT_ID="..." ENV_ID="..."
#   export PANELS='{"xui-nl": "https://...", ...}'
#   export SERVICE_IDS='{"xui-nl": "svc-1", ...}'
#   bash run_all.sh
#
# متغیرهای اختیاری:
#   XUI_USERNAME / XUI_PASSWORD (پیش‌فرض admin/admin)
#   TARGET_DOMAIN_REALITY (پیش‌فرض is1-ssl.mzstatic.com:443)
#   MAIN_PANEL (پیش‌فرض xui-nl)
# ============================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
START_TIME=$(date +%s)

echo "=============================================="
echo "  🚂 3x-ui Multi-Region — One-Click Setup"
echo "=============================================="
echo ""

# ── پیش‌نیازها ────────────────────────────────────────
if [ -z "$RAILWAY_TOKEN" ]; then
    echo "❌ RAILWAY_TOKEN را ست کن!"
    exit 1
fi

step() {
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  [$1/4] $2"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# ── 1) ساخت سرویس‌ها ──────────────────────────────────
step 1 "ساخت سرویس‌ها (ریجن + دامنه + ولوم)"
python3 "$SCRIPT_DIR/deploy.py" || echo "⚠️ deploy.py خطا داد (شاید سرویس‌ها از قبل هستن)"

# ── 2) اتصال نودها ────────────────────────────────────
step 2 "اتصال نودها به پنل مرکزی"
python3 "$SCRIPT_DIR/xui-node-connector.py" || echo "⚠️ اتصال نودها خطا داد"

# ── 3) ساخت اینباند Reality ───────────────────────────
step 3 "ساخت اینباند VLESS+Reality"
python3 "$SCRIPT_DIR/xui-reality-inbound.py" || echo "⚠️ ساخت اینباند خطا داد"

# ── 4) TCP proxy + Host ها ────────────────────────────
step 4 "TCP proxy + روتیت + Host ها"
python3 "$SCRIPT_DIR/xui-tcp-proxy-setup.py" || echo "⚠️ TCP proxy خطا داد"

END_TIME=$(date +%s)
echo ""
echo "=============================================="
echo "  ✅ تمام شد! (مدت: $((END_TIME - START_TIME)) ثانیه)"
echo "=============================================="
echo ""
echo "📋 لینک پنل اصلی:"
echo "   $MAIN_PANEL_BASE/managepanel/  (admin/admin)"
echo ""
echo "⚠️ فراموش نکن: رمز پیش‌فرض پنل را عوض کن!"
