import uuid
import logging
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.models import Allocation, OrderItem, Product
from app.schemas.allocation_schema import AllocationOutput, AllocationAssignment
from config.allocation_config import WEIGHTS

logger = logging.getLogger(__name__)

def _get_experience_score(exp: str) -> int:
    exp_lower = exp.lower() if exp else ""
    if exp_lower == "high": return 3
    if exp_lower == "medium": return 2
    if exp_lower == "low": return 1
    return 2 # default

def _get_priority_score(priority: int) -> int:
    # 1=3, 2=2, 3=1
    if priority == 1: return 3
    if priority == 2: return 2
    if priority == 3: return 1
    return 2 # default

async def process_allocations(
    order_id: str,
    product_name: str,
    need_to_produce: int,
    eligible_members: List[Dict[str, Any]],
    db: AsyncSession
) -> AllocationOutput:
    
    # Early exits
    if need_to_produce <= 0:
        return AllocationOutput(allocation_successful=True, remaining_quantity=0)
        
    if not eligible_members:
        return AllocationOutput(
            allocation_successful=False,
            reason="No eligible members available",
            remaining_quantity=need_to_produce
        )

    # 1. Calculate Scores
    scored_members = []
    for member in eligible_members:
        remaining_cap = member.get("remaining_capacity", 0)
        if remaining_cap <= 0:
            continue # Edge Cases 4 & 5
            
        exp_score = _get_experience_score(member.get("experience_level"))
        prio_score = _get_priority_score(member.get("priority"))
        workload = member.get("current_workload", 0)
        
        # Step 5: Score formula
        score = (
            remaining_cap * WEIGHTS.get("remaining_capacity", 0) +
            exp_score * WEIGHTS.get("experience", 0) +
            workload * WEIGHTS.get("workload", 0) +
            prio_score * WEIGHTS.get("priority_bonus", 0)
        )
        
        member_id = member.get("member_id")
        member_id_str = str(member_id) if member_id else ""
        
        scored_members.append({
            "member_id": member_id_str,
            "name": member.get("name"),
            "remaining_capacity": remaining_cap,
            "workload": workload,
            "score": score
        })

    if not scored_members:
        return AllocationOutput(
            allocation_successful=False,
            reason="All eligible members are at full capacity",
            remaining_quantity=need_to_produce
        )

    # 2. Sort members (Score DESC, Capacity DESC, Workload ASC, MemberID ASC)
    scored_members.sort(key=lambda x: (
        -x["score"],                     # DESC
        -x["remaining_capacity"],        # DESC
        x["workload"],                   # ASC
        x["member_id"]                   # ASC
    ))
    
    # 3. Greedy Allocation
    remaining = need_to_produce
    assignments = []
    
    for member in scored_members:
        if remaining <= 0:
            break
            
        allocated = min(member["remaining_capacity"], remaining)
        
        if allocated > 0:
            assignments.append(AllocationAssignment(
                member_id=member["member_id"],
                member=member["name"],
                allocated_quantity=allocated,
                score=round(member["score"], 2)
            ))
            remaining -= allocated

    # 4. Insert into Database
    order_item_id = None
    try:
        parsed_order_id = uuid.UUID(str(order_id))
        stmt = select(OrderItem.id).join(Product).where(
            OrderItem.order_id == parsed_order_id,
            Product.name.ilike(f"%{product_name}%")
        )
        result = await db.execute(stmt)
        order_item_id = result.scalars().first()
    except Exception as e:
        logger.warning(f"Failed to find order_item_id for order {order_id} product {product_name}: {e}")

    if order_item_id:
        try:
            for assign in assignments:
                new_allocation = Allocation(
                    order_item_id=order_item_id,
                    member_id=uuid.UUID(assign.member_id),
                    allocated_quantity=assign.allocated_quantity,
                    status="pending"
                )
                db.add(new_allocation)
            await db.commit()
        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to save allocations to DB: {e}")
            return AllocationOutput(
                allocation_successful=False,
                reason=f"Database error during allocation saving: {str(e)}",
                remaining_quantity=need_to_produce
            )

    allocation_successful = (remaining == 0)
    
    return AllocationOutput(
        assignments=assignments,
        remaining_quantity=remaining,
        allocation_successful=allocation_successful,
        reason=None if allocation_successful else "Not enough capacity to fully fulfill the order."
    )
