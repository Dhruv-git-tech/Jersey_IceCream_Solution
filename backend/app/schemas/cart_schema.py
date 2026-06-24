from pydantic import BaseModel
from typing import List, Optional

class CartItemSchema(BaseModel):
    id: int
    product_id: int
    quantity: int
    price: float
    user_id: int
    

class CartSchema(BaseModel):
    id: int
    user_id: int
    items: List[CartItemSchema]
    total: float

    class Config:
        orm_mode = True