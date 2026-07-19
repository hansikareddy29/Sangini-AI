from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database.connection import get_db
from app.models.models import Order, OrderStatus, OrderItem, Allocation
from app.websocket.manager import manager

router = APIRouter(prefix="/admin", tags=["admin"])

@router.get("/stats")
async def get_admin_stats(db: AsyncSession = Depends(get_db)):
    """
    Get live statistics for the Admin Dashboard.
    """
    # Active orders (not completed or cancelled)
    active_orders_stmt = select(func.count(Order.id)).where(
        Order.status.not_in([OrderStatus.completed, OrderStatus.cancelled])
    )
    active_result = await db.execute(active_orders_stmt)
    active_orders = active_result.scalar() or 0

    # Pending allocations (pending or inventory_reserved)
    pending_allocations_stmt = select(func.count(Order.id)).where(
        Order.status.in_([OrderStatus.pending, OrderStatus.inventory_reserved])
    )
    pending_result = await db.execute(pending_allocations_stmt)
    pending_allocations = pending_result.scalar() or 0

    # SHG Members Online (Count of users currently connected via WebSocket)
    # We can estimate this by checking the number of connections in manager.
    shg_members_online = len(manager.active_connections)

    return {
        "active_orders": active_orders,
        "shg_members_online": shg_members_online,
        "pending_allocations": pending_allocations
    }

from sqlalchemy.orm import selectinload

@router.get("/orders")
async def get_active_orders(db: AsyncSession = Depends(get_db)):
    """
    Get detailed information about active orders and their allocations.
    """
    stmt = (
        select(Order)
        .where(Order.status.not_in([OrderStatus.completed, OrderStatus.cancelled]))
        .options(
            selectinload(Order.order_items).selectinload(OrderItem.product),
            selectinload(Order.order_items).selectinload(OrderItem.allocations).selectinload(Allocation.member)
        )
        .order_by(Order.created_at.desc())
    )
    result = await db.execute(stmt)
    orders = result.scalars().all()
    
    response_data = []
    for order in orders:
        order_dict = {
            "id": str(order.id),
            "customer_phone": order.customer_phone,
            "status": order.status,
            "created_at": order.created_at.isoformat() if order.created_at else None,
            "items": []
        }
        for item in order.order_items:
            item_dict = {
                "product_name": item.product.name if item.product else "Unknown",
                "quantity": item.quantity,
                "allocations": []
            }
            for allocation in item.allocations:
                item_dict["allocations"].append({
                    "member_name": allocation.member.name if allocation.member else "Unknown",
                    "allocated_quantity": allocation.allocated_quantity,
                    "status": allocation.status
                })
            order_dict["items"].append(item_dict)
        response_data.append(order_dict)
        
    return response_data
