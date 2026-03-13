from flask import Flask, request, jsonify
import requests
import json
import os
from datetime import datetime

app = Flask(__name__)

# ========================================
# 简道云配置（已填好，无需修改）
# ========================================
JIANDAOYUN_API_KEY = os.environ.get("JIANDAOYUN_API_KEY", "ZDOh1mmoium1dUZy1IJRtDvSxMLJDeM3")
JIANDAOYUN_APP_ID  = os.environ.get("JIANDAOYUN_APP_ID",  "659d2050806aac7d76af53f5")
JIANDAOYUN_FORM_ID = os.environ.get("JIANDAOYUN_FORM_ID", "69b3af25e63532229a28f450")

JIANDAOYUN_URL = f"https://api.jiandaoyun.com/api/v5/app/{JIANDAOYUN_APP_ID}/entry/{JIANDAOYUN_FORM_ID}/data"

# ========================================
# 接收 SaleSmartly Webhook
# ========================================
@app.route("/webhook", methods=["POST"])
def receive_webhook():
    try:
        data = request.json
        print(f"[{datetime.now()}] 收到询盘数据:\n{json.dumps(data, ensure_ascii=False, indent=2)}")

        # 从 SaleSmartly 数据中提取字段
        customer_name    = data.get("visitor_name") or data.get("name") or ""
        whatsapp         = data.get("whatsapp") or data.get("phone") or data.get("visitor_phone") or ""
        email            = data.get("email") or data.get("visitor_email") or ""
        company_name     = data.get("company") or data.get("company_name") or ""
        company_website  = data.get("website") or data.get("company_website") or ""
        country          = data.get("country") or data.get("visitor_country") or ""
        city             = data.get("city") or data.get("visitor_city") or ""
        main_product     = data.get("product") or data.get("main_product") or ""
        source           = data.get("channel") or data.get("source") or "SaleSmartly"
        customer_type    = data.get("customer_type") or ""
        salesperson      = data.get("salesperson") or data.get("agent_name") or ""
        customer_segment = data.get("segment") or data.get("customer_segment") or ""
        follow_status    = data.get("status") or data.get("follow_status") or ""
        remark           = data.get("remark") or data.get("note") or data.get("message") or ""
        created_time     = data.get("created_at") or datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        success = write_to_jiandaoyun(
            customer_name, whatsapp, email, company_name, company_website,
            country, city, main_product, source, customer_type,
            salesperson, customer_segment, follow_status, remark, created_time
        )

        if success:
            return jsonify({"status": "ok", "message": "同步成功 ✅"}), 200
        else:
            return jsonify({"status": "error", "message": "写入简道云失败"}), 500

    except Exception as e:
        print(f"[错误] {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500


# ========================================
# 写入简道云（字段ID已按截图填好）
# ========================================
def write_to_jiandaoyun(
    customer_name, whatsapp, email, company_name, company_website,
    country, city, main_product, source, customer_type,
    salesperson, customer_segment, follow_status, remark, created_time
):
    headers = {
        "Authorization": f"Bearer {JIANDAOYUN_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "data": {
            "_widget_1711089179446": {"value": customer_name},       # 客户名字
            "_widget_1706178443484": {"value": whatsapp},            # 客户手机号(Whatsapp)
            "_widget_1706178443483": {"value": email},               # 客户邮箱
            "_widget_1706177627141": {"value": company_name},        # 公司名称
            "_widget_1706259112687": {"value": company_website},     # 公司网址
            "_widget_1711089179447": {"value": country},             # 客户国家
            "_widget_1706250922588": {"value": city},                # 客户城市
            "_widget_1706250922593": {"value": main_product},        # 主营产品
            "_widget_1706259707456": {"value": source},              # 线索来源
            "_widget_1706259112693": {"value": customer_type},       # 客户类型
            "_widget_1706178443481": {"value": salesperson},         # 业务名称
            "_widget_1706259112688": {"value": customer_segment},    # 客户分组
            "_widget_1748335923699": {"value": follow_status},       # 跟进状态
            "_widget_1748946748107": {"value": remark},              # 备注
        }
    }

    response = requests.post(JIANDAOYUN_URL, headers=headers, json=payload)
    print(f"[简道云响应] {response.status_code}: {response.text}")
    return response.status_code == 200


# ========================================
# 健康检查
# ========================================
@app.route("/", methods=["GET"])
def health_check():
    return jsonify({"status": "running", "message": "询盘同步服务正在运行 ✅"}), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
