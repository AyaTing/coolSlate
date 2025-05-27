from fastapi import APIRouter, HTTPException, Depends, Request
import asyncpg
from utils.dependencies import get_connection
from models.payment_model import (
    PaymentIntentRequest,
    PaymentIntentResponse,
    PaymentStatusResponse
)
from services.payment_service import (
    create_payment_intent,
    get_payment_status,
    handle_webhook
)
router = APIRouter(prefix="/api", tags=["payment"])

@router.post("/payment/create-intent", response_model=PaymentIntentResponse)
async def create_payment_intent_endpoint(request: PaymentIntentRequest, db: asyncpg.Pool = Depends(get_connection)):
    try:
        return await create_payment_intent(request.order_id, db)
    except HTTPException as http_exc:
        print(f"{http_exc.status_code} - {http_exc.detail}")
        raise http_exc
    except Exception as e:
        print(f"創建 Payment Intent 失敗: {e}")
        raise HTTPException(status_code=500, detail="創建 Payment Intent 失敗")

@router.get("/payment/status/{order_id}", response_model=PaymentStatusResponse)
async def get_payment_status_endpoint(order_id: int, db: asyncpg.Pool = Depends(get_connection)):
    try:
        return await get_payment_status(order_id, db)
    except HTTPException as http_exc:
        print(f"{http_exc.status_code} - {http_exc.detail}")
        raise http_exc
    except Exception as e:
        print(f"查詢付款狀態失敗: {e}")
        raise HTTPException(status_code=500, detail="查詢付款狀態失敗")

@router.post("/payment/webhook/stripe")
async def stripe_webhook_endpoint(request: Request, db: asyncpg.Pool = Depends(get_connection)):
    try:
        payload = await request.body()
        sig_header = request.headers.get("stripe-signature", "")
        return await handle_webhook(payload, sig_header, db)
    except HTTPException as http_exc:
        print(f"{http_exc.status_code} - {http_exc.detail}")
        raise http_exc
    except Exception as e:
        print(f"處理 Stripe webhook 失敗: {e}")
        raise HTTPException(status_code=500, detail="Webhook 處理失敗")