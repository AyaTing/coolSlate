from fastapi import APIRouter, Depends, HTTPException, Query
from utils.auth import require_admin, get_connection
from services.admin_service import (
    get_all_orders_service,
    get_all_users_service,
    get_user_orders_service_by_admin,
)
from services.booking_service import get_order_detail_service
from services.scheduling_service import process_immediate_scheduling
from models.booking_model import OrderDetail
import asyncpg
from typing import Optional

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/users")
async def get_all_users_by_admin(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    search: Optional[str] = Query(None),
    current_user: dict = Depends(require_admin),
    db: asyncpg.Connection = Depends(get_connection),
):
    try:
        return await get_all_users_service(page, limit, search, db)
    except Exception as e:
        print(f"取得使用者列表失敗: {e}")
        raise HTTPException(status_code=500, detail="取得使用者列表失敗")


@router.get("/orders")
async def get_all_orders_by_admin(
    status: Optional[str] = Query(None),
    payment_status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    current_user: dict = Depends(require_admin),
    db: asyncpg.Connection = Depends(get_connection),
):
    try:
        return await get_all_orders_service(status, payment_status, page, limit, db)
    except Exception as e:
        print(f"取得訂單列表失敗: {e}")
        raise HTTPException(status_code=500, detail="取得訂單列表失敗")


@router.get("/order/{order_id}", response_model=OrderDetail)
async def get_order_detail_by_admin(
    order_id: int,
    current_user: dict = Depends(require_admin),
    db: asyncpg.Connection = Depends(get_connection),
):
    try:
        return await get_order_detail_service(order_id, db)
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        print(f"取得訂單詳情失敗: {e}")
        raise HTTPException(status_code=500, detail="取得訂單詳情失敗")


@router.get("/user/{user_id}/orders")
async def get_user_orders_by_admin(
    user_id: int,
    current_user: dict = Depends(require_admin),
    db: asyncpg.Connection = Depends(get_connection),
):
    try:
        return await get_user_orders_service_by_admin(user_id, db)
    except Exception as e:
        print(f"取得訂單列表失敗: {e}")
        raise HTTPException(status_code=500, detail="取得訂單列表失敗")


@router.post("/scheduling/{order_id}")
async def schedule_order(
    order_id: int,
    current_user: dict = Depends(require_admin),
    db: asyncpg.Connection = Depends(get_connection),
):
    try:
        order = await get_order_detail_service(order_id, db)
        if order.service_type in ["INSTALLATION", "MAINTENANCE"]:
            result = await process_immediate_scheduling(order_id, db)
            return result
        else:
            pass # 待維修排程邏輯完成
    except Exception as e:
        print(f"排程出現錯誤: {str(e)}")
        raise HTTPException(status_code=500, detail="排程出現錯誤")


# @router.post("/order/{order_id}/cancel")
# async def cancel_order_by_admin(
#     order_id: int,
#     current_user: dict = Depends(require_admin),
#     db: asyncpg.Connection = Depends(get_connection),
# ):
#     pass
