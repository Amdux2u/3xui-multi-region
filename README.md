# 🌍 3x-ui Multi-Region on Railway

دیپلوی **3x-ui v3.6.0** + nginx reverse proxy روی Railway — آماده برای اجرای **چند نمونه در ریجن‌های مختلف** (هلند، سنگاپور، آمریکا و...) از یک ریپو.

> هر نمونه یک سرویس جدا در Railway است که از همین ریپو دیپلوی می‌شود، فقط متغیر `REGION_NAME` و ریجن سرور فرق می‌کند.

---

## 🗺 معماری چند ریجن

| سرویس | ریجن Railway | کد ریجن | موقعیت |
|---|---|---|---|
| `xui-nl` | Amsterdam | `ams` | 🇳🇱 هلند |
| `xui-sg` | Singapore | `sin` | 🇸🇬 سنگاپور |
| `xui-us-va` | Virginia | `iad` | 🇺🇸 آمریکا (شرق) |
| `xui-us-ca` | San Francisco | `sfo` | 🇺🇸 آمریکا (غرب - کالیفرنیا) |

هر سرویس یک دامنه مستقل `.up.railway.app` می‌گیرد — کلاینت به نزدیک‌ترین ریجن وصل می‌شود.

---

## 🚀 دیپلوی

### روش ۱ — داشبورد Railway
1. **New Project → Deploy from GitHub repo** → این ریپو را انتخاب کنید
2. برای هر ریجن: **دوباره همان ریپو را اضافه کنید** (Add Service → Deploy from GitHub → همین ریپو)
3. هر سرویس را نام‌گذاری کنید (مثلاً `xui-nl`, `xui-sg`, ...)
4. در هر سرویس: **Settings → Networking → Generate Domain** (فقط یک دامنه)
5. در هر سرویس: **Settings → Region** → ریجن مورد نظر را انتخاب کنید
6. متغیر `REGION_NAME` را ست کنید (اختیاری، فقط برای لاگ)

### روش ۲ — API (خودکار)
این کار را می‌توان با Railway GraphQL API هم انجام داد:
```
serviceCreate(input: { name: "xui-nl", projectId: "...", source: { repo: "Kolkolz/3xui-multi-region" }, branch: "main" })
serviceInstanceUpdate(environmentId, input: { region: "ams" }, serviceId)
```

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

## 📄 فایل‌ها

| فایل | توضیح |
|---|---|
| `Dockerfile` | alpine:3.20 + 3x-ui v3.6.0 + nginx |
| `nginx.conf.template` | reverse proxy: پنل (2053) + ساب (2096) + اینباند (8080-8089) |
| `start.sh` | راه‌اندازی x-ui + ساخت nginx.conf با `$PORT` |

*ساخته‌شده توسط Hermes برای پروژه Railway امیر*
