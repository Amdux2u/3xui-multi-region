#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
3x-ui TCP Proxy + Hosts Setup
=============================
برای هر سرویس 3x-ui یک TCP Proxy روی Railway می‌سازد، آن را به یکی از دامنه‌های
خوب (لیست تأیید) می‌چرخاند، و روی پنل اصلی در بخش Host ها ثبت می‌کند.

استفاده:
    export RAILWAY_TOKEN="توکن_اکانت"
    export PROJECT_ID="..." ENV_ID="..."
    export PANELS='{"xui-nl": "https://...", "xui-sg": "https://..."}'
    export SERVICE_IDS='{"xui-nl": "svc-id-1", ...}'
    export MAIN_PANEL="xui-nl"
    export XUI_USERNAME="admin" XUI_PASSWORD="admin"
    python3 xui-tcp-proxy-setup.py
"""

import json
import os
import socket
import sys
import time
import urllib.request
import urllib.error

# ── تنظیمات ────────────────────────────────────────────
RAILWAY_URL = "https://backboard.railway.com/graphql/v2"
RAILWAY_TOKEN = os.environ.get("RAILWAY_TOKEN", "")
PROJECT_ID = os.environ.get("PROJECT_ID", "")
ENV_ID = os.environ.get("ENV_ID", "")
MAIN_PANEL = os.environ.get("MAIN_PANEL", "xui-nl")
XUI_USERNAME = os.environ.get("XUI_USERNAME", "admin")
XUI_PASSWORD = os.environ.get("XUI_PASSWORD", "admin")
TARGET_PORT = int(os.environ.get("TARGET_PORT", "443"))

# دامنه‌های خوب (لیست تأیید)
GOOD_DOMAINS = os.environ.get(
    "GOOD_DOMAINS",
    "monorail,nozomi,turntable,trolley,reseau,autorack,metro,hopper,kodama,interchange,switchyard,junction"
).split(",")
GOOD_DOMAINS = {d.strip().lower() for d in GOOD_DOMAINS if d.strip()}

# پنل‌ها و سرویس‌ها — JSON
PANELS = json.loads(os.environ.get("PANELS", "{}"))
SERVICE_IDS = json.loads(os.environ.get("SERVICE_IDS", "{}"))

MAX_TRIES = int(os.environ.get("MAX_TRIES", "40"))
COOLDOWN = float(os.environ.get("COOLDOWN", "5"))


# ══════════ Railway GraphQL ══════════
def gql(query, variables=None):
    body = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(RAILWAY_URL, data=body, headers={
        "Authorization": "Bearer " + RAILWAY_TOKEN,
        "Content-Type": "application/json",
        "User-Agent": "railway-cli/5.30.4",
    })
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def list_tcp_proxies(service_id):
    d = gql('query($e: String!, $s: String!){ tcpProxies(environmentId: $e, serviceId: $s) '
            '{ id domain proxyPort applicationPort syncStatus } }',
            {"e": ENV_ID, "s": service_id})
    return (d.get("data") or {}).get("tcpProxies", [])


def delete_proxy(proxy_id):
    d = gql('mutation($id: String!){ tcpProxyDelete(id: $id) }', {"id": proxy_id})
    return "errors" not in d


def create_proxy(service_id):
    d = gql('mutation($input: TCPProxyCreateInput!){ tcpProxyCreate(input: $input) '
            '{ id domain proxyPort applicationPort syncStatus } }',
            {"input": {"applicationPort": TARGET_PORT, "environmentId": ENV_ID, "serviceId": service_id}})
    if "errors" in d:
        return None
    return (d.get("data") or {}).get("tcpProxyCreate") or {}


def wait_active(service_id, timeout=240):
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        proxies = list_tcp_proxies(service_id)
        live = [p for p in proxies if p.get("syncStatus") == "ACTIVE"]
        if len(live) == 1:
            return live[0]
        if live:
            last = live[0]
        time.sleep(5)
    return last


def rotate_service(service_id):
    """حذف و ساخت تا رسیدن به دامنه خوب."""
    seen = set()
    for attempt in range(1, MAX_TRIES + 1):
        proxies = list_tcp_proxies(service_id)
        for p in proxies:
            dom = (p.get("domain") or "").rstrip(".")
            if dom.split(".")[0] not in GOOD_DOMAINS and p.get("syncStatus") not in ("DELETED", "DELETING"):
                delete_proxy(p["id"])
        time.sleep(max(COOLDOWN - 2, 3))
        created = create_proxy(service_id)
        if not created:
            time.sleep(COOLDOWN)
            continue
        domain = (created.get("domain") or "?").rstrip(".")
        seen.add(domain.split(".")[0])
        proxy = wait_active(service_id)
        if proxy:
            final_domain = (proxy.get("domain") or "").rstrip(".")
            if final_domain:
                seen.add(final_domain.split(".")[0])
                domain = final_domain
        base = domain.split(".")[0]
        if base in GOOD_DOMAINS:
            return proxy or created
        time.sleep(COOLDOWN)
    return None


# ══════════ 3x-ui API ══════════
def xui_req(base, path, method="GET", data=None, cookie=None, csrf=None, timeout=20):
    headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
    body = None
    if data is not None:
        body = json.dumps(data).encode()
        headers["Content-Type"] = "application/json"
    if cookie:
        headers["Cookie"] = cookie
    if csrf:
        headers["X-CSRF-Token"] = csrf
    r = urllib.request.Request(base + path, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            return resp.status, dict(resp.headers), resp.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read().decode()
    except Exception as e:
        return 0, {}, str(e)


def xui_login(base):
    resp = urllib.request.urlopen(urllib.request.Request(
        base + "/managepanel/", headers={"User-Agent": "Mozilla/5.0"}), timeout=15)
    cookie = resp.headers.get("Set-Cookie", "").split(";")[0]
    resp.close()
    _, _, body = xui_req(base, "/managepanel/csrf-token", cookie=cookie)
    csrf = json.loads(body).get("obj", "")
    status, hdrs, body = xui_req(base, "/managepanel/login", method="POST",
                                 data={"username": XUI_USERNAME, "password": XUI_PASSWORD},
                                 cookie=cookie, csrf=csrf)
    if status != 200:
        return None, None
    sess = hdrs.get("Set-Cookie", "").split(";")[0] or cookie
    _, _, body = xui_req(base, "/managepanel/csrf-token", cookie=sess)
    csrf = json.loads(body).get("obj", "")
    return sess, csrf


def xui_api(base, cookie, csrf, path, method="GET", data=None):
    status, _, body = xui_req(base, path, method=method, data=data, cookie=cookie, csrf=csrf)
    return status, body


def main():
    if not RAILWAY_TOKEN or not ENV_ID or not SERVICE_IDS:
        print("❌ RAILWAY_TOKEN / PROJECT_ID / ENV_ID / SERVICE_IDS لازم است!")
        return 2

    print("🌐 ساخت TCP Proxy + Hosts\n" + "=" * 50)

    # 1) ساخت TCP proxy برای هر سرویس
    tcp_results = {}
    for name, svc_id in SERVICE_IDS.items():
        print(f"\n[{name}] ساخت TCP proxy (هدف: پورت {TARGET_PORT})...")
        proxy = rotate_service(svc_id)
        if proxy:
            domain = (proxy.get("domain") or "").rstrip(".")
            port = proxy.get("proxyPort")
            tcp_results[name] = (domain, port)
            print(f"  ✅ {domain}:{port} → app:{proxy.get('applicationPort')}")
        else:
            print(f"  ❌ به دامنه خوب نرسید (بعد از {MAX_TRIES} تلاش)")
        time.sleep(2)

    if not tcp_results:
        print("\n❌ هیچ TCP proxy ساخته نشد")
        return 1

    # 2) لاگین به پنل اصلی
    main_base = PANELS.get(MAIN_PANEL, "")
    if not main_base:
        print("\n⚠️ PANELS تنظیم نشده — Host ها اضافه نمی‌شوند")
        return 0
    print(f"\n🔐 لاگین به پنل اصلی ({MAIN_PANEL})...")
    sess, csrf = xui_login(main_base)
    if not sess:
        print("❌ لاگین نشد")
        return 1

    # 3) پیدا کردن اینباند Reality (پورت 443)
    _, body = xui_api(main_base, sess, csrf, "/managepanel/panel/api/inbounds/list")
    inbounds = json.loads(body).get("obj", [])
    inbound_id = None
    for ib in inbounds:
        if isinstance(ib, dict) and ib.get("port") == 443:
            inbound_id = ib.get("id")
            break
    if not inbound_id:
        print("❌ اینباند پورت 443 پیدا نشد")
        return 1
    print(f"  📡 اینباند: id={inbound_id}")

    # 4) افزودن Host برای هر TCP proxy
    print("\n🖥 افزودن Host ها...")
    for name, (domain, port) in tcp_results.items():
        payload = {
            "inboundIds": [inbound_id],
            "remark": f"tcp-{name}",
            "hosts": [domain],
            "port": port,
            "security": "same",
            "tags": [name],
        }
        status, body = xui_api(main_base, sess, csrf, "/managepanel/panel/api/hosts/add",
                               method="POST", data=payload)
        ok = status == 200 and '"success":true' in body
        print(f"  {name}: {domain}:{port} → {'✅' if ok else '❌ ' + body[:100]}")
        time.sleep(1)

    print("\n🎉 تمام شد!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
