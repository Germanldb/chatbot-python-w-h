from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum

class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

class Message(BaseModel):
    role: MessageRole
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    image_url: Optional[str] = None
    product_ids: Optional[List[str]] = None

class ConversationStatus(str, Enum):
    ACTIVE = "active"
    IDLE = "idle"
    CLOSED = "closed"

class Conversation(BaseModel):
    phone_number: str
    customer_name: Optional[str] = None
    messages: List[Message] = []
    status: ConversationStatus = ConversationStatus.ACTIVE
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_product_searched: Optional[str] = None
    pending_order: Optional[dict] = None