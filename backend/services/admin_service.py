from fastapi import HTTPException
from typing import Optional
from services.booking_service import get_user_orders_service


async def get_all_orders_service(
    status: Optional[str], payment_status: Optional[str], page: int, limit: int, db
):
    try:
        where_conditions = []
        params = []
        param_count = 0
        if status:
            param_count += 1
            where_conditions.append(f"o.status = ${param_count}")
            params.append(status)
        if payment_status:
            param_count += 1
            where_conditions.append(f"o.payment_status = ${param_count}")
            params.append(payment_status)
        where_clause = " AND ".join(where_conditions)
        if where_clause:
            where_clause = "WHERE " + where_clause
        select_query = f"SELECT COUNT(*) FROM orders o {where_clause}"
        total = await db.fetchval(select_query, *params)

        offset = (page - 1) * limit
        param_count += 1
        limit_param = f"${param_count}"
        param_count += 1
        offset_param = f"${param_count}"

        select_query = f"""
        SELECT o.*, st.name as service_type, u.name as user_name, u.email as user_email
        FROM orders o 
        JOIN service_types st ON o.service_type_id = st.id
        JOIN users u ON o.user_id = u.id
        {where_clause}
        ORDER BY o.created_at DESC
        LIMIT {limit_param} OFFSET {offset_param}
        """
        orders = await db.fetch(select_query, *params, limit, offset)
        return {
            "orders": orders,
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": (total + limit - 1) // limit,
        }
    except Exception as e:
        print(f"獲取訂單列表失敗：{e}")
        raise HTTPException(status_code=500, detail="獲取訂單列表失敗")


async def get_all_users_service(page: int, limit: int, search: Optional[str], db):
    try:
        where_clause = ""
        params = []
        if search:
            where_clause = "WHERE name ILIKE $1 OR email ILIKE $1"
            params.append(f"%{search}%")
        select_query = f"SELECT COUNT(*) FROM users {where_clause}"
        total = await db.fetchval(select_query, *params)
        offset = (page - 1) * limit
        select_query = f"""
        SELECT id, name, email, role, created_at
        FROM users 
        {where_clause}
        ORDER BY created_at DESC
        LIMIT ${len(params) + 1} OFFSET ${len(params) + 2}
        """
        users = await db.fetch(select_query, *params, limit, offset)
        return {
            "users": users,
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": (total + limit - 1) // limit,
        }
    except Exception as e:
        print(f"獲取使用者列表失敗：{e}")
        raise HTTPException(status_code=500, detail="獲取使用者列表失敗")


async def get_user_orders_service_by_admin(user_id: int, db):
    try:
        user = await db.fetchrow("SELECT * FROM users WHERE id = $1", user_id)
        if not user:
            raise HTTPException(status_code=404, detail="使用者不存在")
        orders = await get_user_orders_service(user_id, db)
        return {
            "user": {"id": user["id"], "name": user["name"], "email": user["email"]},
            "orders": orders,
        }
    except Exception as e:
        print(f"獲取使用者訂單列表失敗：{e}")
        raise HTTPException(status_code=500, detail="獲取使用者訂單列表失敗")
