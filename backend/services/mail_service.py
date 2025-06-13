import resend
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
resend.api_key = os.getenv("RESEND_API_KEY")


def send_scheduling_success_email(order_data: dict):
    try:
        scheduled_date = order_data["scheduled_date"].strftime("%Y年%m月%d日")
        scheduled_time = order_data["scheduled_time"].strftime("%H:%M")
        estimated_end_time = order_data["estimated_end_time"].strftime("%H:%M")
        service_type_map = {
        "INSTALLATION": "新機安裝",
        "MAINTENANCE": "冷氣保養",
        "REPAIR": "冷氣維修",
    }
        service_type = service_type_map.get(
        order_data["service_type"], order_data["service_type"]
    )
        html_content = f"""
<div
  style="
    font-family: Arial, sans-serif;
    max-width: 600px;
    margin: 0 auto;
    padding: 20px;
  "
>
  <div style="width: 60%; margin: 0 auto">
    <img
      src="https://cool-slate.ayating.workers.dev/assets/logo_1-ChZ3hRQB.png"
      style="width: 100%; height: 150px; object-fit: cover; display: block"
    />
  </div>
  <div style="display: flex; flex-direction: column">
    <div style="background: #395fd2; padding: 30px; border-radius: 0 0 8px 8px">
          <div style="text-align: center">
        <h1 style="margin: 5px auto 10px; color: #fff">
          ✅ 冷氣服務排程確認通知
        </h1>
      </div>
      <h2 style="color: #fff">{order_data.get("user_name", "客戶")}，您好</h2>
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
            "from": "Cool Slate 冷氣服務 <noreply@mail.ayating.lol>",
            "to": [order_data["user_email"]],
            "subject": f"✅ 排程確認 - {service_type}服務已安排",
            "html": html_content,
        }
        result = resend.Emails.send(params)
        if result["success"]:   
          print(f"排程成功郵件已發送給 {order_data['user_email']}")
          return {"success": True}
        else:
          print(f"郵件發送失敗: {result.get('error', '未知錯誤')}")
          return {"success": False, "error": result.get('error')}
    except resend.ResendError as resend_error:
        print(f"Resend API 錯誤: {resend_error}")
        return {"success": False, "error": f"Resend API 錯誤: {resend_error}"}
    except Exception as e:
        print(f"未知錯誤: {e}")
        return {"success": False, "error": f"未知錯誤: {e}"}
