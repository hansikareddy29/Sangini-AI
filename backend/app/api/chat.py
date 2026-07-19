import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.database.connection import get_db
from app.websocket.manager import manager
from app.models.models import User, Message, SHG, Member, Order, OrderItem, Product
from sqlalchemy.orm import selectinload

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])

@router.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    await manager.connect(websocket, user_id)
    try:
        while True:
            data = await websocket.receive_text()
            # We can process incoming messages directly here, or we can handle them
            # via a REST API. For the hackathon, we'll process chat texts here!
            payload = json.loads(data)
            
            # Example payload: {"type": "text", "content": "I need 50 laptops"}
            # In a real app, we'd save this to the DB and trigger the LangGraph workflow here.
            
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
