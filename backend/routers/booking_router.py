from fastapi import APIRouter, HTTPException, Depends
from utils.dependencies import get_connection
from utils.auth import verify_order_ownership
from models.booking_model import OrderRequest, OrderResponse, OrderDetail
from services.booking_service import create_order_with_lock, get_order_detail_service, get_user_orders_service, request_cancel_order_service
import asyncpg
from utils.auth import require_auth
from typing import List

router = APIRouter(prefix="/api", tags=["order"])

@router.post("/order", response_model=OrderResponse)
async def create_order(order_data: OrderRequest, current_user: dict = Depends(require_auth), db: asyncpg.Connection = Depends(get_connection)):
    try:
        order_data.user_id = current_user["id"]
        order_response = await create_order_with_lock(order_data, db)
        return order_response
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        print(f"預約失敗，請重新預約: {e}")
        raise HTTPException(status_code=500, detail="預約失敗，請重新預約")
    
@router.get("/orders", response_model=List[OrderDetail])
async def get_user_orders(current_user: dict = Depends(require_auth), db: asyncpg.Connection = Depends(get_connection)):
    try:
        return await get_user_orders_service(current_user["id"], db)
    except Exception as e:
        print(f"取得訂單列表失敗: {e}")
        raise HTTPException(status_code=500, detail="取得訂單列表失敗")

@router.get("/order/{order_id}", response_model=OrderDetail)
async def get_order_detail(order_id: int, current_user: dict = Depends(require_auth), db: asyncpg.Connection = Depends(get_connection)):
    try:
        await verify_order_ownership(order_id, current_user["id"], db)
        return await get_order_detail_service(order_id, db)
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        print(f"取得訂單詳情失敗: {e}")
        raise HTTPException(status_code=500, detail="取得訂單詳情失敗")
    

@router.post("/order/{order_id}/cancel-request")
async def request_cancel_order(
    order_id: int, 
    current_user: dict = Depends(require_auth), 
    db: asyncpg.Connection = Depends(get_connection)
):
    try:
        await verify_order_ownership(order_id, current_user["id"], db)
        return request_cancel_order_service(order_id, db)
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        print(f"取消申請失敗: {e}")
        raise HTTPException(status_code=500, detail="取消申請失敗")




