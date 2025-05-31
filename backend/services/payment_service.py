from fastapi import HTTPException
import stripe
import os
from models.payment_model import (
    PaymentIntentResponse,
    PaymentStatusResponse,
    PaymentStatus
)
from dotenv import load_dotenv

load_dotenv()

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY")

async def create_payment_intent(order_id: int, db):
    try:
        select_query = "SELECT o.*, st.name as service_type FROM orders o   JOIN service_types st ON o.service_type_id = st.id WHERE o.id = $1"
        order = await db.fetchrow( select_query, order_id,)    
        if not order:
            raise HTTPException(status_code=404, detail="訂單不存在")
        if order["status"] != "pending":
            raise HTTPException(status_code=400, detail="訂單狀態錯誤，無法付款")    
        if order["payment_status"] == "paid":
            raise HTTPException(status_code=400, detail="訂單已完成付款")
        if order['payment_intent_id']:
            try:
                existing_intent = stripe.PaymentIntent.retrieve(order["payment_intent_id"])
                if existing_intent.status in ["requires_payment_method", "requires_confirmation", "requires_action"]:
                    return PaymentIntentResponse(
                        client_secret=existing_intent.client_secret,
                        payment_intent_id=existing_intent.id,
                        amount=order["total_amount"],
                        currency="twd",
                        publishable_key=STRIPE_PUBLISHABLE_KEY
                        )
                elif existing_intent.status == 'succeeded':
                    print(f"訂單{order_id}已完成，狀態未同步")
                    raise HTTPException(status_code=400, detail=f"訂單{order_id}已完成，狀態未同步")
            except stripe.error.StripeError as e:
                print(f"查詢現有 Payment Intent 失敗: {e}")
        try:
            intent = stripe.PaymentIntent.create(
                amount=order["total_amount"] * 100,
                currency="twd",
                automatic_payment_methods={"enabled": True},
                metadata={
                    "order_id": str(order_id),
                    "order_number": order['order_number'],
                    "service_type": order['service_type'],
                    "user_email": order["user_email"]
                },
                description=f"冷氣服務預約 - {order['service_type']} - {order['order_number']}",
                receipt_email=order["user_email"]
            )
            update_query = "UPDATE orders SET payment_intent_id = $1, updated_at = NOW() WHERE id = $2"
            await db.execute(update_query, intent.id, order_id)
            print(f"成功創建 Payment Intent: {intent.id} for 訂單 {order['order_number']}")
            return PaymentIntentResponse(
                    client_secret=intent.client_secret,
                    payment_intent_id=intent.id,
                    amount=order["total_amount"],
                    currency="twd",
                    publishable_key=STRIPE_PUBLISHABLE_KEY
            )
        except stripe.error.StripeError as e:
            print(f"Stripe 錯誤: {str(e)}")
            raise HTTPException(status_code=400, detail=f"創建 PaymentIntent 失敗: {str(e)}")
        except Exception as err:
            print(f"創建 Payment Intent 時發生錯誤: {str(err)}")
            raise HTTPException(status_code=500, detail="付款服務暫時無法使用")
    except Exception as e:
        print(f"出現預期外錯誤，無法確認：{e}")
        raise HTTPException(status_code=500, detail="出現預期外錯誤，無法確認")

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
        event_type = event['type']
        if event_type == "payment_intent.succeeded":
            payment_intent = event["data"]["object"]
            order_id = int(payment_intent["metadata"]["order_id"])
            try:
                async with db.transaction():
                    update_query = "UPDATE orders SET status = 'paid', payment_status = 'paid', updated_at = NOW() WHERE id = $1 AND payment_status = 'unpaid'"
                    result = await db.execute(update_query, order_id,)
                    if result == "UPDATE 1":
                        order_number = await db.fetchval(
                            "SELECT order_number FROM orders WHERE id = $1", order_id
                        )
                        print(f"訂單 {order_number} 付款成功")
                        # await trigger_scheduling(order_id)
                        return {"status": "received"}
                    else:
                        print(f"訂單 {order_id} 可能已處理過")
                        return {"status": "received"}
            except Exception as e:
                print(f"❌ 處理 webhook 事件時發生錯誤: {str(e)}")
                return {"status": "error", "message": str(e)}
        elif event_type == 'payment_intent.payment_failed':
            order_id = int(event['data']['object']['metadata']['order_id'])
            print(f"訂單 {order_id} 付款失敗")
            return {"status": "received"}
        else:
            print(f"收到未處理的事件: {event_type}")
            return {"status": "received"}
