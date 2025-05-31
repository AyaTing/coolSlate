from fastapi import APIRouter, HTTPException, Depends
from utils.dependencies import get_connection
from models.booking_model import OrderRequest, OrderResponse
from services.booking_service import create_order_with_lock
import asyncpg

router = APIRouter(prefix="/api", tags=["order"])

@router.post("/order", response_model=OrderResponse)
async def create_order(order_data: OrderRequest, db: asyncpg.Connection = Depends(get_connection)):
    try:
        order_response = await create_order_with_lock(order_data, db)
        return order_response
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        print(f"預約失敗，請重新預約: {e}")
        raise HTTPException(status_code=500, detail="預約失敗，請重新預約")