import logging
from typing import Dict, Any
from datetime import datetime, time
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.models import Member, MemberProduct, Product, Allocation
from app.schemas.community_schema import CommunityAgentOutput, EligibleMember

logger = logging.getLogger(__name__)

async def check_community_capacity(shared_state: Dict[str, Any], db: AsyncSession) -> Dict[str, Any]:
    """
    Identifies SHG members capable of producing the requested product,
    calculates their remaining daily capacity, and determines if the community
    can fulfill the production needs.
    """
    
    # 1. Extract inputs from shared state
    order_data = shared_state.get("order", {})
    inventory_data = shared_state.get("inventory", {})
    
    product_name = order_data.get("product")
    need_to_produce = inventory_data.get("need_to_produce", 0)
    
    # Edge Case 3: Need to produce is zero. Return immediately. No database query required.
    if need_to_produce <= 0:
        return {"community": CommunityAgentOutput(
            eligible_members=[],
            available_member_count=0,
            total_capacity=0,
            need_to_produce=0,
            can_fulfill=True
        ).model_dump()}
        
    if not product_name:
        # Invalid input, cannot fulfill
        return {"community": CommunityAgentOutput(
            eligible_members=[],
            available_member_count=0,
            total_capacity=0,
            need_to_produce=need_to_produce,
            can_fulfill=False
        ).model_dump()}

    # 2. Query PostgreSQL to find members who can produce the requested product and are available
    # Join MemberProduct with Member and Product
    stmt = (
        select(MemberProduct)
        .join(Member)
        .join(Product)
        .options(selectinload(MemberProduct.member).selectinload(Member.member_products).selectinload(MemberProduct.product))
        .where(
            Product.name.ilike(f"%{product_name}%"),
            Member.availability == True
        )
    )
    
    result = await db.execute(stmt)
    capable_member_products = result.scalars().all()
    
    eligible_members_list = []
    total_capacity = 0
    
    # Get the start of today for allocation filtering
    start_of_today = datetime.combine(datetime.today(), time.min)

    # 3. For every eligible member calculate capacity and workload
    for mp in capable_member_products:
        member = mp.member
        
        # Calculate today's allocations
        alloc_stmt = (
            select(
                func.coalesce(func.sum(Allocation.allocated_quantity), 0),
                func.count(Allocation.id)
            )
            .where(
                Allocation.member_id == member.id,
                Allocation.created_at >= start_of_today
            )
        )
        
        alloc_result = await db.execute(alloc_stmt)
        today_allocated_quantity, today_allocations_count = alloc_result.first()
        
        # We use MemberProduct.daily_capacity as the member's capacity for this specific product
        daily_capacity = mp.daily_capacity
        
        # Formula: remaining_capacity = daily_capacity - today_allocated_quantity
        remaining_capacity = daily_capacity - today_allocated_quantity
        
        # Edge Case 4: Remaining capacity becomes negative. Treat it as zero.
        if remaining_capacity < 0:
            remaining_capacity = 0
            
        # Get all products this member can produce
        all_products = [prod.product.name for prod in member.member_products if prod.product]
        
        # Add to eligible members list
        eligible_members_list.append(
            EligibleMember(
                member_id=str(member.id),
                name=member.name,
                phone=member.phone_number or "N/A",
                status="Available",
                products=all_products,
                daily_capacity=daily_capacity,
                current_workload=today_allocated_quantity,
                remaining_capacity=remaining_capacity,
                today_allocations=today_allocations_count,
                experience_level="Medium", # Defaulting for now
                priority=1 # Defaulting for now
            )
        )
        
        # 4. Calculate total capacity
        total_capacity += remaining_capacity
        
    # Edge Case 1: No eligible members
    if not eligible_members_list:
        return {"community": CommunityAgentOutput(
            eligible_members=[],
            available_member_count=0,
            total_capacity=0,
            need_to_produce=need_to_produce,
            can_fulfill=False
        ).model_dump()}
        
    # 5. Determine can_fulfill
    can_fulfill = need_to_produce <= total_capacity
    
    # 6. Return all information required by the Allocation Agent
    output = CommunityAgentOutput(
        eligible_members=eligible_members_list,
        available_member_count=len(eligible_members_list),
        total_capacity=total_capacity,
        need_to_produce=need_to_produce,
        can_fulfill=can_fulfill
    )
    
    return {"community": output.model_dump()}
