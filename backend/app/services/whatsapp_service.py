import os
import httpx
import logging

logger = logging.getLogger(__name__)

META_ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN", "dummy_token")
META_PHONE_NUMBER_ID = os.getenv("META_PHONE_NUMBER_ID", "dummy_phone_id")
META_API_VERSION = "v19.0"

import json
import logging
from app.websocket.manager import manager

logger = logging.getLogger(__name__)

async def send_whatsapp_message(to_phone: str, message: str) -> bool:
    """
    Sends a message. Originally this hit the WhatsApp Meta API. 
    Now, it broadcasts to the custom frontend via WebSockets.
    """
    print(f"DEBUG: Broadcasting message to {to_phone}: {message}")
    logger.info(f"Broadcasting message to {to_phone}: {message}")
    
    payload = json.dumps({
        "type": "agent_message",
        "to_phone": to_phone,
        "message": message
    })
    
    print(f"DEBUG: Active connections in manager: {manager.active_connections}")
    
    # Broadcast to all connected clients; the frontend will filter by active chat
    await manager.broadcast(payload)
    print("DEBUG: Broadcast successful")
    
    return True

