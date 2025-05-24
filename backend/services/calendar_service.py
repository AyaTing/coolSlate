from fastapi import HTTPException
from datetime import datetime, date, time, timedelta
import asyncpg
from models.service_model import ServiceType
from models.calendar_model import (
    CalendarResponse,
    SlotDetail,
    CalendarDay,
    SlotResponse,
)


async def get_available_calendar(
    service_type: ServiceType,
    year: int = None,
    month: int = None,
    db: asyncpg.Pool = None,
):
    try:
        select_query = "SELECT required_workers, booking_advance_months FROM service_types WHERE name = $1"
        service_info = await db.fetchrow(select_query, service_type.value)
        if not service_info:
            raise HTTPException(status_code=400, detail="無效的服務類型")
        today = datetime.now().date()
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

        select_query = "SELECT slot_date, slot_time, available_workers FROM get_available_slots($1, $2, $3, $4)"
        slots = await db.fetch(
            select_query,
            service_type.value,
            service_info["required_workers"],
            from_date,
            to_date,
        )
        days_dict = {}
        for slot in slots:
            slot_date = slot["slot_date"]
            slot_time = slot["slot_time"]
            available_workers = slot["available_workers"]
            if slot_date is None or slot_time is None or available_workers is None:
                print(f"跳過無效資料: date={slot_date}, time={slot_time}, workers={available_workers}")
                continue
            if slot_date not in days_dict:
                days_dict[slot_date] = []
            days_dict[slot_date].append(
                SlotDetail(
                    time=slot_time,
                    available_workers=available_workers,
                )
            )
        days = []
        current_date = from_date
        while current_date <= to_date:
            available_slots = days_dict.get(current_date, [])
            is_available_for_booking = len(available_slots) > 0
            days.append(
                CalendarDay(
                    date=current_date,
                    available_slots=available_slots,
                    is_available_for_booking=is_available_for_booking,
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
    service_type: ServiceType, target_date: date, target_time: time, db: asyncpg.Pool
):
    try:
        select_query = "SELECT required_workers FROM service_types WHERE name = $1"
        service_info = await db.fetchrow(select_query, service_type.value)
        if not service_info:
            raise HTTPException(status_code=400, detail="無效的服務類型")
        today = datetime.now().date()
        if target_date <= today:
            return SlotResponse(
                available=False,
                available_workers=0,
                required_workers=service_info["required_workers"],
            )
        select_query = "SELECT slot_date, slot_time, available_workers FROM get_available_slots($1, $2, $3, $4)"
        slots = await db.fetch(
            select_query,
            service_type.value,
            service_info["required_workers"],
            target_date,
            target_date,
        )
        found_slot = None

        for slot in slots:
            if slot["slot_date"] == target_date and slot["slot_time"] == target_time:
                found_slot = slot
                break
        if found_slot:
            return SlotResponse(
                available=True,
                available_workers=found_slot["available_workers"],
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
