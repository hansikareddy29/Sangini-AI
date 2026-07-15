from pydantic import BaseModel
from typing import List, Optional

class AllocationAssignment(BaseModel):
    member_id: str
    member: str
    allocated_quantity: int
    score: float

class AllocationOutput(BaseModel):
    assignments: List[AllocationAssignment] = []
    remaining_quantity: int = 0
    allocation_successful: bool
    reason: Optional[str] = None
