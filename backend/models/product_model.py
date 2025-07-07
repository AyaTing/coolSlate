from pydantic import BaseModel
from typing import Optional

class Product(BaseModel):
    id: int
    name: str
    model: str
    price: int
    image: str = '❄️'
    description: Optional[str] = None
    category: str = '冷氣機'
    is_active: bool = True