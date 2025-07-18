from fastapi import HTTPException
from datetime import datetime, timedelta, time
from zoneinfo import ZoneInfo
from services.mail_service import send_scheduling_success_email
from utils.geocoding import get_coordinates
from services.calendar_service import check_service_slot_bookable

TAIPEI_TZ = ZoneInfo("Asia/Taipei")


async def process_immediate_scheduling(order_id: int, db):
    try:
        async with db.transaction():
            select_query = "SELECT o.*, st.name as service_type, st.required_workers, st.base_duration_hours, st.additional_duration_hours FROM orders o  JOIN service_types st ON o.service_type_id = st.id WHERE o.id = $1 FOR UPDATE"
            order = await db.fetchrow(
                select_query,
                order_id,
            )
            if not order:
                raise HTTPException(status_code=404, detail="訂單不存在")
            if order["payment_status"] != "paid":
                raise HTTPException(status_code=400, detail="只能為已付款的訂單排程")
            if order["status"] not in ["pending_schedule"]:
                raise HTTPException(
                    status_code=400, detail=f"訂單狀態 '{order['status']}' 無法進行排程"
                )
            select_query = "SELECT bs.*, tsl.id as lock_id FROM booking_slots bs LEFT JOIN time_slot_locks tsl ON bs.temp_lock_id = tsl.id WHERE bs.order_id = $1 AND bs.is_locked = true AND bs.temp_lock_id IS NOT NULL ORDER BY bs.is_primary DESC, bs.preferred_date, bs.preferred_time"
            locked_slots = await db.fetch(select_query, order_id)
            if not locked_slots:
                raise HTTPException(status_code=400, detail="沒有已鎖定的時段可以排程")
            selected_slot = None
            for slot in locked_slots:
                if slot["is_primary"]:
                    selected_slot = slot
                    break
            if not selected_slot and locked_slots:
                selected_slot = locked_slots[0]
            if not selected_slot:
                raise HTTPException(status_code=400, detail="沒有已鎖定的時段可以排程")
            required_hours = (
                order["base_duration_hours"]
                + (order["unit_count"] - 1) * order["additional_duration_hours"]
            )
            required_hours = min(required_hours, 8)
            start_datetime = datetime.combine(
                selected_slot["preferred_date"], selected_slot["preferred_time"]
            )
            end_datetime = start_datetime + timedelta(hours=required_hours)
            estimated_end_time = end_datetime.time()
            insert_query = "INSERT INTO schedules (order_id, booking_slot_id, scheduled_date, scheduled_time, estimated_end_time, assigned_workers, status) VALUES ($1, $2, $3, $4, $5, $6, 'scheduled') RETURNING id"
            schedule_id = await db.fetchval(
                insert_query,
                order_id,
                selected_slot["id"],
                selected_slot["preferred_date"],
                selected_slot["preferred_time"],
                estimated_end_time,
                order["required_workers"],
            )
            if selected_slot["lock_id"]:
                select_query = "SELECT id FROM time_slot_locks WHERE slot_date = $1 AND slot_time >= $2 AND slot_time < $3 AND lock_type = 'booking' AND (expires_at IS NULL OR expires_at > NOW()) ORDER BY slot_time"
                start_datetime = datetime.combine(
                    selected_slot["preferred_date"], selected_slot["preferred_time"]
                )
                end_datetime = start_datetime + timedelta(hours=required_hours)
                lock_records = await db.fetch(
                    select_query,
                    selected_slot["preferred_date"],
                    selected_slot["preferred_time"],
                    end_datetime.time(),
                )
                for lock_record in lock_records:
                    await db.fetchval(
                        "SELECT convert_lock_to_schedule($1, $2)",
                        lock_record["id"],
                        schedule_id,
                    )
            update_query = "UPDATE orders SET status = 'scheduled', updated_at = NOW() WHERE id = $1"
            await db.execute(
                update_query,
                order_id,
            )
            update_query = "UPDATE booking_slots SET is_selected = true WHERE id = $1"
            await db.execute(
                update_query,
                selected_slot["id"],
            )
            await release_unused_locks(order_id, selected_slot["id"], db)
        email_sent = False
        try:
            select_query = "SELECT u.email, u.name FROM users u JOIN orders o ON u.id = o.user_id WHERE o.id = $1"
            user = await db.fetchrow(select_query, order_id)
            if user:
                order_data = {
                    "order_id": order_id,
                    "order_number": order["order_number"],
                    "service_type": order["service_type"],
                    "location_address": order["location_address"],
                    "total_amount": order["total_amount"],
                    "scheduled_date": selected_slot["preferred_date"],
                    "scheduled_time": selected_slot["preferred_time"],
                    "estimated_end_time": estimated_end_time,
                    "contact_name": selected_slot.get("contact_name"),
                    "contact_phone": selected_slot.get("contact_phone"),
                    "user_email": user["email"],
                    "user_name": user["name"],
                }
                result = send_scheduling_success_email(order_data)
                email_sent = result.get("success", False)
        except Exception as email_error:
            print(f"郵件發送失敗，但排程已成功: {email_error}")
        return {
            "success": True,
            "order_id": order_id,
            "schedule_id": schedule_id,
            "scheduled_date": selected_slot["preferred_date"],
            "scheduled_time": selected_slot["preferred_time"],
            "estimated_end_time": estimated_end_time,
            "email_sent": email_sent,
        }
    except Exception as e:
        print(f"立即排程出現錯誤: {str(e)}")
        raise HTTPException(status_code=500, detail="立即排程出現錯誤")


async def release_unused_locks(order_id: int, selected_slot_id: int, db):
    try:
        select_query = """
            SELECT bs.preferred_date, bs.preferred_time, o.unit_count,
                   st.base_duration_hours, st.additional_duration_hours
            FROM booking_slots bs
            JOIN orders o ON bs.order_id = o.id
            JOIN service_types st ON o.service_type_id = st.id
            WHERE bs.order_id = $1 
              AND bs.id != $2 
              AND bs.temp_lock_id IS NOT NULL
              AND bs.is_locked = true
            """
        unused_slots = await db.fetch(select_query, order_id, selected_slot_id)
        if not unused_slots:
            print(f"訂單 {order_id} 沒有需要釋放的未選中時段")
            return
        released_count = 0
        for slot in unused_slots:
            required_hours = (
                slot["base_duration_hours"]
                + (slot["unit_count"] - 1) * slot["additional_duration_hours"]
            )
            required_hours = min(required_hours, 8)
            start_datetime = datetime.combine(
                slot["preferred_date"], slot["preferred_time"]
            )
            end_datetime = start_datetime + timedelta(hours=required_hours)
            delete_query = "DELETE FROM time_slot_locks WHERE slot_date = $1 AND slot_time >= $2 AND slot_time < $3 AND lock_type = 'booking'"
            await db.execute(
                delete_query,
                slot["preferred_date"],
                slot["preferred_time"],
                end_datetime.time(),
            )
            update_query = "UPDATE booking_slots SET is_locked = false, temp_lock_id = NULL, lock_expires_at = NULL WHERE order_id = $1 AND preferred_date = $2 AND preferred_time = $3"
            await db.execute(
                update_query, order_id, slot["preferred_date"], slot["preferred_time"]
            )
            released_count += 1
        if released_count > 0:
            print(f"訂單 {order_id} 釋放了 {released_count} 個未選中的暫時鎖定")
    except Exception as e:
        print(f"釋放未使用鎖定失敗: {e}")
        raise


async def process_repair_order(order_id: int, db, http_client):
    try:
        async with db.transaction():
            select_query = "SELECT o.*, st.name as service_type, st.required_workers, st.base_duration_hours, st.additional_duration_hours FROM orders o  JOIN service_types st ON o.service_type_id = st.id WHERE o.id = $1 AND st.name = 'REPAIR' FOR UPDATE"
            order = await db.fetchrow(
                select_query,
                order_id,
            )
            if not order:
                raise HTTPException(status_code=404, detail="訂單不存在")
            if order["payment_status"] != "paid":
                raise HTTPException(status_code=400, detail="只能為已付款的訂單排程")
            if order["status"] not in ["pending_schedule", "scheduling_failed"]:
                raise HTTPException(
                    status_code=400, detail=f"訂單狀態 '{order['status']}' 無法進行排程"
                )
            if not order["location_lat"] or not order["location_lng"]:
                coords = await get_coordinates(order["location_address"], http_client)
                if not coords:
                    update_query = "UPDATE orders SET status = 'scheduling_failed', scheduling_feedback = '地址無法解析' WHERE id = $1"
                    await db.execute(update_query, order_id)
                    return {"success": False, "reason": "地址無法解析"}
                update_query = "UPDATE orders SET location_lat = $1, location_lng = $2 WHERE id = $3"
                await db.execute(update_query, coords["lat"], coords["lng"], order_id)
                lat, lng = coords["lat"], coords["lng"]
            else:
                lat, lng = order["location_lat"], order["location_lng"]
            company_info = await db.fetchrow("SELECT * FROM company_settings LIMIT 1")
            distance = await db.fetchval(
                "SELECT calculate_distance($1, $2, $3, $4)",
                lat,
                lng,
                company_info["company_lat"],
                company_info["company_lng"],
            )
            if distance > company_info["max_service_distance_km"]:
                feedback = f"超出服務範圍 ({distance:.1f}km > {company_info['max_service_distance_km']}km)"
                update_query = "UPDATE orders SET status = 'scheduling_failed', scheduling_feedback = $1 WHERE id = $2"
                await db.execute(update_query, feedback, order_id)
                return {"success": False, "reason": "超出服務範圍"}
            select_query = "SELECT * FROM booking_slots WHERE order_id = $1 ORDER BY is_primary DESC"
            booking_slots = await db.fetch(select_query, order_id)
            selected_slot = None
            for slot in booking_slots:
                can_book = await check_service_slot_bookable(
                    slot["preferred_date"],
                    slot["preferred_time"],
                    "REPAIR",
                    order["unit_count"],
                    db,
                )
                if can_book:
                    selected_slot = slot
                    break
            if not selected_slot:
                update_query = "UPDATE orders SET status = 'scheduling_failed', scheduling_feedback = '偏好時段皆已滿' WHERE id = $1"
                await db.execute(update_query, order_id)
                return {"success": False, "reason": "時段已滿"}
            required_hours = (
                order["base_duration_hours"]
                + (order["unit_count"] - 1) * order["additional_duration_hours"]
            )
            required_hours = min(required_hours, 8)
            start_datetime = datetime.combine(
                selected_slot["preferred_date"], selected_slot["preferred_time"]
            )
            end_datetime = start_datetime + timedelta(hours=required_hours)
            insert_query = "INSERT INTO schedules (order_id, booking_slot_id, scheduled_date, scheduled_time, estimated_end_time, assigned_workers, status) VALUES ($1, $2, $3, $4, $5, $6, 'scheduled') RETURNING id"
            schedule_id = await db.fetchval(
                insert_query,
                order_id,
                selected_slot["id"],
                selected_slot["preferred_date"],
                selected_slot["preferred_time"],
                end_datetime.time(),
                order["required_workers"],
            )
            for i in range(required_hours):
                current_time = (start_datetime + timedelta(hours=i)).time()
                if current_time < time(17, 0):
                    insert_query = "INSERT INTO daily_workforce_usage(date, time_slot, used_workers, schedule_id) VALUES ($1, $2, $3, $4)"
                    await db.execute(
                        insert_query,
                        selected_slot["preferred_date"],
                        current_time,
                        order["required_workers"],
                        schedule_id,
                    )
            update_query = "UPDATE orders SET status = 'scheduled', scheduling_feedback = NULL WHERE id = $1"
            await db.execute(update_query, order_id)
            update_query = "UPDATE booking_slots SET is_selected = true WHERE id = $1"
            await db.execute(update_query, selected_slot["id"])
        try:
            email_sent = False
            select_query = "SELECT u.email, u.name FROM users u JOIN orders o ON u.id = o.user_id WHERE o.id = $1"
            user = await db.fetchrow(select_query, order_id)
            if user:
                order_data = {
                    "order_id": order_id,
                    "order_number": order["order_number"],
                    "service_type": "REPAIR",
                    "location_address": order["location_address"],
                    "total_amount": order["total_amount"],
                    "scheduled_date": selected_slot["preferred_date"],
                    "scheduled_time": selected_slot["preferred_time"],
                    "estimated_end_time": end_datetime.time(),
                    "contact_name": selected_slot.get("contact_name"),
                    "contact_phone": selected_slot.get("contact_phone"),
                    "user_email": user["email"],
                    "user_name": user["name"],
                }
            result = send_scheduling_success_email(order_data)
            email_sent = result.get("success", False)
        except Exception as email_error:
            print(f"郵件發送失敗，但排程已成功: {email_error}")
        return {
            "success": True,
            "order_id": order_id,
            "schedule_id": schedule_id,
            "scheduled_date": selected_slot["preferred_date"],
            "scheduled_time": selected_slot["preferred_time"],
            "estimated_end_time": end_datetime.time(),
            "email_sent": email_sent,
        }
    except Exception as e:
        print(f"維修排程出現錯誤: {str(e)}")
        raise HTTPException(status_code=500, detail="立即排程出現錯誤")
