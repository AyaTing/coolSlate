import asyncio
from datetime import date, timedelta, datetime
from zoneinfo import ZoneInfo
from services.scheduling_service import process_repair_order


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
        await db.execute(
            """
            UPDATE booking_slots
            SET is_locked = false,
                temp_lock_id = NULL,
                lock_expires_at = NULL
            WHERE temp_lock_id IS NOT NULL
              AND temp_lock_id NOT IN (
                  SELECT id FROM time_slot_locks
                  WHERE expires_at IS NULL OR expires_at > NOW()
              )
        """
        )
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
    expired_orders = await db.fetch(
        """
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
    """
    )
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
                    order["base_duration_hours"]
                    + (unit_count - 1) * order["additional_duration_hours"]
                )
                required_hours = min(required_hours, 8)
                slots = await db.fetch(
                    """
                    SELECT bs.*, tsl.id as lock_id
                    FROM booking_slots bs
                    LEFT JOIN time_slot_locks tsl ON bs.temp_lock_id = tsl.id
                    WHERE bs.order_id = $1
                """,
                    order_id,
                )

                for slot in slots:
                    if slot["lock_id"]:
                        select_query = "SELECT unlock_service_time_slot($1, $2, $3, $4)"
                        await db.fetchval(
                            select_query,
                            slot["lock_id"],
                            slot["preferred_date"],
                            slot["preferred_time"],
                            required_hours,
                        )
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
        expired_repair_orders = await db.fetch(
            """
            SELECT o.id, o.order_number
            FROM orders o
            JOIN service_types st ON o.service_type_id = st.id
            WHERE o.status = 'pending' 
              AND o.payment_status = 'unpaid'
              AND st.name = 'REPAIR'
              AND o.created_at < NOW() - INTERVAL '30 minutes'
        """
        )
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


async def repair_scheduling_loop(db, client):
    while True:
        try:
            now = datetime.now(TAIPEI_TZ)
            next_run = now.replace(hour=15, minute=0, second=0, microsecond=0)
            if now > next_run:
                next_run += timedelta(days=1)
            sleep_seconds = (next_run - now).total_seconds()
            print(f"下次維修排程將在 {sleep_seconds:.0f} 秒後執行...")
            await asyncio.sleep(sleep_seconds)
            print(f"[{datetime.now(TAIPEI_TZ)}] 開始執行每日維修排程...")
            async with db.acquire() as conn:
                await daily_repair_scheduling(conn, client)
        except asyncio.CancelledError:
            print("維修背景排程循環已成功停止")
            raise
        except Exception as e:
            print(f"維修背景排程循環錯誤: {e}")
            await asyncio.sleep(3600)


async def daily_repair_scheduling(db, client):
    try:
        two_weeks_later = date.today() + timedelta(days=14)
        orders = await db.fetch(
            """
                SELECT DISTINCT o.id FROM orders o
                JOIN booking_slots bs ON o.id = bs.order_id
                JOIN service_types st ON o.service_type_id = st.id
                WHERE st.name = 'REPAIR' 
                  AND o.status = 'pending_schedule' 
                  AND bs.is_primary = true 
                  AND bs.preferred_date <= $1
            """,
            two_weeks_later,
        )
        success_count = 0
        for order_record in orders:
            try:
                result = await process_repair_order(order_record["id"], db, client)
                if result and result.get("success"):
                    success_count += 1
                print(
                    f"處理訂單 {order_record['id']}: {'成功' if result['success'] else result['reason']}"
                )
            except Exception as e:
                print(f"處理訂單 {order_record['id']} 發生錯誤: {e}")
        print(f"維修排程完成，成功處理 {success_count}/{len(orders)} 筆訂單")
    except Exception as e:
        print(f"每日維修排程失敗: {e}")
