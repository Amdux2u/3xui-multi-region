# 🌍 3x-ui Multi-Region on Railway

دیپلوی **3x-ui v3.6.0** + nginx reverse proxy روی Railway — **خود-راه‌انداز**: فقط یک‌بار `Deploy from GitHub` بزنید و خودش ۴ سرویس در ۴ ریجن (هلند، سنگاپور، ویرجینیا، کالیفرنیا) + دامنه + ولوم می‌سازد.

---

## ⚡ شروع فوق سریع

1. **New Project → Deploy from GitHub repo** → همین ریپو را انتخاب کنید
2. در سرویس اول این متغیرها را ست کنید (Settings → Variables):
   - `RAILWAY_TOKEN` ← توکن اکانت Railway (Settings → Tokens)
   - `BOOTSTRAP=1` ← فعال‌سازی خود-راه‌انداز
   - `REGION_NAME` ← ریجن این سرویس (اختیاری، مثلاً `ams`)
3. Deploy تمام شود — **خودش بقیه را می‌سازد**:
   - `xui-nl` (🇳🇱 آمستردام) + دامنه + ولوم
   - `xui-sg` (🇸🇬 سنگاپور) + دامنه + ولوم
   - `xui-us-va` (🇺🇸 ویرجینیا) + دامنه + ولوم
   - `xui-us-ca` (🇺🇸 سان‌فرانسیسکو) + دامنه + ولوم

> هر سرویس جدید با `BOOTSTRAP=0` ساخته می‌شود تا دوباره bootstrap نشود (جلوگیری از حلقه‌ی بی‌نهایت).

---

## 🗺 معماری چند ریجن

| سرویس | ریجن Railway | کد ریجن | موقعیت |
|---|---|---|---|
| `xui-nl` | Amsterdam | `ams` | 🇳🇱 هلند |
| `xui-sg` | Singapore | `sin` | 🇸🇬 سنگاپور |
| `xui-us-va` | Virginia | `iad` | 🇺🇸 آمریکا (شرق) |
| `xui-us-ca` | San Francisco | `sfo` | 🇺🇸 آمریکا (غرب - کالیفرنیا) |

هر سرویس یک دامنه مستقل `.up.railway.app` با **پورت 3000** می‌گیرد — کلاینت به نزدیک‌ترین ریجن وصل می‌شود.

---

## 🚀 دیپلوی دستی (بدون bootstrap)

### روش ۱ — داشبورد Railway
1. **New Project → Deploy from GitHub repo** → این ریپو را انتخاب کنید
2. برای هر ریجن: **دوباره همان ریپو را اضافه کنید** (Add Service → Deploy from GitHub → همین ریپو)
3. هر سرویس را نام‌گذاری کنید (مثلاً `xui-nl`, `xui-sg`, ...)
4. در هر سرویس: **Settings → Networking → Generate Domain** (فقط یک دامنه)
5. در هر سرویس: **Settings → Region** → ریجن مورد نظر را انتخاب کنید
6. متغیر `REGION_NAME` را ست کنید (اختیاری، فقط برای لاگ)

### روش ۲ — API (خودکار)
با اسکریپت `deploy.py` همه‌چیز خودکار انجام می‌شود: ساخت سرویس + تنظیم ریجن + ساخت دامنه با پورت 3000 + ولوم:

```bash
export RAILWAY_TOKEN="توکن_اکانت"
python3 deploy.py            # همه ۴ سرویس
python3 deploy.py xui-nl     # فقط یکی
```

| متغیر | پیش‌فرض | توضیح |
|---|---|---|
| `WORKSPACE_ID` | اولین workspace | شناسه workspace |
| `PROJECT_ID` | خودکار (پیدا/ساخت) | شناسه پروژه |
| `REPO` | `Kolkolz/3xui-multi-region` | ریپوی سورس |
| `BRANCH` | `main` | برنچ |
| `TARGET_PORT` | `3000` | پورت دامنه |
| `VOLUME_PATH` | `/etc/x-ui` | مسیر مونت ولوم |

> هر سرویس بعد از ساخت، **دامنه‌ی خودکار** با `targetPort=3000` می‌گیرد (همان پورتی که nginx گوش می‌دهد) و **یک Volume** روی `/etc/x-ui` مونت می‌شود تا تنظیمات پنل بعد از هر ری‌دیپلوی پاک نشود.

---

## 🖥 اولین ورود به پنل

```
https://دامنه.up.railway.app/managepanel/
```
یوزرنیم/پسورد پیش‌فرض: `admin/admin` — **فوراً تغییر دهید!** ⚠️

---

## 🔧 ساخت Inbound

| فیلد | مقدار |
|---|---|
| Protocol | VLESS |
| Listen Port | **8080** (با nginx هماهنگ است — تغییر ندهید) |
| Listen IP | خالی یا `0.0.0.0` |
| Network | ws |
| Security | none |
| Path | هر مسیر، مثلاً `/cdn` |

> اینباندهای اضافه: پورت‌های `8081`-`8089` با path های `/in1`-`/in9` در nginx از قبل تعریف شده‌اند.

### لینک کلاینت
```
vless://UUID@دامنه.up.railway.app:443?encryption=none&security=tls&sni=دامنه&fp=chrome&type=ws&host=دامنه&path=%2Fcdn#MyConfig
```

---

## 💾 ذخیره تنظیمات (مهم!)

دیتابیس پنل در `/etc/x-ui` است — روی فایل‌سیستم موقت کانتینر! برای اینکه بعد از هر Redeploy تنظیمات پاک نشود:

1. در هر سرویس: **Settings → Volumes → Add Volume**
2. مسیر: `/etc/x-ui` (حجم حداقل 1GB — دیتابیس خیلی کوچک است، 1GB کافی است)

---

## 🧪 تست سریع

```bash
# اینباند (باید Bad Request بدهد = به Xray رسیده)
curl https://دامنه.up.railway.app/cdn

# پنل
curl -I https://دامنه.up.railway.app/managepanel/
```

---

## 📄 فایل‌های ریپو

| فایل | توضیح |
|---|---|
| `Dockerfile` | alpine:3.20 + 3x-ui v3.6.0 + nginx |
| `nginx.conf.template` | reverse proxy: پنل (2053) + ساب (2096) + اینباند (8080-8089) |
| `start.sh` | راه‌اندازی x-ui + ساخت nginx.conf با `$PORT` |
| `deploy.py` | ساخت خودکار سرویس‌ها (ریجن + دامنه + ولوم) از بیرون با API |
| `bootstrap.py` | خود-راه‌انداز داخل کانتینر (فقط با `BOOTSTRAP=1`) |
| `xui-node-connector.py` | اتصال نودهای چند-ریجن به پنل مرکزی |
| `xui-reality-inbound.py` | ساخت اینباند VLESS+Reality روی همه پنل‌ها |
| `xui-tcp-proxy-setup.py` | TCP proxy + روتیت به دامنه خوب + Host ها |
| `run_all.sh` | **راه‌اندازی یک‌کلیک — همه مراحل پشت سر هم** |
| `SETUP_NOTES.md` | **نکات کامل راه‌اندازی — حتماً بخوانید!** |

> 📖 قبل از هر کاری [`SETUP_NOTES.md`](SETUP_NOTES.md) را بخوان — شامل همه‌ی اشتباهات رایج و فیکس‌های آن‌هاست.

*ساخته‌شده توسط Hermes برای پروژه Railway امیر*
