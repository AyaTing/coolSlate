from fastapi import APIRouter, HTTPException, Depends
from utils.dependencies import get_connection
import asyncpg
from typing import Optional
from models.service_model import ServiceType
from models.calendar_model import CalendarResponse
from services.calendar_service import get_available_calendar, check_slot_availability
from datetime import date, time

router = APIRouter(prefix="/api", tags=["calendar"])


@router.get("/calendar/{service_type}", response_model=CalendarResponse)
async def get_service_calendar(
    service_type: ServiceType,
    year: Optional[int] = None,
    month: Optional[int] = None,
    db: asyncpg.Pool = Depends(get_connection),
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


@router.get("/calendar/slots/")
async def check_service_slot(
    service_type: ServiceType,
    target_date: date,
    target_time: time,
    db: asyncpg.Pool = Depends(get_connection),
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
