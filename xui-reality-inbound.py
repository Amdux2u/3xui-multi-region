#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
3x-ui Reality Inbound Creator
=============================
ساخت اینباند VLESS + TCP + Reality روی همه پنل‌ها.

مشخصات اینباند:
  - پورت: 443
  - پروتکل: vless
  - شبکه: tcp (raw)
  - امنیت: reality
  - Target: is1-ssl.mzstatic.com:443
  - SNI: is1-ssl.mzstatic.com
  - بقیه تنظیمات پیش‌فرض

هر پنل یک UUID متفاوت می‌گیرد.
"""

import base64
import json
import os
import sys
import time
import urllib.request
import urllib.error
import uuid

from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
from cryptography.hazmat.primitives import serialization

# ── تنظیمات ────────────────────────────────────────────
PANELS = {
    "xui-nl": "https://xui-nl-production-a29c.up.railway.app",
    "xui-sg": "https://xui-sg-production-434c.up.railway.app",
    "xui-us-va": "https://xui-us-va-production-3d26.up.railway.app",
    "xui-us-ca": "https://xui-us-ca-production-4c58.up.railway.app",
}
USERNAME = "admin"
PASSWORD = "admin"

PORT = 443
DEST = "is1-ssl.mzstatic.com:443"
SNI = "is1-ssl.mzstatic.com"
REMARK = "VLESS-Reality-443"


def gen_keypair():
    """تولید X25519 keypair برای Reality."""
    priv = X25519PrivateKey.generate()
    priv_b64 = base64.urlsafe_b64encode(priv.private_bytes(
        serialization.Encoding.Raw, serialization.PrivateFormat.Raw,
        serialization.NoEncryption())).decode().rstrip("=")
    pub_b64 = base64.urlsafe_b64encode(priv.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw)).decode().rstrip("=")
    return priv_b64, pub_b64


def gen_short_id():
    """شناسه کوتاه reality (8 کاراکتر hex)."""
    return os.urandom(4).hex()


def req(base, path, method="GET", data=None, cookie=None, csrf=None, timeout=20):
    url = base + path
    headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
    body = None
    if data is not None:
        body = json.dumps(data).encode()
        headers["Content-Type"] = "application/json"
    if cookie:
        headers["Cookie"] = cookie
    if csrf:
        headers["X-CSRF-Token"] = csrf
    r = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            return resp.status, dict(resp.headers), resp.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read().decode()
    except Exception as e:
        return 0, {}, str(e)


def login(base):
    resp = urllib.request.urlopen(urllib.request.Request(
        base + "/managepanel/", headers={"User-Agent": "Mozilla/5.0"}), timeout=15)
    cookie = resp.headers.get("Set-Cookie", "").split(";")[0]
    resp.close()
    status, _, body = req(base, "/managepanel/csrf-token", cookie=cookie)
    csrf = json.loads(body).get("obj", "")
    status, hdrs, body = req(base, "/managepanel/login", method="POST",
                             data={"username": USERNAME, "password": PASSWORD},
                             cookie=cookie, csrf=csrf)
    if status != 200:
        return None, None, f"لاگین ناموفق ({status}): {body[:120]}"
    sess = hdrs.get("Set-Cookie", "").split(";")[0] or cookie
    # CSRF تازه بعد از لاگین
    status, _, body = req(base, "/managepanel/csrf-token", cookie=sess)
    csrf = json.loads(body).get("obj", "")
    return sess, csrf, ""


def create_inbound(base, cookie, csrf):
    priv, pub = gen_keypair()
    short_id = gen_short_id()
    client_id = str(uuid.uuid4())

    inbound = {
        "enable": True,
        "remark": REMARK,
        "listen": "",
        "port": PORT,
        "protocol": "vless",
        "expiryTime": 0,
        "total": 0,
        "settings": {
            "clients": [{"id": client_id, "email": "amir"}],
            "decryption": "none",
            "fallbacks": []
        },
        "streamSettings": {
            "network": "tcp",
            "security": "reality",
            "realitySettings": {
                "show": False,
                "dest": DEST,
                "serverNames": [SNI],
                "privateKey": priv,
                "shortIds": [short_id],
                "settings": {
                    "publicKey": pub,
                    "fingerprint": "chrome",
                    "serverName": "",
                    "spiderX": ""
                },
                "xver": 0
            }
        },
        "sniffing": {"enabled": True, "destOverride": ["http", "tls"]}
    }

    status, _, body = req(base, "/managepanel/panel/api/inbounds/add",
                          method="POST", data=inbound, cookie=cookie, csrf=csrf)
    return status, body, client_id, pub, short_id


def main():
    print("🔐 ساخت اینباند Reality روی همه پنل‌ها\n" + "=" * 50)
    results = {}

    for name, base in PANELS.items():
        print(f"\n[{name}] لاگین...")
        sess, csrf, err = login(base)
        if not sess:
            print(f"  ❌ {err}")
            continue
        print(f"  ✅ لاگین موفق")

        print(f"  📡 ساخت اینباند VLESS+Reality :{PORT} → {DEST} ...")
        status, body, client_id, pub, short_id = create_inbound(base, sess, csrf)
        if status == 200 and '"success":true' in body:
            print(f"  ✅ اینباند ساخته شد!")
            print(f"  🆔 UUID: {client_id}")
            print(f"  🔑 PublicKey: {pub}")
            print(f"  🏷 ShortId: {short_id}")
            results[name] = {
                "uuid": client_id, "pub": pub, "short_id": short_id,
                "address": base.replace("https://", ""),
            }
        else:
            print(f"  ❌ خطا ({status}): {body[:200]}")
        time.sleep(1)

    print(f"\n{'=' * 50}\n📋 خلاصه:")
    for name, info in results.items():
        print(f"\n🔗 {name}:")
        print(f"   vless://{info['uuid']}@{info['address']}:{PORT}?encryption=none&security=reality&sni={SNI}&fp=chrome&pbk={info['pub']}&sid={info['short_id']}&type=tcp&headerType=none#VLESS-Reality-{name}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
