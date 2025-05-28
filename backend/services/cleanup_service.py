from fastapi import HTTPException, Request
import asyncio
import asyncpg
from zoneinfo import ZoneInfo


TAIPEI_TZ = ZoneInfo("Asia/Taipei")
 

async def stop_cleanup(cleanup_task):
    if cleanup_task and not cleanup_task.done():
        cleanup_task.cancel()
        try:
            await cleanup_task
        except asyncio.CancelledError:
            print("清理服務已成功停止") 
        except Exception as e:
            print(f"停止清理服務時，發生意外錯誤: {e}") 
    else:
        print("清理服務無需停止 (可能未啟動或已完成)。") 


async def cleanup_loop(db: asyncpg.Pool):
    while True:
        try:
            await run_cleanup(db)
            await asyncio.sleep(300)
        except asyncio.CancelledError:
            print("清理服務已成功停止") 
            raise
        except Exception as e:
            await asyncio.sleep(60)
            print(f"清理服務發生意外錯誤: {e}") 



async def run_cleanup(db: asyncpg.Pool):
    try:
        update_query = "UPDATE booking_slots SET is_locked = false, temp_lock_id = NULL, lock_expires_at = NULL WHERE temp_lock_id IS NOT NULL AND temp_lock_id NOT IN (SELECT id FROM time_slot_locks)"
        await db.execute(update_query,)
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
        raise HTTPException(status_code=500, detail="清除程式出現錯誤，無法確認")


async def find_orders_with_all_slots_expired(db):
    expired_orders = await db.fetch("""
            SELECT DISTINCT o.id, o.order_number, st.name as service_type
            FROM orders o
            JOIN service_types st ON o.service_type_id = st.id               
            WHERE o.status = 'pending' 
              AND o.payment_status = 'unpaid'
              AND st.name IN ('新機安裝', '冷氣保養')
              AND EXISTS (
                  SELECT 1 FROM booking_slots bs 
                  WHERE bs.order_id = o.id
              )
              AND NOT EXISTS (
                  SELECT 1 FROM booking_slots bs 
                  WHERE bs.order_id = o.id 
                    AND bs.is_locked = true
              )
        """)
    return expired_orders

async def delete_orders_with_expired_slots(expired_orders: list, db):
    deleted_count = 0
    for order in expired_orders:
        try:
            async with db.acquire() as conn:
                async with conn.transaction():
                    order_id = order["id"]
                    order_number = order["order_number"]
                    service_type = order["service_type"]
                    select_query = "SELECT unlock_time_slot(temp_lock_id) FROM booking_slots WHERE order_id = $1 AND temp_lock_id IS NOT NULL"
                    await conn.execute(select_query, order_id)
                    count_query = "SELECT COUNT(*) FROM booking_slots WHERE order_id = $1"
                    deleted_slots = await conn.fetchval(count_query, order_id)
                    delete_query = "DELETE FROM booking_slots WHERE order_id = $1"
                    await conn.fetchval(delete_query, order_id)
                    delete_query = "DELETE FROM orders WHERE id = $1"
                    await conn.execute(delete_query, order_id)
                    deleted_count += 1
                    print(f"完全刪除: {order_number} ({service_type}, 含 {deleted_slots or 0} 個預約時段)")
        except Exception as e:
            print(f"刪除訂單 {order['order_number']} 失敗: {e}")
            continue
    return deleted_count


async def delete_unpaid_repair_orders(db):
    expired_repair_orders = await db.fetch("""
            SELECT o.id, o.order_number
            FROM orders o
            JOIN service_types st ON o.service_type_id = st.id
            WHERE o.status = 'pending' 
              AND o.payment_status = 'unpaid'
              AND st.name = '冷氣維修'
              AND o.created_at < NOW() - INTERVAL '30 minutes'
        """)
    if not expired_repair_orders:
        return 0
    deleted_count = 0
    for order in expired_repair_orders:
        try:
            async with db.acquire() as conn:
                async with conn.transaction():
                    order_id = order["id"]
                    order_number = order["order_number"]
                    count_query = "SELECT COUNT(*) FROM booking_slots WHERE order_id = $1"
                    deleted_slots = await conn.fetchval(count_query, order_id)
                    delete_query = "DELETE FROM booking_slots WHERE order_id = $1"
                    await conn.fetchval(delete_query, order_id)
                    delete_query = "DELETE FROM orders WHERE id = $1"
                    await conn.execute(delete_query, order_id)                    
                    deleted_count += 1
                    print(f"清理維修預約: {order_number} (含 {deleted_slots or 0} 個預約時段)")       
        except Exception as e:
            print(f"清理維修訂單 {order['order_number']} 失敗: {e}")
            continue    
    return deleted_count
