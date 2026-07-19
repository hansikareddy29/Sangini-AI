import logging
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.allocation_service import process_allocations
from app.schemas.state_schema import SharedState

logger = logging.getLogger(__name__)

async def allocate_order(shared_state: SharedState, db: AsyncSession) -> dict:
   
    order_data = shared_state.get("order", {})
    community_data = shared_state.get("community", {})
    products_data = community_data.get("products", {})
    
    order_id = order_data.get("order_id", "")
    
    all_allocations = []
    overall_success = True
    
    try:
        from app.services.gemini_services import ask_gemini
        from app.websocket.manager import manager
        import json
        from app.models.models import Member, Message
        from sqlalchemy import select
        import uuid
        import datetime
        
        for product_name, p_data in products_data.items():
            need_to_produce = p_data.get("need_to_produce", 0)
            eligible_members = p_data.get("eligible_members", [])
            
            if need_to_produce <= 0:
                continue
                
            allocation_output = await process_allocations(
                order_id=order_id,
                product_name=product_name,
                need_to_produce=need_to_produce,
                eligible_members=eligible_members,
                db=db
            )
            
            if not allocation_output.allocation_successful:
                overall_success = False
            
            output_dict = allocation_output.model_dump()
            output_dict["product"] = product_name
            all_allocations.append(output_dict)
            
            if allocation_output.assignments:
                for assignment in allocation_output.assignments:
                    prompt = f"You are Sangini AI, a friendly coordinator for a Women's Self Help Group. Inform {assignment.member} that they have been allocated a new production task. They need to produce {assignment.allocated_quantity} units of {product_name} for order {order_id[:4] if order_id else 'New Order'}. Keep it encouraging, concise, and in 1-2 sentences."
                    try:
                        ai_message = ask_gemini(prompt)
                    except Exception as e:
                        logger.error(f"Error generating AI message: {e}")
                        ai_message = f"Hello {assignment.member}, please produce {assignment.allocated_quantity} units of {product_name} for order #{order_id[:4]}."
                    
                    stmt = select(Member).where(Member.id == uuid.UUID(assignment.member_id))
                    member_result = await db.execute(stmt)
                    member_record = member_result.scalars().first()
                    
                    if member_record and member_record.user_id:
                        db_message = Message(
                            id=uuid.uuid4(),
                            sender_id=None,
                            receiver_id=member_record.user_id,
                            message=ai_message.strip(),
                            message_type="text",
                            timestamp=datetime.datetime.utcnow()
                        )
                        db.add(db_message)
                        await db.flush()
                        
                        await manager.broadcast_admin_log("AllocationAgent", f"Allocated {assignment.allocated_quantity} {product_name} to {assignment.member}")
                        
                        payload = json.dumps({
                            "type": "shg_message",
                            "member": assignment.member,
                            "message": ai_message.strip(),
                            "product": product_name,
                            "quantity": assignment.allocated_quantity
                        })
                        await manager.send_personal_message(payload, str(member_record.user_id))
                        
        return {
            "allocation": {
                "allocation_successful": overall_success,
                "product_allocations": all_allocations
            }
        }
        
    except Exception as e:
        logger.error(f"Error in allocation agent: {e}")
        return {
            "allocation": {
                "allocation_successful": False,
                "reason": f"Agent error: {str(e)}",
                "product_allocations": []
            }
        }
