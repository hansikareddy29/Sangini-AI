from typing import Dict, Any
from langchain_core.runnables import RunnableConfig
from app.services.gemini_services import ask_gemini
from app.services.whatsapp_service import send_whatsapp_message
from app.schemas.state_schema import SharedState

async def generate_response_node(state: SharedState, config: RunnableConfig) -> Dict[str, Any]:
    """
    Synthesizes all structured data from the LangGraph agents into a natural language response.
    """
    customer_phone = config["configurable"].get("customer_phone")
    if not customer_phone:
        return state
        
    intent = state.get("intent", "GENERAL_CHAT")
    messages = state.get("messages", [])
    
    # Get the latest message
    latest_message = ""
    if messages:
        last = messages[-1]
        latest_message = getattr(last, "content", last.get("content", "")) if hasattr(last, "get") else getattr(last, "content", "")
    
    # Build a context summary based on what the agents have done
    context_str = ""
    
    if intent in ["PLACE_ORDER", "MODIFY_ORDER"]:
        order = state.get("order", {})
        inventory = state.get("inventory", {})
        allocation = state.get("allocation", {})
        
        if order.get("error"):
            context_str += f"Order Extraction Error: {order['error']}\n"
        
        if inventory.get("inventory_status"):
            context_str += "Inventory Check Results:\n"
            for item in inventory["inventory_status"]:
                status = item.get("status")
                name = item.get("product_name")
                req_qty = item.get("requested_quantity")
                prod_qty = item.get("need_to_produce", 0)
                context_str += f"- {name}: Requested {req_qty}, Status: {status}, Need to Produce: {prod_qty}\n"
                
        if "allocation_successful" in allocation:
            if allocation["allocation_successful"]:
                context_str += "Overall Production Allocation: Successful\n"
            else:
                context_str += "Overall Production Allocation: Failed (Not enough SHG capacity for some items)\n"
                
            if allocation.get("product_allocations"):
                context_str += "Detailed Allocations:\n"
                for pa in allocation["product_allocations"]:
                    status = "Successful" if pa.get("allocation_successful") else "Failed"
                    context_str += f"- {pa.get('product')}: {status} (Remaining quantity: {pa.get('remaining_quantity')})\n"
    
    prompt = f"""You are Sangini AI, an intelligent, business-focused assistant for a Women's Self Help Group.
Your goal is to reply to the user concisely and professionally, based on their latest message and the system context. YOU MUST ACT STRICTLY AS A PRODUCT ASSISTANT.

Customer's Latest Message: '{latest_message}'
Detected Intent: {intent}

Backend System Context:
{context_str}

Strict Instructions:
1. If the intent is GENERAL_CHAT, steering the conversation BACK TO OUR PRODUCTS (Pickles, Papads, etc.). DO NOT offer generic advice, philosophical quotes, or act like a therapist (e.g. NEVER say "we all make mistakes"). Keep it strictly business.
2. If the user placed or modified an order and there are NOT_FOUND items, politely ask them to clarify those specific items (e.g., spelling mistakes you couldn't resolve).
3. If the user placed or modified an order and all items are in stock (or reserved successfully), enthusiastically confirm their order concisely.
4. If some items are OUT_OF_STOCK and need to be produced, but allocation was successful, let them know it will take a little time to prepare their fresh items.
5. If allocation failed because of capacity, apologize and ask if they would accept a partial delivery or revised date.
6. Keep your response extremely concise (1-2 sentences maximum). DO NOT be overly chatty.
7. NEVER expose the raw system variables (like NOT_FOUND, need_to_produce). Translate them into natural conversational English.
8. LANGUAGE & SCRIPT INSTRUCTION: You MUST detect the native language of the Customer's Latest Message (e.g., Hindi, Telugu, Marathi). Even if the customer types their native language using the English alphabet (like Hinglish or Tenglish), you MUST reply in their proper native language using its PROPER NATIVE SCRIPT (e.g., Devanagari script for Hindi, Telugu script for Telugu). Do NOT reply in English or Romanized script unless the user's message is strictly and completely English.
"""

    try:
        msg = ask_gemini(prompt)
    except Exception:
        msg = "I'm having a little trouble understanding right now. Could you please try again?"
        
    db = config["configurable"].get("db")
    if db and customer_phone:
        from sqlalchemy import select
        from app.models.models import User, Message
        import uuid
        stmt = select(User).where(User.phone_number == customer_phone)
        result = await db.execute(stmt)
        user = result.scalars().first()
        if user:
            db_message = Message(
                id=uuid.uuid4(),
                sender_id=None,
                receiver_id=user.id,
                message=msg.strip(),
                message_type="text"
            )
            db.add(db_message)
            await db.commit()

    await send_whatsapp_message(customer_phone, msg.strip())
    
    # Broadcast order update if an order was processed in this turn
    order = state.get("order", {})
    if order.get("order_id") and db and customer_phone:
        from app.websocket.manager import manager
        import json
        stmt = select(User).where(User.phone_number == customer_phone)
        result = await db.execute(stmt)
        user = result.scalars().first()
        if user:
            payload = json.dumps({"type": "order_update", "order_id": order.get("order_id"), "status": "pending"})
            await manager.send_personal_message(payload, str(user.id))
    # We append the AI's response to the message history so context is kept!
    from langchain_core.messages import AIMessage
    
    # We return the new message to be appended by the reducer
    return {"messages": [AIMessage(content=msg.strip())]}
