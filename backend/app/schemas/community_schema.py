from pydantic import BaseModel
from typing import List

class EligibleMember(BaseModel):
    member_id: str  # using string for UUID
    name: str
    phone: str
    status: str
    products: List[str]
    daily_capacity: int
    current_workload: int
    remaining_capacity: int
    today_allocations: int
    experience_level: str = "Medium"
    priority: int = 1

class CommunityAgentOutput(BaseModel):
    eligible_members: List[EligibleMember]
    available_member_count: int
    total_capacity: int
    need_to_produce: int
    can_fulfill: bool
