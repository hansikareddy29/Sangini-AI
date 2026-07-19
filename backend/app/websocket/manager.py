from fastapi import WebSocket
from typing import Dict, List, Set
import json
import logging

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        # Maps user_id to a list of active websocket connections (a user might have multiple tabs)
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.recent_admin_logs = []

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        logger.info(f"User {user_id} connected. Total active sessions for user: {len(self.active_connections[user_id])}")

    def disconnect(self, websocket: WebSocket, user_id: str):
        if user_id in self.active_connections:
            if websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)
            if len(self.active_connections[user_id]) == 0:
                del self.active_connections[user_id]
        logger.info(f"User {user_id} disconnected.")

    async def send_personal_message(self, message: str, user_id: str):
        if user_id in self.active_connections:
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_text(message)
                except Exception as e:
                    logger.error(f"Failed to send message to user {user_id}: {e}")

    async def broadcast(self, message: str):
        print(f"DEBUG: Broadcasting to {len(self.active_connections)} users")
        for user_id, connections in self.active_connections.items():
            for connection in connections:
                try:
                    await connection.send_text(message)
                    print(f"DEBUG: Successfully sent to {user_id}")
                except Exception as e:
                    print(f"DEBUG: Failed to broadcast to user {user_id}: {e}")

    async def broadcast_to_group(self, message: str, group_member_ids: List[str]):
        """
        Send a message only to the connected users in a specific group.
        group_member_ids should be a list of user_ids that belong to the group.
        """
        for user_id in group_member_ids:
            if user_id in self.active_connections:
                for connection in self.active_connections[user_id]:
                    try:
                        await connection.send_text(message)
                    except Exception as e:
                        logger.error(f"Failed to broadcast to group member {user_id}: {e}")

    async def broadcast_admin_log(self, agent: str, message: str):
        import datetime
        now = datetime.datetime.now().strftime("%H:%M:%S")
        log_entry = {
            "type": "admin_log",
            "agent": agent,
            "message": message,
            "timestamp": f"[{now}]"
        }
        self.recent_admin_logs.append(log_entry)
        if len(self.recent_admin_logs) > 50:
            self.recent_admin_logs.pop(0)
            
        payload = json.dumps(log_entry)
        await self.broadcast(payload)

manager = ConnectionManager()
