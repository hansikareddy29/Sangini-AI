"""Strongly typed shared state for Sangini worker agents.

This module is deliberately framework-neutral: it contains Pydantic models
only, with no LangGraph imports or orchestration logic.  A future graph can
use ``SharedState`` as its state contract without changing worker data shapes.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class WorkflowAction(str, Enum):
    """Actions a future workflow orchestrator may select."""

    ORDER_AGENT = "ORDER_AGENT"
    INVENTORY_AGENT = "INVENTORY_AGENT"
    COMMUNITY_AGENT = "COMMUNITY_AGENT"
    ALLOCATION_AGENT = "ALLOCATION_AGENT"
    CONFIRM_ORDER = "CONFIRM_ORDER"
    REJECT_ORDER = "REJECT_ORDER"
    END = "END"


class WorkflowStatus(str, Enum):
    """Lifecycle status for the whole order workflow."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    CONFIRMED = "CONFIRMED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"
    COMPLETED = "COMPLETED"

"""
PENDING   → initial state, nothing has run
RUNNING   → agents are processing the order
CONFIRMED → stock/production is successfully planned
REJECTED  → cannot fulfill the order
FAILED    → technical failure, such as an API/database error
COMPLETED → future lifecycle state after actual delivery/work completion
"""

class CustomerInfo(BaseModel):
    """Customer-owned request information, populated by the API layer."""

    phone_number: str
    customer_name: Optional[str] = None
    language: str = "en"
    original_message: str
    timestamp: datetime = Field(default_factory=datetime.now)


class InventoryInfo(BaseModel):
    """Inventory result for exactly one requested product."""

    available_quantity: int = 0
    reserved_quantity: int = 0
    available_after: int = 0
    need_to_produce: int = 0
    inventory_status: Optional[str] = None
    checked: bool = False
"""
inventory_status possible values =>
RESERVED
PARTIALLY_RESERVED
OUT_OF_STOCK
NOT_FOUND
"""

class EligibleMemberInfo(BaseModel):
    # Defines one capable SHG member returned by the Community Agent.
    member_id: str
    member_name: str
    phone_number: Optional[str] = None
    products: list[str] = Field(default_factory=list) #products that this person can make
    daily_capacity: int = 0 #default values => product-specific production limit
    current_workload: int = 0 #default values=> amount already allocated today
    remaining_capacity: int = 0 #default values => capacity still available for this product
    experience_level: Optional[str] = None
    priority: Optional[int] = None
    today_allocations: int = 0


class CommunityInfo(BaseModel):
    # Defines the Community Agent’s result for one product.

    eligible_members: list[EligibleMemberInfo] = Field(default_factory=list)
    total_capacity: int = 0
    can_fulfill: Optional[bool] = None
    unavailable_members: list[str] = Field(default_factory=list)
    checked: bool = False


class AllocationAssignmentInfo(BaseModel):
    """One member's production assignment for an order item."""

    member_id: str
    member_name: str
    allocated_quantity: int
    score: Optional[float] = None


class AllocationInfo(BaseModel):
    """Allocation result for exactly one requested product."""

    assignments: list[AllocationAssignmentInfo] = Field(default_factory=list)
    remaining_quantity: int = 0
    allocation_successful: Optional[bool] = None
    reason: Optional[str] = None
    attempted: bool = False


class OrderItemState(BaseModel):
    """One product request and the independent results produced for it.

    The Order Agent owns the product fields.  Inventory, Community, and
    Allocation workers own only their corresponding nested result models.
    """

    order_item_id: Optional[str] = None
    product_id: Optional[str] = None
    product_name: Optional[str] = None
    requested_name: str
    requested_quantity: int
    deadline: Optional[str] = None
    parsed_successfully: bool = False

    inventory: InventoryInfo = Field(default_factory=InventoryInfo)
    community: CommunityInfo = Field(default_factory=CommunityInfo)
    allocation: AllocationInfo = Field(default_factory=AllocationInfo)


class OrderInfo(BaseModel):
    """Order Agent output and persistent order metadata."""

    order_id: Optional[str] = None
    order_items: list[OrderItemState] = Field(default_factory=list)
    special_instructions: Optional[str] = None
    parsed_successfully: bool = False


class WorkflowInfo(BaseModel):
    """Reserved for a future CEO/router; worker agents must not modify it."""

    current_step: Optional[WorkflowAction] = None
    next_action: Optional[WorkflowAction] = None
    workflow_status: WorkflowStatus = WorkflowStatus.PENDING
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class FinalResponse(BaseModel):
    """Reserved for a future orchestrator's API/customer-facing response."""

    status: Optional[str] = None
    message: Optional[str] = None
    order_summary: list[OrderItemState] = Field(default_factory=list)


class SharedState(BaseModel):
    """The single, serializable source of truth for an order workflow.

    ``inventory``, ``community``, and ``allocation`` results are nested per
    order item so multi-product orders never overwrite one another's results.
    Database sessions and ORM objects deliberately do not belong in state.
    """

    customer: CustomerInfo
    order: OrderInfo = Field(default_factory=OrderInfo)
    workflow: WorkflowInfo = Field(default_factory=WorkflowInfo)
    final_response: Optional[FinalResponse] = None
