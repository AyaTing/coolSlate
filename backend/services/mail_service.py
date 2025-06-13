import resend
import os
from urllib.parse import quote
from datetime import datetime, date, time
from dotenv import load_dotenv

load_dotenv()
resend.api_key = os.getenv("RESEND_API_KEY")


def send_scheduling_success_email(order_data: dict):
    try:

        scheduled_date = order_data["scheduled_date"].strftime("%Y年%m月%d日")
        scheduled_time = order_data["scheduled_time"].strftime("%H:%M")
        estimated_end_time = order_data["estimated_end_time"].strftime("%H:%M")

        start_datetime = datetime.combine(
            order_data["scheduled_date"], order_data["scheduled_time"]
        )
        end_datetime = datetime.combine(
            order_data["scheduled_date"], order_data["estimated_end_time"]
        )

        start_str = start_datetime.strftime("%Y%m%dT%H%M%S")
        end_str = end_datetime.strftime("%Y%m%dT%H%M%S")

        service_type_map = {
            "INSTALLATION": "新機安裝",
            "MAINTENANCE": "冷氣保養",
            "REPAIR": "冷氣維修",
        }
        service_type = service_type_map.get(
            order_data["service_type"], order_data["service_type"]
        )

        event_title = f"Cool Slate - {service_type}服務"
        event_details = f"""
訂單編號：{order_data["order_number"]}
服務類型：{service_type}
服務地址：{order_data["location_address"]}
聯絡人：{order_data.get("contact_name")}
聯絡電話：{order_data.get("contact_phone")}
        """.strip()
        calendar_url = f"https://calendar.google.com/calendar/render?action=TEMPLATE&text={quote(event_title)}&dates={start_str}/{end_str}&details={quote(event_details)}&location={quote(order_data['location_address'])}"
        html_content = f"""
<div
  style="
    font-family: Arial, sans-serif;
    max-width: 600px;
    margin: 0 auto;
    padding: 20px;
  "
>
  <div style="display: flex; flex-direction: column">
    <div style="background: #395fd2; padding: 30px; border-radius: 0 0 8px 8px">
          <div style="width: 60%; margin: 0 auto; background: #fff">
        <img
          src="https://cool-slate.ayating.workers.dev/assets/logo_1-ChZ3hRQB.png"
          style="width: 100%; height: 150px; object-fit: cover; display: block"
        />
      </div>
        <h1 style="text-align: center; margin: 5px auto 10px; color: #fff">
          冷氣服務排程確認通知
        </h1>
        <div style="display: flex; justify-content: space-between">
      <h2 style="color: #fff">{order_data.get("user_name", "客戶")}，您好</h2>
      <a
          href="{calendar_url}"
          style="
            display: block;
            background: #d8f999;
            color: black;
            padding: 12px 24px;
            text-decoration: none;
            border-radius: 6px;
            font-weight: bold;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
          "
        >
          📅 加入 Google 行事曆
        </a>
      </div>
      <div
        style="
          background: white;
          padding: 20px;
          border-radius: 8px;
          margin: 20px 0;
        "
      >
        <h3 style="color: #4caf50; margin-top: 0">📋 訂單資訊</h3>
        <p><strong>訂單編號：</strong>{order_data["order_number"]}</p>
        <p><strong>服務類型：</strong>{service_type}</p>
        <p><strong>服務地址：</strong>{order_data["location_address"]}</p>
        <p><strong>服務金額：</strong>NT$ {order_data["total_amount"]:,}</p>
      </div>
      <div
        style="
          background: white;
          padding: 20px;
          border-radius: 8px;
          margin: 20px 0;
        "
      >
        <h3 style="color: #2196f3; margin-top: 0">🗓️ 服務時間</h3>
        <p>
          <strong>服務日期：</strong
          ><span style="color: #e74c3c; font-weight: bold"
            >{scheduled_date}</span
          >
        </p>
        <p>
          <strong>服務時間：</strong
          ><span style="color: #e74c3c; font-weight: bold"
            >{scheduled_time}</span
          >
        </p>
        <p><strong>預估結束：</strong>{estimated_end_time}</p>
        <p><strong>聯絡人：</strong>{order_data.get("contact_name")}</p>
        <p><strong>聯絡電話：</strong>{order_data.get("contact_phone")}</p>
      </div>
      <div
        style="
          background: #fff3cd;
          padding: 15px;
          border-radius: 8px;
          margin: 10px 0;
          border: 1px solid #ffeaa7;
        "
      >
        <h4 style="color: #856404; margin: 0px 0px 8px 0px">⚠️ 重要提醒</h4>
        <ul style="color: #856404; margin: 0; padding-left: 20px">
          <li>服務當天請保持聯絡電話暢通。</li>
          <li>請確保服務時間有人在現場。</li>
          <li>如需變更預約，請提前 24 小時電話聯繫我們。</li>
          <li>若需取消預約，請於預約日三日前於會員中心進行取消申請。</li>
        </ul>
      </div>
      <div style="text-align: center; margin-top: 30px">
        <p style="color: #fff">如有任何問題，請隨時聯繫我們</p>
        <p style="color: #fff">
          客服電話：(02) 1234-5678 | 營業時間：08:00-17:00
        </p>
      </div>
    </div>
  </div>
</div>
        """
        params = {
            "from": "Cool Slate 冷氣服務預約 <noreply@mail.ayating.lol>",
            "to": [order_data["user_email"]],
            "subject": f"【Cool Slate】✅ 排程確認 - {service_type}服務已安排",
            "html": html_content,
        }
        result = resend.Emails.send(params)
        if result and "id" in result:
            print(
                f"排程成功郵件已發送給 {order_data["user_email"]}, 郵件ID: {result["id"]}"
            )
            return {"success": True, "email_id": result["id"]}
        else:
            print(f"訂單 {order_data["order_id"]}郵件發送失敗")
            return {"success": False, "error": "無效的回應格式"}
    except Exception as e:
        print(f"未知錯誤: {e}")
        return {"success": False, "error": f"未知錯誤: {e}"}
