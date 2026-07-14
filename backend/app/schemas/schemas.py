from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from uuid import UUID

# Product Schemas
class ProductBase(BaseModel):
    name: str
    unit: str
    description: Optional[str] = None

class ProductResponse(ProductBase):
    id: UUID
    
    # This config allows Pydantic to read data directly from SQLAlchemy ORM models
    model_config = ConfigDict(from_attributes=True)

# Inventory Schemas
class InventoryBase(BaseModel):
    available_quantity: int

class InventoryResponse(InventoryBase):
    id: UUID
    product: ProductResponse
    
    model_config = ConfigDict(from_attributes=True)
