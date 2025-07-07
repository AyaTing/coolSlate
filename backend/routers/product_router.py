from fastapi import APIRouter, HTTPException, Depends
import asyncpg
from utils.dependencies import get_connection
from services.product_service import get_products


router = APIRouter(prefix="/api", tags=["product"])

@router.get("/product")
async def get_products_endpoint(db: asyncpg.Connection = Depends(get_connection)):
    try:
       products_list = await get_products(db)
       return products_list
    except HTTPException as http_exc:
        print(f"{http_exc.status_code} - {http_exc.detail}")
        raise http_exc
    except Exception as e:
        print(f"商品清單取得失敗: {e}")
        raise HTTPException(status_code=500, detail="商品清單取得失敗")


