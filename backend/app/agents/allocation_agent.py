import logging
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.allocation_service import process_allocations

logger = logging.getLogger(__name__)

async def allocate_order(shared_state: Dict[str, Any], db: AsyncSession) -> Dict[str, Any]:
    """
    LangGraph Agent entrypoint for Allocation.
    Retrieves data from shared state and calls the allocation service.
    Operates deterministically without an LLM.
    """
    order_data = shared_state.get("order", {})
    inventory_data = shared_state.get("inventory", {})
    community_data = shared_state.get("community", {})
    
    order_id = order_data.get("order_id", "")
    product_name = order_data.get("product", "")
    need_to_produce = inventory_data.get("need_to_produce", 0)
    eligible_members = community_data.get("eligible_members", [])
    
    try:
        # Call the dedicated service layer
        allocation_output = await process_allocations(
            order_id=order_id,
            product_name=product_name,
            need_to_produce=need_to_produce,
            eligible_members=eligible_members,
            db=db
        )
        
        # Format the output for the shared state
        return {
            "allocation": allocation_output.model_dump()
        }
        
    except Exception as e:
        logger.error(f"Error in allocation agent: {e}")
        return {
            "allocation": {
                "allocation_successful": False,
                "reason": f"Agent error: {str(e)}",
                "remaining_quantity": need_to_produce,
                "assignments": []
            }
        }
