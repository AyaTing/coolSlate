from fastapi import HTTPException
from datetime import date, time, timedelta, datetime
from zoneinfo import ZoneInfo
from typing import List
from models.booking_model import (
    OrderRequest,
    OrderStatus,
    OrderResponse,
    BookingSlotResponse,
    OrderDetail
)
import json
import uuid

TAIPEI_TZ = ZoneInfo("Asia/Taipei")

async def create_order_with_lock(order_data: OrderRequest, db):
    if len(order_data.booking_slots) < 1:
        raise HTTPException(status_code=400, detail="至少需要選擇一個預約時段")
    if len(order_data.booking_slots) > 2:
        raise HTTPException(status_code=400, detail="最多只能選擇兩個預約時段")
    
    service_type = order_data.service_type.value
    select_query = (
        "SELECT id, required_workers, name, base_duration_hours, additional_duration_hours FROM service_types WHERE name = $1"
    )
    service_info = await db.fetchrow(select_query, service_type)
    if not service_info:
        raise HTTPException(status_code=400, detail="無效的服務類型，無法取得服務資訊")

    service_name = service_info["name"]
    needs_locking = service_name in ["INSTALLATION", "MAINTENANCE"]
    required_hours = (
        service_info["base_duration_hours"]
        + (order_data.unit_count - 1) * service_info["additional_duration_hours"]
    )
    required_hours = min(required_hours, 8)

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

    booking_slots_response = []
    for i, slot in enumerate(order_data.booking_slots):
        slot_response = BookingSlotResponse(
            date=slot.preferred_date,
            time=slot.preferred_time,
            contact_name=slot.contact_name,
            contact_phone=slot.contact_phone,
            is_primary=i == 0,
            is_available=True,
        )
        
        if not await validate_slot_time(service_name, slot.preferred_date, slot.preferred_time, db):
            slot_response.is_available = False
            
        booking_slots_response.append(slot_response)

    available_slots = [slot for slot in booking_slots_response if slot.is_available]
    if not available_slots:
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
        equipment_json = json.dumps([item.dict() for item in order_data.equipment_details])

    temp_locks = []
    order_id = None
    
    try:
        async with db.transaction():
            print(f"開始創建訂單 {order_number}")
            
            if needs_locking:
                for i, slot in enumerate(order_data.booking_slots):
                    if booking_slots_response[i].is_available:
                        print(f"嘗試鎖定時段: {slot.preferred_date} {slot.preferred_time}")
                        lock_id = await db.fetchval(
                            "SELECT lock_service_time_slot($1, $2, $3, $4, NULL, 30)",
                            slot.preferred_date,
                            slot.preferred_time,
                            service_info["required_workers"],
                            required_hours
                        )
                        if lock_id == -1:
                            print(f"時段鎖定失敗: {slot.preferred_date} {slot.preferred_time}")
                            booking_slots_response[i].is_available = False
                        else:
                            print(f"時段鎖定成功: {slot.preferred_date} {slot.preferred_time}, lock_id={lock_id}")
                            temp_locks.append((lock_id, slot.preferred_date, slot.preferred_time))


                available_count = sum(1 for slot in booking_slots_response if slot.is_available)
                if available_count == 0:
                    print("所有時段鎖定失敗")
                    raise HTTPException(status_code=409, detail="所選時段都無法預約")


            print("創建訂單記錄")
            insert_query = """
                INSERT INTO orders (order_number, user_id, service_type_id, location_address, 
                                  location_lat, location_lng, unit_count, total_amount, 
                                  equipment_details, notes, status) 
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, 'pending') 
                RETURNING id
            """
            order_id = await db.fetchval(
                insert_query,
                order_number,
                order_data.user_id,
                service_info["id"],
                order_data.location_address,
                order_data.location_lat,
                order_data.location_lng,
                order_data.unit_count,
                total_amount,
                equipment_json,
                order_data.notes,
            )
            print(f"訂單創建成功，ID: {order_id}")

            lock_expires_at = (
                datetime.now(TAIPEI_TZ) + timedelta(minutes=30) if needs_locking else None
            )
            
            lock_index = 0
            for i, (slot_request, slot_response) in enumerate(
                zip(order_data.booking_slots, booking_slots_response)
            ):
                temp_lock_id = None
                is_locked = False
                
                if needs_locking and slot_response.is_available and lock_index < len(temp_locks):
                    temp_lock_id = temp_locks[lock_index][0]
                    is_locked = True
                    lock_index += 1

                print(f"創建預約時段 {i+1}: {slot_request.preferred_date} {slot_request.preferred_time}")
                
                insert_query = """
                    INSERT INTO booking_slots (order_id, preferred_date, preferred_time, 
                                             contact_name, contact_phone, is_primary, 
                                             is_locked, temp_lock_id, lock_expires_at, is_selected) 
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                """
                await db.execute(
                    insert_query,
                    order_id,
                    slot_request.preferred_date,
                    slot_request.preferred_time,
                    slot_request.contact_name,
                    slot_request.contact_phone,
                    i == 0,  # is_primary
                    is_locked,
                    temp_lock_id,
                    lock_expires_at,
                    False,  # is_selected
                )

            print(f"訂單 {order_number} 創建完成")

        return OrderResponse(
            order_id=order_id,
            order_number=order_number,
            total_amount=total_amount,
            booking_slots=booking_slots_response,
            status=OrderStatus.PENDING,
            service_type=service_name,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"創建訂單失敗：{str(e)}")
        raise HTTPException(status_code=500, detail="預約失敗")


async def validate_slot_time(
    service_type: str, slot_date: date, slot_time: time, db):
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

async def get_user_orders_service(user_id, db):
    try: 
        select_query = "SELECT o.*, st.name as service_type FROM orders o JOIN service_types st ON o.service_type_id = st.id WHERE o.user_id = $1 ORDER BY o.created_at DESC"
        orders = await db.fetch(select_query, user_id)
        result = []
        for order in orders:
            select_query = "SELECT preferred_date, preferred_time, contact_name, contact_phone, is_primary, is_selected FROM booking_slots WHERE order_id = $1 ORDER BY is_primary DESC, preferred_date, preferred_time"
            slots = await db.fetch(select_query, order["id"])
            order_dict = dict(order)
            order_dict["order_id"] = order_dict["id"]
            order_dict["booking_slots"] = [dict(slot) for slot in slots]
            if order_dict["equipment_details"]:
                order_dict["equipment_details"] = json.loads(order_dict["equipment_details"])
            else:
                order_dict["equipment_details"] = None
            result.append(OrderDetail(**order_dict))
        return result
    except Exception as e:
        print(f"出現預期外錯誤，無法確認：{e}")
        raise HTTPException(status_code=500, detail="出現預期外錯誤，無法確認")

async def get_order_detail_service(order_id: int, db):
    try: 
        select_query = "SELECT o.*, st.name as service_type FROM orders o JOIN service_types st ON o.service_type_id = st.id WHERE o.id = $1"
        order = await db.fetchrow(select_query, order_id)
        if not order:
            raise HTTPException(status_code=404, detail="訂單不存在")
        select_query = "SELECT preferred_date, preferred_time, contact_name, contact_phone, is_primary, is_selected FROM booking_slots WHERE order_id = $1 ORDER BY is_primary DESC, preferred_date, preferred_time"
        slots = await db.fetch(select_query, order_id)
        order_dict = dict(order)
        order_dict["order_id"] = order_dict["id"]
        order_dict["booking_slots"] = [dict(slot) for slot in slots]
        if order_dict["equipment_details"]:
            order_dict["equipment_details"] = json.loads(order_dict["equipment_details"])
        else:
            order_dict["equipment_details"] = None
        return OrderDetail(**order_dict)
    except Exception as e:
        print(f"出現預期外錯誤，無法確認：{e}")
        raise HTTPException(status_code=500, detail="出現預期外錯誤，無法確認")