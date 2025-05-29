from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, date, time
from models.service_model import ServiceType
from enum import Enum
from models.payment_model import PaymentStatus

class OrderStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    SCHEDULED = "scheduled"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    PENDING_RESCHEDULE = "pending_reschedule"


class EquipmentItem(BaseModel):
    name: str
    model: str
    price: int
    quantity: int


class BookingSlotRequest(BaseModel):
    preferred_date: date 
    preferred_time: time
    contact_name: str
    contact_phone: str


class OrderRequest(BaseModel):
    user_email: EmailStr
    service_type: ServiceType
    location_address: str
    location_lat: Optional[float] = None
    location_lng: Optional[float] = None
    unit_count: int
    equipment_details: Optional[List[EquipmentItem]] = None
    notes: Optional[str] = None
    booking_slots: List[BookingSlotRequest]= Field(..., min_items=1, max_items=2)
    

class BookingSlotResponse(BaseModel):
    date: date
    time: time
    contact_name: str
    contact_phone: str
    is_primary: bool
    is_available: bool

class OrderResponse(BaseModel):
    order_id: int
    order_number: str
    total_amount: int
    booking_slots: List[BookingSlotResponse]
    status: OrderStatus
    service_type: str


class OrderDetail(BaseModel):
    order_id: int
    order_number: str
    user_email: str
    service_type: str
    location_address: str
    location_lat: Optional[float] = None
    location_lng: Optional[float] = None
    unit_count: int
    total_amount: int
    status: OrderStatus
    payment_status: PaymentStatus
    equipment_details: Optional[List[Dict[str, Any]]] = None
    notes: Optional[str] = None
    booking_slots: List[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime