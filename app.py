import requests
import hashlib
import time
import json
import os
from datetime import datetime
from flask import Flask, jsonify
import threading

app = Flask(__name__)

# ========================================
# 所有配置已填好，无需修改
# ========================================
SS_TOKEN      = "40f5ZdyDpUFE5Ws"
SS_PROJECT_ID = "f1n28qu"

JDY_API_KEY = "ZDOh1mmoium1dUZy1IJRtDvSxMLJDeM3"
JDY_APP_ID  = "659d2050806aac7d76af53f5"
JDY_FORM_ID = "69b3af25e63532229a28f450"

JDY_URL = f"https://api.jiandaoyun.com/api/v5/app/{JDY_APP_ID}/entry/{JDY_FORM_ID}/data"

# 每60秒同步一次
SYNC_INTERVAL = 60

# 记录上次同步时间
last_sync_time = int(time.time()) - SYNC_INTERVAL


# ========================================
# 生成 SaleSmartly 签名
# ========================================
def make_sign(params: dict) -> str:
    # 文档规则：Token 在最前面，后面参数按字典序排序，用 & 连接，最后整体 MD5
    sorted_keys = sorted(params.keys())
    params_str = "&".join(f"{k}={params[k]}" for k in sorted_keys)
    sign_str = SS_TOKEN + "&" + params_str
    print(f"[签名原文] {sign_str}")
    return hashlib.md5(sign_str.encode("utf-8")).hexdigest()


# ========================================
# 从 SaleSmartly 拉取新客户列表
# ========================================
def fetch_new_customers():
    global last_sync_time

    now = int(time.time())

    params = {
        "project_id": SS_PROJECT_ID,
        "page": "1",
        "page_size": "50",
        "start_time": str(last_sync_time),
        "end_time": str(now),
    }

    sign = make_sign(params)

    headers = {
        "external-sign": sign,
        "Content-Type": "application/json"
    }

    try:
        response = requests.get(
            "https://api.salesmartly.com/api/chat-user/get-page-list",
            params=params,
            headers=headers,
            timeout=10
        )
        data = response.json()
        print(f"[{datetime.now()}] SaleSmartly响应: {json.dumps(data, ensure_ascii=False)[:200]}")

        if data.get("code") == 0:
            customers = data.get("data", {}).get("list", [])
            last_sync_time = now
            return customers
        else:
            print(f"[错误] SaleSmartly返回异常: {data}")
            return []
    except Exception as e:
        print(f"[错误] 请求SaleSmartly失败: {e}")
        return []


# ========================================
# 写入简道云
# ========================================
def write_to_jiandaoyun(customer: dict):
    headers = {
        "Authorization": f"Bearer {JDY_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "data": {
            "_widget_1711089179446": {"value": customer.get("name") or customer.get("remark_name") or ""},
            "_widget_1706178443484": {"value": customer.get("phone") or ""},
            "_widget_1706178443483": {"value": customer.get("email") or ""},
            "_widget_1711089179447": {"value": customer.get("country") or ""},
            "_widget_1706250922588": {"value": customer.get("city") or ""},
            "_widget_1706259707456": {"value": customer.get("channel") or customer.get("channel_name") or ""},
            "_widget_1706178443481": {"value": customer.get("sys_user_name") or ""},
            "_widget_1748335923699": {"value": "新询盘"},
            "_widget_1748946748107": {"value": customer.get("remark") or customer.get("content") or ""},
        }
    }

    try:
        response = requests.post(JDY_URL, headers=headers, json=payload, timeout=10)
        if response.status_code == 200:
            print(f"  ✅ 写入成功: {customer.get('name') or customer.get('remark_name') or '未知客户'}")
            return True
        else:
            print(f"  ❌ 写入失败: {response.status_code} {response.text}")
            return False
    except Exception as e:
        print(f"  ❌ 写入异常: {e}")
        return False


# ========================================
# 定时同步主循环
# ========================================
def sync_loop():
    print(f"[{datetime.now()}] 🚀 同步服务启动，每 {SYNC_INTERVAL} 秒同步一次")
    while True:
        try:
            print(f"\n[{datetime.now()}] 开始同步...")
            customers = fetch_new_customers()

            if customers:
                print(f"  发现 {len(customers)} 条新客户，写入简道云...")
                success = 0
                for c in customers:
                    if write_to_jiandaoyun(c):
                        success += 1
                    time.sleep(0.3)
                print(f"  ✅ 本次同步完成：{success}/{len(customers)} 条成功")
            else:
                print(f"  暂无新客户")

        except Exception as e:
            print(f"[同步错误] {e}")

        time.sleep(SYNC_INTERVAL)


# ========================================
# 健康检查 & 手动触发
# ========================================
@app.route("/", methods=["GET"])
def health():
    return jsonify({
        "status": "running ✅",
        "sync_interval": f"每 {SYNC_INTERVAL} 秒同步一次",
        "last_sync": datetime.fromtimestamp(last_sync_time).strftime("%Y-%m-%d %H:%M:%S")
    })

@app.route("/sync-now", methods=["GET"])
def manual_sync():
    """手动立即触发一次同步"""
    customers = fetch_new_customers()
    count = 0
    for c in customers:
        if write_to_jiandaoyun(c):
            count += 1
        time.sleep(0.3)
    return jsonify({"status": "ok", "synced": count, "message": f"同步了 {count} 条数据"})


if __name__ == "__main__":
    t = threading.Thread(target=sync_loop, daemon=True)
    t.start()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
