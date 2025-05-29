from fastapi import HTTPException
from datetime import date, time, timedelta, datetime
from zoneinfo import ZoneInfo
from typing import List
from models.booking_model import (
    OrderRequest,
    OrderStatus,
    OrderResponse,
    BookingSlotResponse,
)
import asyncpg
import json
import uuid

TAIPEI_TZ = ZoneInfo("Asia/Taipei")

async def create_order_with_lock(order_data: OrderRequest, db: asyncpg.Pool):
    if len(order_data.booking_slots) < 1:
        raise HTTPException(status_code=400, detail="至少需要選擇一個預約時段")
    if len(order_data.booking_slots) > 2:
        raise HTTPException(status_code=400, detail="最多只能選擇兩個預約時段")
    try:
        async with db.transaction():
            service_type = order_data.service_type.value
            select_query = (
                "SELECT id, required_workers, name, base_duration_hours, additional_duration_hours FROM service_types WHERE name = $1"
            )
            service_info = await db.fetchrow(
                select_query,
                service_type,
            )
        if not service_info:
            raise HTTPException(
                status_code=400, detail="無效的服務類型，無法取得服務資訊"
            )

        service_name = service_info["name"]
        needs_locking = service_name in ["新機安裝", "冷氣保養"]
        booking_slots_response = []
        temp_locks = []

        for slot in order_data.booking_slots:
            from services.calendar_service import calculate_service_max_units
            max_units = await calculate_service_max_units(
                    slot.preferred_date, slot.preferred_time, service_type, db
                )
                
            if order_data.unit_count > max_units:
                raise HTTPException(
                        status_code=400, 
                        detail=f"時段 {slot.preferred_time.strftime('%H:%M')} 最多只能預約 {max_units} 台"
                    )

        for i, slot in enumerate(order_data.booking_slots):
            slot_response = BookingSlotResponse(
                date=slot.preferred_date,
                time=slot.preferred_time,
                contact_name=slot.contact_name,
                contact_phone=slot.contact_phone,
                is_primary=i == 0,
                is_available=True,
            )
            if needs_locking:
                if not await validate_slot_time(
                    service_name, slot.preferred_date, slot.preferred_time, db
                ):
                    slot_response.is_available = False
                else:
                    required_hours = (service_info["base_duration_hours"] + (order_data.unit_count - 1) * service_info["additional_duration_hours"])
                    required_hours = min(required_hours, 8)
                    select_query = "SELECT lock_service_time_slot($1, $2, $3, $4, NULL, 30)"
                    lock_id = await db.fetchval(
                        select_query,
                        slot.preferred_date,
                        slot.preferred_time,
                        service_info["required_workers"],
                        required_hours
                    )
                    if lock_id == -1:
                        slot_response.is_available = False
                    else:
                        temp_locks.append((lock_id, slot.preferred_date, slot.preferred_time))
            else:
                if not await validate_slot_time(
                    service_name, slot.preferred_date, slot.preferred_time, db
                ):
                    slot_response.is_available = False
            booking_slots_response.append(slot_response)
        if needs_locking:
            available_count = sum(
                1 for slot in booking_slots_response if slot.is_available
            )
            if available_count == 0:
                for lock_info in temp_locks:
                    lock_id, slot_date, slot_time = lock_info
                    select_query = "SELECT unlock_service_time_slot($1, $2, $3, $4)"
                    await db.fetchval(select_query, lock_id, slot_date, slot_time, required_hours)
                raise HTTPException(status_code=409, detail="所選時段都無法預約")
        total_amount = await calculate_order_amount(
            service_name,
            order_data.location_address,
            order_data.unit_count,
            order_data.equipment_details,
            db,
        )
        order_number = f"AC{datetime.now(TAIPEI_TZ).strftime('%Y%m%d%H%M%S')}{str(uuid.uuid4())[:4].upper()}"
        equipment_json = None
        if order_data.equipment_details:
            equipment_json = json.dumps(
                [item.dict() for item in order_data.equipment_details]
            )
        insert_query = "INSERT INTO orders (order_number, user_email, service_type_id, location_address, location_lat, location_lng, unit_count, total_amount, equipment_details, notes, status) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, 'pending') RETURNING id"
        order_id = await db.fetchval(
            insert_query,
            order_number,
            order_data.user_email,
            service_info["id"],
            order_data.location_address,
            order_data.location_lat,
            order_data.location_lng,
            order_data.unit_count,
            total_amount,
            equipment_json,
            order_data.notes,
        )
        lock_expires_at = (
            datetime.now(TAIPEI_TZ) + timedelta(minutes=30) if needs_locking else None
        )
        lock_index = 0
        for i, (slot_request, slot_response) in enumerate(
            zip(order_data.booking_slots, booking_slots_response)
        ):
            temp_lock_id = None
            is_locked = False
            if (
                needs_locking
                and slot_response.is_available
                and lock_index < len(temp_locks)
            ):
                temp_lock_id = temp_locks[lock_index][0]
                is_locked = True
                lock_index += 1

        insert_query = "INSERT INTO booking_slots (order_id, preferred_date, preferred_time, contact_name, contact_phone, is_primary, is_locked, temp_lock_id, lock_expires_at, is_selected) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)"
        await db.execute(
            insert_query,
            order_id,
            slot_request.preferred_date,
            slot_request.preferred_time,
            slot_request.contact_name,
            slot_request.contact_phone,
            i == 0,
            is_locked,
            temp_lock_id,
            lock_expires_at,
            False,
        )
        return OrderResponse(
            order_id=order_id,
            order_number=order_number,
            total_amount=total_amount,
            booking_slots=booking_slots_response,
            status=OrderStatus.PENDING,
            service_type=service_name,
        )
    except Exception as e:
        for lock_info in temp_locks:
            try:
                lock_id, slot_date, slot_time = lock_info
                await db.fetchval("SELECT unlock_service_time_slot($1, $2, $3, $4)", lock_id, slot_date, slot_time, required_hours)
            except Exception as unlock_error:
                print(f"清理鎖定失敗：{unlock_error}")
        print(f"預約失敗：{e}")
        raise HTTPException(status_code=500, detail="預約失敗")


async def validate_slot_time(
    service_type: str, slot_date: date, slot_time: time, db=asyncpg.Pool
):
    if not (time(8, 0) <= slot_time <= time(16, 0)):
        return False
    try:
        from services.calendar_service import check_service_slot_bookable
        return await check_service_slot_bookable(slot_date, slot_time, service_type, 1, db)
    except Exception as e:
        print(f"出現預期外錯誤，無法確認：{e}")
        raise HTTPException(status_code=500, detail="出現預期外錯誤，無法確認")


async def calculate_order_amount(
    service_type: str,
    location_address: str,
    unit_count: int,
    equipment_details: List = None,
    db=None,
):
    try:
        select_query = "SELECT pricing_type FROM service_types WHERE name = $1"
        service_info = await db.fetchrow(
            select_query,
            service_type,
        )
        if not service_info:
            print(f"找不到服務類型")
            raise HTTPException(
                status_code=400, detail="無效的服務類型，無法取得服務資訊"
            )
        pricing_type = service_info["pricing_type"]
        if pricing_type == "equipment":  # 做完商品列表再確認
            if equipment_details:
                total = 0
                for item in equipment_details:
                    total += item.price * item.quantity
                return total
            else:
                print(f"找不到 {service_type} 的設備價格")
                raise HTTPException(status_code=400, detail="無法取得正確價格")
        elif pricing_type == "unit_count":
            select_query = "SELECT base_price, additional_price FROM unit_pricing up JOIN service_types st ON up.service_type_id = st.id WHERE st.name = $1"
            pricing = await db.fetchrow(
                select_query,
                service_type,
            )
            if pricing:
                base_price = pricing["base_price"]
                additional_price = pricing["additional_price"]
                return base_price + max(0, unit_count - 1) * additional_price
            else:
                print(f"找不到 {service_type} 的單價")
                raise HTTPException(status_code=400, detail="無法取得正確價格")
        elif pricing_type == "location":
            region = determine_region(location_address)
            select_query = "SELECT lp.price FROM location_pricing lp    JOIN service_types st ON lp.service_type_id = st.id WHERE st.name = $1 AND lp.region = $2"
            price = await db.fetchval(select_query, service_type, region)
            return price or 1000
    except Exception as e:
        print(f"出現預期外錯誤，無法確認：{e}")
        raise HTTPException(status_code=500, detail="出現預期外錯誤，無法確認")


def determine_region(address: str):
    keywords = ["台北", "新北"]
    if any(keyword in address for keyword in keywords):
        return "雙北"
    return "其他地區"
