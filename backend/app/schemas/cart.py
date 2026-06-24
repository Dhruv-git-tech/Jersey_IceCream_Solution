from pydantic import BaseModel
from typing import Optional, List

class CartItem(BaseModel):
    product_id: str
    quantity: int
    price: float

class CartCreate(BaseModel):
    items: List[CartItem]

class CartResponse(BaseModel):
    cart_id: str
    items: List[CartItem]
    total: float