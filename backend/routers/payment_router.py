from fastapi import APIRouter, HTTPException, Depends, Request
import asyncpg
from utils.dependencies import get_connection
from utils.auth import require_auth, verify_order_ownership
from models.payment_model import (
    PaymentStatusResponse,
    CheckoutSessionRequest,
    CheckoutSessionResponse,
)
from services.payment_service import (
    create_checkout_session,
    get_payment_status,
    handle_webhook,
)

router = APIRouter(prefix="/api", tags=["payment"])


@router.post("/payment/create-checkout-session", response_model=CheckoutSessionResponse)
async def create_checkout_session_endpoint(
    request: CheckoutSessionRequest,
    current_user: dict = Depends(require_auth),
    db: asyncpg.Connection = Depends(get_connection),
):
    try:
        await verify_order_ownership(request.order_id, current_user["id"], db)
        return await create_checkout_session(request.order_id, db)
    except HTTPException as http_exc:
        print(f"{http_exc.status_code} - {http_exc.detail}")
        raise http_exc
    except Exception as e:
        print(f"創建 Checkout Session 失敗: {e}")
        raise HTTPException(status_code=500, detail="創建付款頁面失敗")


@router.get("/payment/status/{order_id}", response_model=PaymentStatusResponse)
async def get_payment_status_endpoint(
    order_id: int,
    current_user: dict = Depends(require_auth),
    db: asyncpg.Connection = Depends(get_connection),
):
    try:
        await verify_order_ownership(order_id, current_user["id"], db)
        return await get_payment_status(order_id, db)
    except HTTPException as http_exc:
        print(f"{http_exc.status_code} - {http_exc.detail}")
        raise http_exc
    except Exception as e:
        print(f"查詢付款狀態失敗: {e}")
        raise HTTPException(status_code=500, detail="查詢付款狀態失敗")


@router.post("/payment/webhook/stripe")
async def stripe_webhook_endpoint(
    request: Request, db: asyncpg.Connection = Depends(get_connection)
):
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
