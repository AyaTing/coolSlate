from fastapi import HTTPException
from typing import Optional
from services.booking_service import get_user_orders_service
from datetime import datetime
from zoneinfo import ZoneInfo

TAIPEI_TZ = ZoneInfo("Asia/Taipei")


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
        result = []
        for order in orders:
            select_query = """
            SELECT preferred_date, preferred_time, contact_name, contact_phone, is_primary, is_selected 
            FROM booking_slots 
            WHERE order_id = $1 
            ORDER BY is_primary DESC, preferred_date, preferred_time
            """
            slots = await db.fetch(select_query, order["id"])
            order_dict = dict(order)
            order_dict["order_id"] = order_dict["id"]
            order_dict["booking_slots"] = [dict(slot) for slot in slots]
            if order_dict["equipment_details"]:
                import json

                order_dict["equipment_details"] = json.loads(
                    order_dict["equipment_details"]
                )
            else:
                order_dict["equipment_details"] = None
            result.append(order_dict)
        return {
            "orders": result,
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
    except HTTPException:
        raise
    except Exception as e:
        print(f"獲取使用者訂單列表失敗：{e}")
        raise HTTPException(status_code=500, detail="獲取使用者訂單列表失敗")


async def update_order_refund_status(order_id: int, refund_user: str, db):
    try:
        async with db.transaction():
            select_query = "SELECT id, order_number, status, payment_status, notes FROM orders WHERE id = $1"
            order = await db.fetchrow(
                select_query,
                order_id,
            )
            if not order:
                raise HTTPException(status_code=404, detail="使用者不存在")
            if order["payment_status"] != "paid":
                raise HTTPException(
                    status_code=400, detail="無法對未付款訂單進行此操作"
                )
            if order["status"] in ["completed", "cancelled"]:
                raise HTTPException(
                    status_code=400, detail=f"訂單狀態為 '{order["status"]}'，無法退款"
                )
            refund_time = datetime.now(TAIPEI_TZ).strftime("%Y-%m-%d %H:%M")
            refund_note = f"[退款記錄] 退款人：{refund_user}，退款時間：{refund_time}"
            existing_notes = order["notes"] or ""
            new_notes = existing_notes + refund_note
            update_query = "UPDATE orders SET payment_status = 'refunded', notes = $2, updated_at = NOW() WHERE id = $1"
            await db.execute(update_query, order_id, new_notes)
            return {
                "success": True,
                "message": f"訂單 {order["order_number"]} 退款狀態已更新",
                "refund_user": refund_user,
                "refund_time": refund_time,
            }
    except HTTPException:
        raise
    except Exception as e:
        print(f"更新退款狀態失敗：{e}")
        raise HTTPException(status_code=500, detail="更新退款狀態失敗")


async def cancel_order(order_id: int, db):
    try:
        async with db.transaction():
            select_query = """
                SELECT o.*, st.name as service_type, st.base_duration_hours, st.additional_duration_hours
                FROM orders o 
                JOIN service_types st ON o.service_type_id = st.id 
                WHERE o.id = $1
            """
            order = await db.fetchrow(select_query, order_id)
            if not order:
                raise HTTPException(status_code=404, detail="訂單不存在")
            if order["status"] in ["completed", "cancelled"]:
                raise HTTPException(
                    status_code=400, detail=f"訂單狀態為 '{order["status"]}'，無法取消"
                )
            if order["payment_status"] == "unpaid":
                raise HTTPException(
                    status_code=400, detail="未付款訂單會自動清理，無需手動取消"
                )
            if order["payment_status"] != "refunded":
                raise HTTPException(status_code=400, detail="請先執行退款程序")
            if (
                order["service_type"] == "REPAIR"
                and order["status"] == "pending_schedule"
            ):
                update_query = "UPDATE orders SET status = 'cancelled', updated_at = NOW() WHERE id = $1"
                await db.execute(update_query, order_id)
                return {
                    "success": True,
                    "message": f"訂單 {order['order_number']} 已成功取消",
                    "cleaned_locks": 0
                }
            else:
                cleaned_locks_count = await cleanup_all_order_locks(order_id, db)
                delete_query = "DELETE FROM daily_workforce_usage WHERE schedule_id IN (SELECT id FROM schedules WHERE order_id = $1)"
                await db.execute(delete_query, order_id)
                delete_query = "DELETE FROM schedules WHERE order_id = $1"
                await db.execute(delete_query, order_id)
                update_query = "UPDATE orders SET status = 'cancelled', updated_at = NOW() WHERE id = $1"
                await db.execute(update_query, order_id)
                return {
                    "success": True,
                    "message": f"訂單 {order['order_number']} 已成功取消",
                    "cleaned_locks": cleaned_locks_count
                }
    except HTTPException:
        raise
    except Exception as e:
        print(f"取消訂單失敗：{e}")
        raise HTTPException(status_code=500, detail="取消訂單失敗")

async def cleanup_all_order_locks(order_id: int, db):
    try:
        select_query = """
                SELECT DISTINCT 
                    tsl.id,
                    tsl.lock_type,
                    tsl.reference_id,
                    tsl.slot_date,
                    tsl.slot_time,
                    CASE 
                        WHEN tsl.reference_id IN (SELECT id FROM schedules WHERE order_id = $1) 
                        THEN 'schedule_lock'
                        WHEN tsl.id IN (SELECT temp_lock_id FROM booking_slots WHERE order_id = $1 AND temp_lock_id IS NOT NULL)
                        THEN 'booking_lock'
                        ELSE 'unknown'
                    END as lock_source
                FROM time_slot_locks tsl
                WHERE 
                    tsl.reference_id IN (
                        SELECT id FROM schedules WHERE order_id = $1
                    )
                    OR
                    tsl.id IN (
                        SELECT temp_lock_id 
                        FROM booking_slots 
                        WHERE order_id = $1 AND temp_lock_id IS NOT NULL
                    )
            """
        lock_records = await db.fetch(select_query, order_id)
        if not lock_records:
            print(f"訂單 {order_id} 沒有需要清理的鎖定記錄")
            return 0
        update_query = """
            UPDATE booking_slots 
            SET temp_lock_id = NULL, 
                is_locked = false, 
                lock_expires_at = NULL
            WHERE order_id = $1 AND temp_lock_id IS NOT NULL
        """
        await db.execute(update_query, order_id)
        lock_ids = [record['id'] for record in lock_records]
        if lock_ids:
            delete_query = "DELETE FROM time_slot_locks WHERE id = ANY($1)"
            delete_result = await db.execute(delete_query, lock_ids)
            deleted_count = 0
            if delete_result and "DELETE" in delete_result:
                deleted_count = int(delete_result.split()[1])
            print(f"成功刪除 {deleted_count} 個鎖定記錄")
            if deleted_count != len(lock_ids):
                print(f"警告：預期刪除 {len(lock_ids)} 個，實際刪除 {deleted_count} 個")
            return deleted_count
        return 0       
    except Exception as e:
        print(f"清理訂單 {order_id} 鎖定時發生錯誤: {e}")
        return 0