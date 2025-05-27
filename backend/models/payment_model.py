# models/payment_model.py
from pydantic import BaseModel
from datetime import datetime
from enum import Enum

class PaymentStatus(str, Enum):
    UNPAID = "unpaid"
    PAID = "paid"
    REFUNDED = "refunded"

class PaymentIntentRequest(BaseModel):
    order_id: int

class PaymentIntentResponse(BaseModel):
    client_secret: str 
    payment_intent_id: str
    amount: int 
    currency: str = "twd"
    publishable_key: str

class PaymentStatusResponse(BaseModel):
    order_id: int
    order_number: str
    payment_status: PaymentStatus
    order_status: str
    total_amount: int
    created_at: datetime
    updated_at: datetime