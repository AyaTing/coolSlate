from fastapi import HTTPException
from datetime import datetime, date, time, timedelta
from zoneinfo import ZoneInfo
from models.service_model import ServiceType
from models.calendar_model import (
    CalendarResponse,
    SlotDetail,
    CalendarDay,
    SlotResponse,
)

TAIPEI_TZ = ZoneInfo("Asia/Taipei")


async def get_available_calendar(
    service_type: ServiceType,
    year: int = None,
    month: int = None,
    db=None,
):
    try:
        select_query = "SELECT required_workers, booking_advance_months FROM service_types WHERE name = $1"
        service_info = await db.fetchrow(select_query, service_type.value)
        if not service_info:
            raise HTTPException(status_code=400, detail="無效的服務類型")
        today = datetime.now(TAIPEI_TZ).date()
        display_year = year if year is not None else today.year
        display_month = month if month is not None else today.month
        try:
            from_date = date(display_year, display_month, 1)
        except ValueError:
            raise HTTPException(status_code=400, detail="無效的年份或月份")
        if display_month == 12:
            to_date = date(display_year + 1, 1, 1) - timedelta(days=1)
        else:
            to_date = date(display_year, display_month + 1, 1) - timedelta(days=1)

        days = []
        current_date = from_date
        while current_date <= to_date:
            is_bookable = await check_date_bookable(
                current_date, service_type.value, 1, db
            )
            available_slots = []
            if is_bookable:
                slots = await get_daily_available_slots(
                    current_date, service_type.value, db
                )
                available_slots = []
                for slot_data in slots:
                    if slot_data["services"]:
                        current_slot_time = slot_data["time"]
                        real_available_workers = await get_slot_available_workers(
                            current_date,
                            current_slot_time,
                            db
                        )
                        available_slots.append(
                            SlotDetail(
                                time=slot_data["time"],
                                available_workers=real_available_workers,
                            )
                        )
            days.append(
                CalendarDay(
                    date=current_date,
                    available_slots=available_slots,
                    is_available_for_booking=is_bookable,
                    is_weekend=current_date.weekday() >= 5,
                )
            )
            current_date += timedelta(days=1)
        return CalendarResponse(
            service_type=service_type,
            days=days,
            booking_range={"from_date": from_date, "to_date": to_date},
            current_month=display_month,
            current_year=display_year,
        )
    except Exception as e:
        print(f"出現預期外錯誤，取得日曆失敗：{e}")
        raise HTTPException(status_code=500, detail="出現預期外錯誤，取得日曆失敗")


async def check_slot_availability(
    service_type: ServiceType, target_date: date, target_time: time, db
):
    try:
        select_query = "SELECT required_workers FROM service_types WHERE name = $1"
        service_info = await db.fetchrow(select_query, service_type.value)
        if not service_info:
            raise HTTPException(status_code=400, detail="無效的服務類型")
        today = datetime.now(TAIPEI_TZ).date()
        if target_date <= today:
            return SlotResponse(
                available=False,
                available_workers=0,
                required_workers=service_info["required_workers"],
            )
        is_available = await check_service_slot_bookable(
            target_date, target_time, service_type.value, 1, db
        )
        if is_available:
            available_workers = await get_slot_available_workers(
                target_date, target_time, db
            )
            return SlotResponse(
                available=True,
                available_workers=available_workers,
                required_workers=service_info["required_workers"],
            )
        else:
            return SlotResponse(
                available=False,
                available_workers=0,
                required_workers=service_info["required_workers"],
            )
    except Exception as e:
        print(f"出現預期外錯誤，無法確認：{e}")
        raise HTTPException(status_code=500, detail="出現預期外錯誤，無法確認")


async def get_daily_available_slots(
    target_date: date, service_type: str = None, db=None
):
    try:
        if service_type:
            service_types = [service_type]
        else:
            select_query = "SELECT name FROM service_types ORDER BY priority"
            services = await db.fetch(select_query)
            service_types = [service["name"] for service in services]
        time_slots = [
            "08:00",
            "09:00",
            "10:00",
            "11:00",
            "12:00",
            "13:00",
            "14:00",
            "15:00",
            "16:00",
        ]
        result_slots = []
        for time_str in time_slots:
            slot_time = datetime.strptime(time_str, "%H:%M").time()
            services_data = []
            for svc_type in service_types:
                is_available = await check_service_slot_bookable(
                    target_date, slot_time, svc_type, 1, db
                )
                if is_available:
                    max_units = await calculate_service_max_units(
                        target_date, slot_time, svc_type, db
                    )
                    services_data.append(
                        {
                            "service_type": svc_type,
                            "is_available": True,
                            "max_units": max_units,
                        }
                    )
            if services_data:
                result_slots.append({"time": slot_time, "services": services_data})
        return result_slots
    except Exception as e:
        print(f"獲取日期可用時段失敗: {e}")
        raise HTTPException(status_code=500, detail="獲取日期可用時段失敗")


async def check_date_bookable(
    target_date: date, service_type: str, unit_count: int, db
):
    try:
        select_query = (
            "SELECT booking_advance_months FROM service_types WHERE name = $1"
        )
        service_info = await db.fetchrow(select_query, service_type)
        if not service_info:
            return False
        today = datetime.now(TAIPEI_TZ).date()
        max_date = today + timedelta(days=service_info["booking_advance_months"] * 30)
        if target_date <= today or target_date > max_date:
            return False
        time_slots = [
            "08:00",
            "09:00",
            "10:00",
            "11:00",
            "12:00",
            "13:00",
            "14:00",
            "15:00",
            "16:00",
        ]
        for time_str in time_slots:
            slot_time = datetime.strptime(time_str, "%H:%M").time()
            if await check_service_slot_bookable(
                target_date, slot_time, service_type, unit_count, db
            ):
                return True
        return False
    except Exception as e:
        print(f"檢查日期可預約性失敗: {e}")
        return False


async def check_service_slot_bookable(
    target_date: date, target_time: time, service_type: str, unit_count: int, db
):
    try:
        select_query = "SELECT required_workers, base_duration_hours, additional_duration_hours FROM service_types WHERE name = $1"
        service_info = await db.fetchrow(select_query, service_type)
        if not service_info:
            return False
        required_hours = (
            service_info["base_duration_hours"]
            + (unit_count - 1) * service_info["additional_duration_hours"]
        )
        required_hours = min(required_hours, 8)
        required_workers = service_info["required_workers"]

        for hour_offset in range(required_hours):
            current_time = (
                datetime.combine(target_date, target_time)
                + timedelta(hours=hour_offset)
            ).time()
            if current_time >= time(17, 0):
                return False
            available_workers = await get_slot_available_workers(
                target_date, current_time, db
            )
            if available_workers < required_workers:
                return False
        return True
    except Exception as e:
        print(f"檢查服務時段可預約性失敗: {e}")
        return False


async def calculate_service_max_units(
    target_date: date, target_time: time, service_type: str, db
):
    try:
        select_query = "SELECT required_workers, base_duration_hours, additional_duration_hours FROM service_types WHERE name = $1"
        service_info = await db.fetchrow(select_query, service_type)
        if not service_info:
            return 0
        max_units = 0
        for units in range(1, 9):
            needed_hours = (
            service_info["base_duration_hours"]
            + (units - 1) * service_info["additional_duration_hours"]
        )
            needed_hours = min(needed_hours, 8)

            end_time = (
                datetime.combine(target_date, target_time)
                + timedelta(hours=needed_hours)
            ).time()

            if end_time > time(17, 0):
                break
            min_workers = await get_min_workers_in_range(
                target_date, target_time, needed_hours, db
            )

            if min_workers >= service_info["required_workers"]:
                max_units = units
            else:
                break
        return max_units
    except Exception as e:
        print(f"計算服務最大台數失敗: {e}")
        return 0


async def get_min_workers_in_range(target_date: date, start_time: time, hours: int, db):
    try:
        min_available = float("inf")  # 初始設為無窮大
        for hour_offset in range(hours):
            current_time = (
                datetime.combine(target_date, start_time) + timedelta(hours=hour_offset)
            ).time()
            if current_time >= time(17, 0):
                return 0

            available = await get_slot_available_workers(target_date, current_time, db)
            min_available = min(min_available, available)
        return min_available if min_available != float("inf") else 0
    except Exception as e:
        print(f"取得時間範圍內最小人力失敗: {e}")
        return 0


async def get_slot_available_workers(target_date: date, target_time: time, db):
    try:
        select_query = "SELECT get_real_available_workers($1, $2)"
        # select_query = "SELECT available_workers FROM available_time_slots WHERE slot_date = $1 AND slot_time = $2"
        available_workers = await db.fetchval(
            select_query,
            target_date,
            target_time,
        )
        if available_workers is None:
            return 0
        return max(0, available_workers)
    except Exception as e:
        print(f"獲取時段可用人力失敗: {e}")
        return 0


async def check_booking_feasibility(
    target_date: date, target_time: time, service_type: str, unit_count: int, db
):
    try:
        select_query = "SELECT required_workers, base_duration_hours, additional_duration_hours FROM service_types WHERE name = $1"
        service_info = await db.fetchrow(select_query, service_type)
        if not service_info:
            raise HTTPException(status_code=400, detail="無效的服務類型")
        required_hours = (
            service_info["base_duration_hours"]
            + (unit_count - 1) * service_info["additional_duration_hours"]
        )
        required_hours = min(required_hours, 8)
        required_workers = service_info["required_workers"]
        is_bookable = True
        time_slots_info = []
        for hour_offset in range(required_hours):
            current_time = (
                datetime.combine(target_date, target_time)
                + timedelta(hours=hour_offset)
            ).time()
            if current_time >= time(17, 0):
                is_bookable = False
                break
            available_workers = await get_slot_available_workers(
                target_date, current_time, db
            )
            time_slots_info.append(
                {
                    "time": current_time.strftime("%H:%M"),
                    "available_workers": available_workers,
                    "required_workers": required_workers,
                }
            )
            if available_workers < required_workers:
                is_bookable = False
        end_time = (
            datetime.combine(target_date, target_time) + timedelta(hours=required_hours)
        ).time()
        return {
            "is_bookable": is_bookable,
            "service_info": {
                "service_type": service_type,
                "unit_count": unit_count,
                "required_hours": required_hours,
                "required_workers": required_workers,
            },
            "time_slots": time_slots_info,
            "estimated_end_time": end_time.strftime("%H:%M"),
        }
    except Exception as e:
        print(f"檢查預約可行性失敗: {e}")
        raise HTTPException(status_code=500, detail="檢查預約可行性失敗")


async def get_service_types_config(db):
    return await db.fetch(
        """
        SELECT name, required_workers, base_duration_hours,
               additional_duration_hours, booking_advance_months, pricing_type
        FROM service_types ORDER BY priority
    """
    )
