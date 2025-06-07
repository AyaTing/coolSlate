from fastapi import HTTPException
import asyncio
from zoneinfo import ZoneInfo


TAIPEI_TZ = ZoneInfo("Asia/Taipei")
 

async def cleanup_loop(db):
    while True:
        try:
            async with db.acquire() as conn:
                await run_cleanup(conn)
            await asyncio.sleep(300)
        except asyncio.CancelledError:
            print("清理服務已成功停止") 
            raise
        except Exception as e:
            await asyncio.sleep(60)
            print(f"清理服務發生意外錯誤: {e}") 


async def run_cleanup(db):
    try:
        await db.execute("""
            UPDATE booking_slots
            SET is_locked = false,
                temp_lock_id = NULL,
                lock_expires_at = NULL
            WHERE temp_lock_id IS NOT NULL
              AND temp_lock_id NOT IN (
                  SELECT id FROM time_slot_locks
                  WHERE expires_at IS NULL OR expires_at > NOW()
              )
        """)
        expired_locks = await db.fetchval("SELECT clean_expired_locks()")
        if expired_locks > 0:
            print(f"清理過期鎖定: {expired_locks} 筆")
        expired_orders = await find_orders_with_all_slots_expired(db)
        if expired_orders:
            deleted_count = await delete_orders_with_expired_slots(expired_orders, db)
            print(f"刪除時段過期訂單: {deleted_count} 筆")
        deleted_repair_orders = await delete_unpaid_repair_orders(db)
        if deleted_repair_orders > 0:
            print(f"刪除未付款的維修訂單: {deleted_repair_orders} 筆")
    except Exception as e:
        print(f"清除程式出現錯誤：{e}")


async def find_orders_with_all_slots_expired(db):
    expired_orders = await db.fetch("""
        SELECT DISTINCT 
            o.id, 
            o.order_number, 
            st.name as service_type,
            o.unit_count,
            st.base_duration_hours,
            st.additional_duration_hours
        FROM orders o
        JOIN service_types st ON o.service_type_id = st.id
        WHERE o.status = 'pending'
          AND o.payment_status = 'unpaid'
          AND st.name IN ('INSTALLATION', 'MAINTENANCE')
          AND o.created_at < NOW() - INTERVAL '30 minutes'
          AND NOT EXISTS (
              SELECT 1 
              FROM booking_slots bs
              LEFT JOIN time_slot_locks tsl ON bs.temp_lock_id = tsl.id
              WHERE bs.order_id = o.id
                AND bs.is_locked = true
                AND (tsl.expires_at IS NULL OR tsl.expires_at > NOW())
          )
    """)
    return expired_orders

async def delete_orders_with_expired_slots(expired_orders: list, db):
    deleted_count = 0
    for order in expired_orders:
        try:
            async with db.transaction():
                order_id = order["id"]
                order_number = order["order_number"]
                service_type = order["service_type"]
                unit_count = order["unit_count"]
                required_hours = (
                        order["base_duration_hours"] + 
                        (unit_count - 1) * order["additional_duration_hours"]
                    )
                required_hours = min(required_hours, 8)
                slots = await db.fetch("""
                    SELECT bs.*, tsl.id as lock_id
                    FROM booking_slots bs
                    LEFT JOIN time_slot_locks tsl ON bs.temp_lock_id = tsl.id
                    WHERE bs.order_id = $1
                """, order_id)

                for slot in slots:
                    if slot["lock_id"]:
                        select_query = "SELECT unlock_service_time_slot($1, $2, $3, $4)"
                        await db.fetchval(select_query, slot["lock_id"], slot["preferred_date"], slot["preferred_time"], required_hours)
                delete_query = "DELETE FROM booking_slots WHERE order_id = $1"
                await db.execute(delete_query, order_id)
                delete_query = "DELETE FROM orders WHERE id = $1"
                await db.execute(delete_query, order_id)
                deleted_count += 1
                print(f"刪除過期訂單: {order_number} ({service_type}, {unit_count}台)")
                
        except Exception as e:
            print(f"刪除訂單 {order['order_number']} 失敗: {e}")
            continue
    return deleted_count


async def delete_unpaid_repair_orders(db):
    try:
        expired_repair_orders = await db.fetch("""
            SELECT o.id, o.order_number
            FROM orders o
            JOIN service_types st ON o.service_type_id = st.id
            WHERE o.status = 'pending' 
              AND o.payment_status = 'unpaid'
              AND st.name = 'REPAIR'
              AND o.created_at < NOW() - INTERVAL '30 minutes'
        """)
        if not expired_repair_orders:
            return 0
        deleted_count = 0
        for order in expired_repair_orders:
            try:
                async with db.transaction():
                    order_id = order["id"]
                    order_number = order["order_number"]
                    delete_query = "DELETE FROM booking_slots WHERE order_id = $1"
                    await db.execute(delete_query, order_id)
                    delete_query = "DELETE FROM orders WHERE id = $1"
                    await db.execute(delete_query, order_id)
                    deleted_count += 1
                    print(f"刪除過期維修訂單: {order_number}")      
            except Exception as e:
                print(f"刪除維修訂單 {order['order_number']} 失敗: {e}")
                continue
            
        return deleted_count
    except Exception as e:
        print(f"清理維修訂單時發生錯誤: {e}")
        return 0
