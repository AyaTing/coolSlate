from fastapi import HTTPException
import stripe
import os
from models.payment_model import (
    PaymentStatusResponse,
    PaymentStatus,
    CheckoutSessionResponse
)
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

TAIPEI_TZ = ZoneInfo("Asia/Taipei")
load_dotenv()

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY")

async def create_checkout_session(order_id: int, db):
    try:
        select_query = "SELECT o.*, st.name as service_type FROM orders o   JOIN service_types st ON o.service_type_id = st.id WHERE o.id = $1"
        order = await db.fetchrow( select_query, order_id,)    
        if not order:
            raise HTTPException(status_code=404, detail="訂單不存在")
        if order["status"] != "pending":
            raise HTTPException(status_code=400, detail="訂單狀態錯誤，無法付款")    
        if order["payment_status"] == "paid":
            raise HTTPException(status_code=400, detail="訂單已完成付款")
        if order["checkout_session_id"]:
            try:
                existing_session = stripe.checkout.Session.retrieve(order["checkout_session_id"])
                if existing_session.status == 'open':
                    return CheckoutSessionResponse(
                        session_id=existing_session.id,
                        session_url=existing_session.url,
                        order_id=order_id,
                        expires_at=datetime.fromtimestamp(existing_session.expires_at, tz=TAIPEI_TZ)
                    )
            except stripe.error.StripeError:
                print("查詢舊有 Checkout Session 出現錯誤")

        description_parts = [f'訂單編號：{order["order_number"]}']
        if order["service_type"] == "INSTALLATION" and order.get("equipment_details"):
            import json
            equipment_list = json.loads(order["equipment_details"])
            description_parts.append("設備清單：")
            for item in equipment_list:
                description_parts.append(f"• {item['name']} ({item['model']}) x{item['quantity']}")
        elif order["service_type"] in ["MAINTENANCE", "REPAIR"] and order.get("unit_count"):
            description_parts.append(f"服務台數：{order["unit_count"]} 台")
        if order.get("location_address"):
            description_parts.append(f"服務地址：{order["location_address"]}")
        if order.get("notes"):
            description_parts.append(f"備註：{order['notes']}")
        description_text = "\n".join(description_parts)

        checkout_session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": "twd",
                    "product_data": {
                        "name": f"冷氣服務 - {order["service_type"]}",
                        "description": description_text,
                    },
                    "unit_amount": order["total_amount"] * 100,
                },
                "quantity": 1,
            }],
            mode="payment",
            success_url=f"https://cool-slate.ayating.workers.dev/payment/success?order_id={order_id}",
            cancel_url=f"https://cool-slate.ayating.workers.dev/payment/cancel?order_id={order_id}",
            metadata={
                "order_id": str(order_id),
                "order_number": order["order_number"],
                "service_type": order["service_type"],
                "user_email": order["user_email"]
            },
            customer_email=order['user_email'],
            expires_at=int((datetime.now(TAIPEI_TZ) + timedelta(hours=1)).timestamp()),
        )
        
        update_query = "UPDATE orders SET checkout_session_id = $1, updated_at = NOW() WHERE id = $2"
        await db.execute(update_query, checkout_session.id, order_id)
        print(f"成功創建訂單 {order["order_number"]} 的 Checkout Session: {checkout_session.id}")
        return CheckoutSessionResponse(
            session_id=checkout_session.id,
            session_url=checkout_session.url,
            order_id=order_id,
            expires_at=datetime.fromtimestamp(checkout_session.expires_at, tz=TAIPEI_TZ)
        )
    except stripe.error.StripeError as e:
        print(f"Stripe 錯誤: {str(e)}")
        raise HTTPException(status_code=400, detail=f"創建付款頁面失敗: {str(e)}")
    except Exception as e:
        print(f"創建 Checkout Session 時發生錯誤: {str(e)}")
        raise HTTPException(status_code=500, detail="付款服務暫時無法使用")

async def get_payment_status(order_id: int, db):
    try:
        select_query = "SELECT o.*, st.name as service_type FROM orders o   JOIN service_types st ON o.service_type_id = st.id WHERE o.id = $1"
        order = await db.fetchrow(select_query, order_id)            
        if not order:
            print("訂單不存在")
            raise HTTPException(status_code=404, detail="訂單不存在")
        return PaymentStatusResponse(
            order_id=order_id,
            order_number=order["order_number"],
            payment_status=PaymentStatus(order["payment_status"]),
            order_status=order["status"],
            total_amount=order["total_amount"],
            created_at=order["created_at"],
            updated_at=order["updated_at"]
        )
    except Exception as e:
        print(f"出現預期外錯誤，無法確認：{e}")
        raise HTTPException(status_code=500, detail="出現預期外錯誤，無法確認")

async def handle_webhook(payload: bytes, sig_header: str, db):
        try:
            event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
        except ValueError:
            print("無效的 payload")
            raise HTTPException(status_code=400, detail="無效的 payload")
        except stripe.error.SignatureVerificationError:
            print("認證失敗")
            raise HTTPException(status_code=400, detail="認證失敗")
        event_type = event["type"]
        if event_type == "checkout.session.completed":
            session = event["data"]["object"]
            order_id = int(session["metadata"]["order_id"])
            try:
                async with db.transaction():
                    select_query = "SELECT o.*, st.name as service_type, st.required_workers, st.base_duration_hours, st.additional_duration_hours FROM orders o    JOIN service_types st ON o.service_type_id = st.id WHERE o.id = $1"
                    order_info = await db.fetchrow(select_query, order_id)
                    if not order_info:
                        print(f"訂單 {order_id} 不存在")
                        return {"status": "error", "message": "訂單不存在"}
                    stripe_amount = session["amount_total"]
                    expected_amount = order_info["total_amount"] * 100
                    if stripe_amount != expected_amount:
                        print(f"訂單 {order_info['order_number']} 金額不符，實付={stripe_amount/100}，應付={order_info['total_amount']}")
                        return {"status": "error", "message": "付款金額與訂單金額不符"}
                    update_query = "UPDATE orders SET status = 'paid', payment_status = 'paid', updated_at = NOW(), checkout_session_id = $2 WHERE id = $1 AND payment_status = 'unpaid'"
                    result = await db.execute(update_query, order_id, session['id'])
                    if result == "UPDATE 1":
                        await extend_booking_locks(order_id, db)
                        print(f"✅ 訂單 {order_info['order_number']} 付款成功，已延長鎖定時間")
                        return {"status": "received"}
                    else:
                        print(f"訂單 {order_id} 可能已處理過")
                        return {"status": "received"}
            except Exception as e:
                print(f"處理 webhook 事件時發生錯誤: {str(e)}")
                return {"status": "error", "message": str(e)}
        else:
            print(f"收到未處理的事件: {event_type}")
            return {"status": "received"}


async def extend_booking_locks(order_id, db):
    try:
        new_expires_at = datetime.now(TAIPEI_TZ) + timedelta(days=7)
        update_query = "UPDATE time_slot_locks SET expires_at = $1 WHERE id IN ( SELECT bs.temp_lock_id FROM booking_slots bs WHERE bs.order_id = $2  AND bs.temp_lock_id IS NOT NULL )"
        await db.execute(update_query, new_expires_at, order_id)
        update_query = "UPDATE booking_slots SET lock_expires_at = $1 WHERE order_id = $2"
        await db.execute(update_query, new_expires_at, order_id)
        print(f"已延長訂單 {order_id} 的鎖定到 {new_expires_at}")  
    except Exception as e:
        print(f"延長鎖定失敗: {e}")


