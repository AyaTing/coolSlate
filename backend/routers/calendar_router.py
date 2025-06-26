from fastapi import APIRouter, HTTPException, Depends
from utils.dependencies import get_connection
import asyncpg
from typing import Optional
from models.service_model import ServiceType
from models.calendar_model import CalendarResponse
from services.calendar_service import (
    get_available_calendar,
    check_slot_availability,
    get_daily_available_slots,
    check_booking_feasibility,
    check_date_bookable,
    calculate_service_max_units,
    get_service_types_config,
    check_service_slot_bookable,
)
from datetime import date, time, datetime, timedelta
from zoneinfo import ZoneInfo

router = APIRouter(prefix="/api", tags=["calendar"])
TAIPEI_TZ = ZoneInfo("Asia/Taipei")


@router.get("/calendar/service")
async def get_service_types_info(db: asyncpg.Connection = Depends(get_connection)):
    try:
        services = await get_service_types_config(db)
        return [
            {
                "name": service["name"],
                "required_workers": service["required_workers"],
                "base_duration_hours": service["base_duration_hours"],
                "additional_duration_hours": service["additional_duration_hours"],
                "booking_advance_months": service["booking_advance_months"],
                "pricing_type": service["pricing_type"],
            }
            for service in services
        ]
    except Exception as e:
        print(f"獲取服務類型資訊失敗: {e}")
        raise HTTPException(status_code=500, detail="獲取服務類型資訊失敗")


@router.get("/calendar/slots/")
async def check_service_slot(
    service_type: ServiceType,
    target_date: date,
    target_time: time,
    db: asyncpg.Connection = Depends(get_connection),
):
    try:
        check_result = await check_slot_availability(
            service_type, target_date, target_time, db
        )
        return check_result
    except HTTPException as http_exc:
        print(f"{http_exc.status_code} - {http_exc.detail}")
        raise http_exc
    except Exception as e:
        print(f"出現預期外錯誤，無法確認：{e}")
        raise HTTPException(status_code=500, detail="出現預期外錯誤，無法確認")


@router.get("/calendar/date/{target_date}")
async def get_daily_availability(
    target_date: date,
    service_type: Optional[ServiceType] = None,
    db: asyncpg.Connection = Depends(get_connection),
):
    try:
        service_filter = service_type.value if service_type else None
        slots_data = await get_daily_available_slots(target_date, service_filter, db)
        slots = []
        for slot_data in slots_data:
            slots.append(
                {
                    "time": slot_data["time"].strftime("%H:%M"),
                    "services": slot_data["services"],
                }
            )
        return {"date": target_date.strftime("%Y-%m-%d"), "slots": slots}
    except Exception as e:
        print(f"獲取日期可用時段失敗: {e}")
        raise HTTPException(status_code=500, detail="獲取可用時段失敗")


@router.get("/calendar/check-booking")
async def check_booking_endpoint(
    target_date: date,
    target_time: time,
    service_type: ServiceType,
    unit_count: int,
    db: asyncpg.Connection = Depends(get_connection),
):
    try:
        result = await check_booking_feasibility(
            target_date, target_time, service_type.value, unit_count, db
        )
        return result

    except HTTPException:
        raise
    except Exception as e:
        print(f"檢查預約可行性失敗: {e}")
        raise HTTPException(status_code=500, detail="檢查預約可行性失敗")


@router.post("/calendar/check-dates")
async def check_multiple_dates_availability(
    dates: list[date],
    service_type: ServiceType,
    db: asyncpg.Connection = Depends(get_connection),
):
    try:
        if len(dates) > 31:
            raise HTTPException(status_code=400, detail="一次最多檢查31個日期")
        availability = {}
        for check_date in dates:
            is_available = await check_date_bookable(
                check_date, service_type.value, 1, db
            )
            availability[check_date.strftime("%Y-%m-%d")] = is_available
        return {"service_type": service_type.value, "availability": availability}
    except HTTPException:
        raise
    except Exception as e:
        print(f"批次檢查日期可用性失敗: {e}")
        raise HTTPException(status_code=500, detail="批次檢查失敗")


@router.get("/calendar/unified")
async def get_unified_calendar(
    year: Optional[int] = None,
    month: Optional[int] = None,
    db: asyncpg.Connection = Depends(get_connection),
):
    try:
        today = datetime.now(TAIPEI_TZ).date()
        display_year = year if year is not None else today.year
        display_month = month if month is not None else today.month
        from_date = date(display_year, display_month, 1)
        if display_month == 12:
            to_date = date(display_year + 1, 1, 1) - timedelta(days=1)
        else:
            to_date = date(display_year, display_month + 1, 1) - timedelta(days=1)
        services = await get_service_types_config(db)
        service_names = [service["name"] for service in services]
        calendar_data = {}
        current_date = from_date
        while current_date <= to_date:
            date_str = current_date.strftime("%Y-%m-%d")
            calendar_data[date_str] = {}
            for service_name in service_names:
                is_available = await check_date_bookable(
                    current_date, service_name, 1, db
                )
                calendar_data[date_str][service_name] = is_available
            current_date += timedelta(days=1)
        return {
            "calendar_data": calendar_data,
            "current_month": display_month,
            "current_year": display_year,
        }
    except Exception as e:
        print(f"獲取統一月曆失敗: {e}")
        raise HTTPException(status_code=500, detail="獲取統一月曆失敗")


@router.get("/calendar/check-units")
async def check_units_dynamic(
    target_date: date,
    target_time: time,
    service_type: ServiceType,
    unit_count: int,
    db: asyncpg.Connection = Depends(get_connection),
):
    try:
        can_book = await check_service_slot_bookable(
            target_date, target_time, service_type.value, unit_count, db
        )
        max_available = await calculate_service_max_units(
            target_date, target_time, service_type.value, db
        )
        return {
            "can_book": can_book,
            "requested_units": unit_count,
            "max_available": max_available,
        }
    except Exception as e:
        print(f"檢查台數失敗: {e}")
        raise HTTPException(status_code=500, detail="檢查台數失敗")


@router.get("/calendar/{service_type}", response_model=CalendarResponse)
async def get_service_calendar(
    service_type: ServiceType,
    year: Optional[int] = None,
    month: Optional[int] = None,
    db: asyncpg.Connection = Depends(get_connection),
):
    try:
        available_calendar = await get_available_calendar(service_type, year, month, db)
        return available_calendar
    except HTTPException as http_exc:
        print(f"{http_exc.status_code} - {http_exc.detail}")
        raise http_exc
    except Exception as e:
        print(f"出現預期外錯誤，取得日曆失敗：{e}")
        raise HTTPException(status_code=500, detail="出現預期外錯誤，取得日曆失敗")
