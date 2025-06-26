from pydantic import BaseModel
from datetime import datetime
from enum import Enum


class PaymentStatus(str, Enum):
    UNPAID = "unpaid"
    PAID = "paid"
    REFUNDED = "refunded"


class CheckoutSessionRequest(BaseModel):
    order_id: int


class CheckoutSessionResponse(BaseModel):
    session_url: str
    session_id: str
    order_id: int
    expires_at: datetime


class PaymentStatusResponse(BaseModel):
    order_id: int
    order_number: str
    payment_status: PaymentStatus
    order_status: str
    total_amount: int
    created_at: datetime
    updated_at: datetime
