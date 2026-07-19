import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.models import Order, Allocation, OrderStatus, AllocationStatus

logger = logging.getLogger(__name__)

# Define allowed transitions as a dictionary mapping current state to allowed next states
ORDER_TRANSITIONS = {
    OrderStatus.pending: {OrderStatus.inventory_reserved, OrderStatus.rejected, OrderStatus.cancelled},
    OrderStatus.inventory_reserved: {OrderStatus.allocated, OrderStatus.partially_allocated, OrderStatus.replan_required, OrderStatus.cancelled},
    OrderStatus.allocated: {OrderStatus.in_production, OrderStatus.replan_required, OrderStatus.cancelled},
    OrderStatus.partially_allocated: {OrderStatus.replan_required, OrderStatus.allocated, OrderStatus.rejected, OrderStatus.cancelled},
    OrderStatus.replan_required: {OrderStatus.allocated, OrderStatus.rejected, OrderStatus.cancelled},
    OrderStatus.in_production: {OrderStatus.ready_for_delivery, OrderStatus.replan_required},
    OrderStatus.ready_for_delivery: {OrderStatus.completed},
    OrderStatus.completed: set(),
    OrderStatus.cancelled: set(),
    OrderStatus.rejected: set(),
}

ALLOCATION_TRANSITIONS = {
    AllocationStatus.assigned: {AllocationStatus.in_progress, AllocationStatus.declined, AllocationStatus.cancelled},
    AllocationStatus.in_progress: {AllocationStatus.completed, AllocationStatus.cancelled},
    AllocationStatus.completed: set(),
    AllocationStatus.declined: set(),
    AllocationStatus.cancelled: set(),
}

async def transition_order_state(
    order_id: str, 
    new_status: OrderStatus, 
    db: AsyncSession
) -> Order:
    """
    Validates and performs an order state transition.
    Throws a ValueError if the transition is invalid.
    """
    stmt = select(Order).where(Order.id == order_id)
    result = await db.execute(stmt)
    order = result.scalars().first()
    
    if not order:
        raise ValueError(f"Order {order_id} not found.")

    current_status = order.status
    if new_status not in ORDER_TRANSITIONS.get(current_status, set()):
        raise ValueError(f"Invalid transition for Order {order_id}: {current_status} -> {new_status}")
    
    logger.info(f"Transitioning Order {order_id}: {current_status} -> {new_status}")
    order.status = new_status
    await db.commit()
    
    # Broadcast to websocket
    from app.models.models import User
    from app.websocket.manager import manager
    import json
    user_result = await db.execute(select(User).where(User.phone_number == order.customer_phone))
    user = user_result.scalars().first()
    if user:
        payload = json.dumps({"type": "order_update", "order_id": str(order.id), "status": new_status})
        await manager.send_personal_message(payload, str(user.id))
    
    return order

async def transition_allocation_state(
    allocation_id: str, 
    new_status: AllocationStatus, 
    db: AsyncSession
) -> Allocation:
    """
    Validates and performs an allocation state transition.
    Throws a ValueError if the transition is invalid.
    """
    stmt = select(Allocation).where(Allocation.id == allocation_id)
    result = await db.execute(stmt)
    allocation = result.scalars().first()
    
    if not allocation:
        raise ValueError(f"Allocation {allocation_id} not found.")

    current_status = allocation.status
    if new_status not in ALLOCATION_TRANSITIONS.get(current_status, set()):
        raise ValueError(f"Invalid transition for Allocation {allocation_id}: {current_status} -> {new_status}")
    
    logger.info(f"Transitioning Allocation {allocation_id}: {current_status} -> {new_status}")
    allocation.status = new_status
    await db.commit()
    
    return allocation
