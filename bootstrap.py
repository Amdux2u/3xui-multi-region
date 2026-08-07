#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
3x-ui Multi-Region Bootstrap
============================
خود-راه‌انداز: وقتی این ریپو مستقیم روی Railway دیپلوی می‌شود، این اسکریپت
خودش ۴ سرویس (هلند/سنگاپور/ویرجینیا/کالیفرنیا) را با ریجن، دامنه (پورت 3000)
و ولوم می‌سازد — بدون نیاز به هیچ ابزار خارجی.

اجرا: خودکار توسط start.sh وقتی BOOTSTRAP=1 باشد.
نیازمندی‌ها (env روی سرویس اول):
    RAILWAY_TOKEN   توکن اکانت Railway (الزامی)
    REGION_NAME     نام ریجن این سرویس (مثلاً ams) — برای ست کردن ریجن خودش
    PROJECT_ID      (اختیاری) اگر خالی باشد، پروژه‌ی فعلی از env Railway پیدا می‌شود
"""

import json
import os
import sys
import urllib.request

TOKEN = os.environ.get("RAILWAY_TOKEN", "")
URL = "https://backboard.railway.com/graphql/v2"
REPO = os.environ.get("REPO", "Kolkolz/3xui-multi-region")
BRANCH = os.environ.get("BRANCH", "main")
TARGET_PORT = int(os.environ.get("TARGET_PORT", "3000"))
MOUNT_PATH = os.environ.get("VOLUME_PATH", "/etc/x-ui")

# (نام سرویس, ریجن)
SERVICES = [
    ("xui-nl",    "ams"),
    ("xui-sg",    "sin"),
    ("xui-us-va", "iad"),
    ("xui-us-ca", "sfo"),
]


def gql(query, variables=None):
    body = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(URL, data=body, headers={
        "Authorization": "Bearer " + TOKEN,
        "Content-Type": "application/json",
        "User-Agent": "railway-cli/5.30.4",
    })
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def log(msg):
    print(f"[bootstrap] {msg}", flush=True)


def find_project():
    """پروژه‌ی فعلی را از متغیرهای Railway پیدا می‌کند."""
    pid = os.environ.get("PROJECT_ID", "")
    if pid:
        return pid
    # Railway پروژه را در RAILWAY_PROJECT_NAME یا از روی workspace پیدا می‌کند
    d = gql("{ me { workspaces { id } } }")
    wid = d["data"]["me"]["workspaces"][0]["id"]
    proj_name = os.environ.get("RAILWAY_PROJECT_NAME", "")
    d2 = gql('query($wid: String!){ projects(workspaceId: $wid) { edges { node { id name } } } }',
             {"wid": wid})
    for e in d2["data"]["projects"]["edges"]:
        if proj_name and e["node"]["name"] == proj_name:
            return e["node"]["id"]
    # اولین پروژه‌ای که سرویس فعلی توش است را پیدا کن (از env SERVICE)
    return None


def find_env(pid):
    d = gql('query($pid: String!){ environments(projectId: $pid) { edges { node { id name } } } }',
            {"pid": pid})
    envs = d["data"]["environments"]["edges"]
    for e in envs:
        if e["node"]["name"] == "production":
            return e["node"]["id"]
    return envs[0]["node"]["id"] if envs else None


def list_services(pid):
    d = gql('query($pid: String!){ project(id: $pid) { services { edges { node { id name } } } } }',
            {"pid": pid})
    return {e["node"]["name"]: e["node"]["id"]
            for e in d["data"]["project"]["services"]["edges"]}


def create_service(pid, name, region):
    """ساخت سرویس با BOOTSTRAP=0 تا دوباره bootstrap نشود."""
    d = gql(
        'mutation($input: ServiceCreateInput!){ serviceCreate(input: $input) { id name } }',
        {"input": {
            "name": name,
            "projectId": pid,
            "source": {"repo": REPO},
            "branch": BRANCH,
            "variables": {  # EnvironmentVariables = JSON object (نه لیست!)
                "REGION_NAME": region,
                "BOOTSTRAP": "0",
            },
        }})
    if "errors" in d:
        msg = d["errors"][0]["message"]
        if "limit exceeded" in msg.lower() or "Free plan" in msg:
            log(f"⚠️ {name}: سقف پلن پر است — {msg}")
        else:
            log(f"⚠️ {name}: {msg}")
        return None
    return d["data"]["serviceCreate"]["id"]


def set_region(env_id, svc_id, region):
    d = gql(
        'mutation($e: String!, $s: String!, $input: ServiceInstanceUpdateInput!){ '
        'serviceInstanceUpdate(environmentId: $e, serviceId: $s, input: $input) { id } }',
        {"e": env_id, "s": svc_id, "input": {"region": region}})
    return "errors" not in d


def create_domain(env_id, svc_id):
    d = gql(
        'mutation($input: ServiceDomainCreateInput!){ serviceDomainCreate(input: $input) { id domain } }',
        {"input": {"environmentId": env_id, "serviceId": svc_id, "targetPort": TARGET_PORT}})
    if "errors" in d:
        log(f"⚠️ دامنه: {d['errors'][0]['message'][:80]}")
        return None
    return d["data"]["serviceDomainCreate"]["domain"]


def create_volume(env_id, pid, svc_id, region):
    d = gql(
        'mutation($input: VolumeCreateInput!){ volumeCreate(input: $input) { id } }',
        {"input": {
            "environmentId": env_id,
            "projectId": pid,
            "serviceId": svc_id,
            "region": region,
            "mountPath": MOUNT_PATH,
        }})
    if "errors" in d:
        log(f"⚠️ ولوم: {d['errors'][0]['message'][:80]}")
        return None
    return d["data"]["volumeCreate"]["id"]


def main():
    if not TOKEN:
        log("❌ RAILWAY_TOKEN ست نشده — bootstrap غیرفعال است")
        return 0

    pid = find_project()
    if not pid:
        log("❌ پروژه پیدا نشد — bootstrap غیرفعال است")
        return 0

    env_id = find_env(pid)
    if not env_id:
        log("❌ environment پیدا نشد")
        return 0

    log(f"پروژه: {pid} | env: {env_id}")
    existing = list_services(pid)
    log(f"سرویس‌های موجود: {list(existing.keys())}")

    for name, region in SERVICES:
        if name in existing:
            log(f"⏭ {name} از قبل هست — رد شد")
            continue
        log(f"🚀 ساخت {name} (ریجن {region})...")
        svc_id = create_service(pid, name, region)
        if not svc_id:
            continue
        if set_region(env_id, svc_id, region):
            log(f"  ✅ ریجن {region}")
        domain = create_domain(env_id, svc_id)
        if domain:
            log(f"  ✅ دامنه: https://{domain} (پورت {TARGET_PORT})")
        vol = create_volume(env_id, pid, svc_id, region)
        if vol:
            log(f"  ✅ ولوم: {vol} → {MOUNT_PATH}")
        else:
            log("  ⚠️ ولوم ساخته نشد")

    # ریجن سرویس خودش را هم هماهنگ کن
    self_region = os.environ.get("REGION_NAME", "")
    if self_region and env_id:
        set_region(env_id, os.environ.get("RAILWAY_SERVICE_ID", ""), self_region)

    log("✅ bootstrap تمام شد")
    return 0


if __name__ == "__main__":
    sys.exit(main())
