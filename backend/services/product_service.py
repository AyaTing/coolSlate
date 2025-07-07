from fastapi import HTTPException

async def get_products(db):
    try:
        select_query = "SELECT * FROM products WHERE is_active = true ORDER BY id"
        products = await db.fetch(select_query)
        return [dict(product) for product in products]
    except Exception as e:
        print(f"取得商品清單失敗: {e}")
        raise HTTPException(status_code=500, detail="取得商品清單失敗")
    
    