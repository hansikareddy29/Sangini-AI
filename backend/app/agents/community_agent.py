import logging
from typing import Dict, Any
from datetime import datetime, time
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.models import Member, MemberProduct, Product, Allocation
from app.schemas.community_schema import CommunityAgentOutput, EligibleMember
from app.schemas.state_schema import SharedState

logger = logging.getLogger(__name__)

async def check_community_capacity(shared_state: SharedState, db: AsyncSession) -> dict:
    """
    Identifies SHG members capable of producing the requested products,
    calculates their remaining daily capacity, and determines if the community
    can fulfill the production needs for each product.
    """
    
    inventory_data = shared_state.get("inventory", {})
    inventory_status_list = inventory_data.get("inventory_status", [])
    
    community_results = {}
    
    start_of_today = datetime.combine(datetime.today(), time.min)
    
    for item in inventory_status_list:
        product_name = item.get("product_name")
        need_to_produce = item.get("need_to_produce", 0)
        
        if need_to_produce <= 0 or not product_name:
            continue
            
        # Query PostgreSQL to find members who can produce this product
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
            
            daily_capacity = mp.daily_capacity
            remaining_capacity = max(0, daily_capacity - today_allocated_quantity)
            
            all_products = [prod.product.name for prod in member.member_products if prod.product]
            
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
                    experience_level="Medium", 
                    priority=1
                )
            )
            total_capacity += remaining_capacity
            
        can_fulfill = need_to_produce <= total_capacity
        
        output = CommunityAgentOutput(
            eligible_members=eligible_members_list,
            available_member_count=len(eligible_members_list),
            total_capacity=total_capacity,
            need_to_produce=need_to_produce,
            can_fulfill=can_fulfill
        )
        
        community_results[product_name] = output.model_dump()
        
    return {"community": {"products": community_results}}
