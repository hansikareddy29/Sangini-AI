from pydantic import BaseModel, Field
from typing import List, Optional

class OrderItem(BaseModel):
    item: str = Field(..., description="The singular name of the product requested (e.g., 'Papad', not 'Papads').")
    quantity: int = Field(..., description="The quantity requested. Use 1 if not explicitly mentioned but implied.")
    deadline: Optional[str] = Field(None, description="The exact date for the deadline, if mentioned. Must be formatted as YYYY-MM-DD.")

class OrderExtraction(BaseModel):
    orders: List[OrderItem] = Field(..., description="A list of all items requested in the customer message.")
