from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum

class OrderStatus(str, Enum):
    PENDING = "pending"
    PAYMENT_SENT = "payment_sent"
    PAID = "paid"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class OrderItem(BaseModel):
    product_id: int
    product_name: str
    quantity: int
    price: float
    image_url: Optional[str] = None

class Order(BaseModel):
    phone_number: str
    customer_name: Optional[str] = None
    items: List[OrderItem]
    total_amount: float
    status: OrderStatus = OrderStatus.PENDING
    payment_link: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)