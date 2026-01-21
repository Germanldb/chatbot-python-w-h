from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class ProductImage(BaseModel):
    src: str
    alt: Optional[str] = None

class Product(BaseModel):
    wc_id: int
    name: str
    price: str
    regular_price: Optional[str] = None
    sale_price: Optional[str] = None
    description: Optional[str] = None
    short_description: Optional[str] = None
    images: List[ProductImage] = []
    categories: List[dict] = []
    tags: List[dict] = []
    stock_status: str = "instock"
    permalink: str
    sku: Optional[str] = None
    cached_at: datetime = Field(default_factory=datetime.utcnow)
    search_count: int = 0