from pydantic import BaseModel
from typing import List, Dict
from datetime import date, time
from models.service_model import ServiceType


class SlotDetail(BaseModel):
    time: time
    available_workers: int


class CalendarDay(BaseModel):
    date: date
    available_slots: List[SlotDetail]
    is_available_for_booking: bool
    is_weekend: bool = False


class CalendarResponse(BaseModel):
    service_type: ServiceType
    days: List[CalendarDay]
    booking_range: Dict[str, date]
    current_month: int
    current_year: int


class SlotResponse(BaseModel):
    available: bool
    available_workers: int
    required_workers: int
