import json
import logging
import os
import re
import uuid
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from pydantic import BaseModel

class SHGMessageRequest(BaseModel):
    user_id: str
    message: str
    is_private: bool

from app.database.connection import get_db
from app.websocket.manager import manager
from app.models.models import User, Message, SHG, Member, Order, OrderItem, Product
from sqlalchemy.orm import selectinload

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])

@router.post("/shg_message")
async def send_shg_message(request: SHGMessageRequest, db: AsyncSession = Depends(get_db)):
    stmt = select(Member).where(Member.user_id == request.user_id)
    result = await db.execute(stmt)
    member = result.scalars().first()
    
    if not member:
        return {"status": "error", "message": "Member not found"}
        
    import uuid
    import datetime
    
    if request.is_private:
        db_msg = Message(
            id=uuid.uuid4(),
            sender_id=request.user_id,
            receiver_id=None,
            message=request.message,
            message_type="text"
        )
        db.add(db_msg)
        await db.commit()
        
        history_stmt = select(Message).where(
            ((Message.sender_id == request.user_id) & (Message.receiver_id == None)) |
            ((Message.receiver_id == request.user_id) & (Message.group_id == None))
        ).order_by(Message.timestamp.asc())
        history_res = await db.execute(history_stmt)
        history_msgs = history_res.scalars().all()
        
        context_str = "\n".join([f"{'Member' if m.sender_id else 'AI'}: {m.message}" for m in history_msgs[-10:]])
        
        from app.services.gemini_services import ask_gemini
        prompt = f"You are Sangini AI, helping an SHG member named {member.name}. They just said: '{request.message}'. Here is the recent chat history:\n{context_str}\n\nRespond concisely and helpfully."
        try:
            ai_reply = ask_gemini(prompt)
        except:
            ai_reply = "I'm having trouble right now, please try again."
            
        ai_msg = Message(
            id=uuid.uuid4(),
            sender_id=None,
            receiver_id=request.user_id,
            message=ai_reply.strip(),
            message_type="text"
        )
        db.add(ai_msg)
        await db.commit()
        
        payload = json.dumps({
            "type": "shg_message",
            "to_phone": member.phone_number,
            "message": ai_reply.strip()
        })
        await manager.send_personal_message(payload, request.user_id)
        
        return {"status": "success"}
    else:
        db_msg = Message(
            id=uuid.uuid4(),
            sender_id=request.user_id,
            group_id=member.shg_id,
            message=request.message,
            message_type="text"
        )
        db.add(db_msg)
        await db.commit()
        
        payload = json.dumps({
            "type": "shg_message",
            "sender_id": str(request.user_id),
            "sender_name": member.name,
            "group_id": str(member.shg_id),
            "message": request.message
        })
        await manager.broadcast(payload)
        
        # Analyze message with Gemini for inventory updates
        try:
            from app.services.gemini_services import ask_gemini
            from app.models.models import Product, Inventory
            
            prompt = f"""You are Sangini AI, monitoring an SHG group chat.
Member '{member.name}' sent the following message: "{request.message}"

Did they report producing new items that need to be added to inventory?
If so, identify the item name and the quantity produced. Also, write a friendly confirmation message to them. You MUST write it in the language they used (e.g., if they wrote in English, reply in English). However, if they wrote in a mixed language like Hinglish (Hindi written in English alphabet), you MUST reply in proper Hindi using the Devanagari script (e.g. 'धन्यवाद अनीता, मैंने 30 आम के अचार कम्युनिटी इन्वेंट्री में जोड़ दिए हैं!').

Output your response ONLY in valid JSON format like this:
{{"is_inventory_update": true, "item": "Mango Pickles", "quantity": 30, "reply_message": "धन्यवाद अनीता, मैंने 30 आम के अचार कम्युनिटी इन्वेंट्री में जोड़ दिए हैं!"}}
or
{{"is_inventory_update": false}}"""

            ai_content = ask_gemini(prompt)
            match = re.search(r'\{.*\}', ai_content, re.DOTALL)
            if match:
                data = json.loads(match.group(0))
                if data.get("is_inventory_update"):
                    item_name = data.get("item")
                    quantity = data.get("quantity")
                    
                    prod_stmt = select(Product).where(Product.name.ilike(f"%{item_name}%"))
                    prod_res = await db.execute(prod_stmt)
                    product = prod_res.scalars().first()
                    
                    if product:
                        inv_stmt = select(Inventory).where(Inventory.product_id == product.id)
                        inv_res = await db.execute(inv_stmt)
                        inventory = inv_res.scalars().first()
                        if inventory:
                            inventory.available_quantity += int(quantity)
                            await db.commit()
                            
                            reply_text = data.get("reply_message", f"Thanks {member.name}, I've added {quantity} {product.name} to our community inventory!")
                            
                            ai_group_msg = Message(
                                id=uuid.uuid4(),
                                sender_id=None,
                                group_id=member.shg_id,
                                message=reply_text,
                                message_type="system"
                            )
                            db.add(ai_group_msg)
                            await db.commit()
                            
                            ai_payload = json.dumps({
                                "type": "shg_message",
                                "sender_id": "system",
                                "sender_name": "Sangini AI",
                                "group_id": str(member.shg_id),
                                "message": reply_text
                            })
                            await manager.broadcast(ai_payload)
                            
                            # Log to admin page
                            await manager.broadcast_admin_log("InventoryAgent", f"Processed inventory update: +{quantity} {product.name} (reported by {member.name})")
        except Exception as e:
            print(f"Failed to process AI group update: {e}")
        
        return {"status": "success"}

@router.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    await manager.connect(websocket, user_id)
    try:
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)
            
            # TODO: Integrate with LangGraph workflow
            
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)
        
@router.get("/users")
async def get_users(db: AsyncSession = Depends(get_db)):
    """Used by the frontend login screen to list available test users."""
    result = await db.execute(select(User))
    users = result.scalars().all()
    return [{"id": str(u.id), "name": u.name, "role": u.role, "phone_number": u.phone_number} for u in users]

@router.get("/history/{user_id}")
async def get_chat_history(user_id: str, db: AsyncSession = Depends(get_db)):
    """Get private chat history for a specific user"""
    # For a customer, this is their chat with Sangini AI (the system)
    # We will fetch messages where sender or receiver is this user
    result = await db.execute(
        select(Message)
        .where(
            ((Message.sender_id == user_id) & (Message.receiver_id == None) & (Message.group_id == None)) |
            ((Message.receiver_id == user_id) & (Message.group_id == None))
        )
        .order_by(Message.timestamp.asc())
    )
    messages = result.scalars().all()
    return [{
        "id": str(m.id),
        "sender_id": str(m.sender_id) if m.sender_id else "system",
        "message": m.message,
        "timestamp": m.timestamp.isoformat(),
        "type": m.message_type
    } for m in messages]

@router.get("/group_history/{group_id}")
async def get_group_chat_history(group_id: str, db: AsyncSession = Depends(get_db)):
    """Get chat history for a specific SHG group"""
    result = await db.execute(
        select(Message)
        .where(Message.group_id == group_id)
        .order_by(Message.timestamp.asc())
    )
    messages = result.scalars().all()
    return [{
        "id": str(m.id),
        "sender_id": str(m.sender_id) if m.sender_id else None,
        "message": m.message,
        "timestamp": m.timestamp.isoformat(),
        "type": m.message_type
    } for m in messages]

@router.get("/shg_history/{user_id}")
async def get_shg_history_by_user(user_id: str, db: AsyncSession = Depends(get_db)):
    """Get chat history for the SHG group that the given user belongs to"""
    stmt = select(Member).where(Member.user_id == user_id)
    result = await db.execute(stmt)
    member = result.scalars().first()
    
    if not member:
        return []
        
    result = await db.execute(
        select(Message, User)
        .outerjoin(User, Message.sender_id == User.id)
        .where(Message.group_id == member.shg_id)
        .order_by(Message.timestamp.asc())
    )
    rows = result.all()
    
    return [{
        "id": str(m.id),
        "sender_id": str(m.sender_id) if m.sender_id else "system",
        "sender_name": u.name if u else "Sangini AI",
        "message": m.message,
        "timestamp": m.timestamp.isoformat(),
        "type": m.message_type
    } for m, u in rows]

@router.get("/orders/{phone_number}")
async def get_customer_orders(phone_number: str, db: AsyncSession = Depends(get_db)):
    """Get orders for a specific customer phone number"""
    result = await db.execute(
        select(Order)
        .options(selectinload(Order.order_items).selectinload(OrderItem.product))
        .where(Order.customer_phone == phone_number)
        .order_by(Order.created_at.desc())
    )
    orders = result.scalars().all()
    
    return [{
        "id": str(o.id),
        "status": o.status,
        "deadline": o.deadline.isoformat() if o.deadline else None,
        "created_at": o.created_at.isoformat() if o.created_at else None,
        "items": [{
            "product_name": item.product.name,
            "quantity": item.quantity
        } for item in o.order_items]
    } for o in orders]
