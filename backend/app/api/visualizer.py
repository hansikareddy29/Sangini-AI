import json
import logging
import asyncio
from typing import AsyncGenerator
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from langchain_core.messages import HumanMessage
import uuid

from app.database.connection import get_db
from app.workflows.main_workflow import graph
from app.schemas.state_schema import SharedState

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/visualizer", tags=["visualizer"])

async def event_generator(message: str, db: AsyncSession) -> AsyncGenerator[str, None]:
    thread_id = str(uuid.uuid4())
    customer_phone = "+910000000000" # Dummy customer phone for visualization

    state: SharedState = {
        "intent": "GENERAL_CHAT",
        "order": {},
        "inventory": {},
        "community": {},
        "allocation": {},
        "messages": [HumanMessage(content=message)]
    }
    
    config = {
        "configurable": {
            "customer_phone": customer_phone,
            "thread_id": thread_id,
            "db": db
        }
    }

    try:
        # We use stream_mode="updates" to get state updates after each node executes
        async for output in graph.astream(state, config=config, stream_mode="updates"):
            for node_name, node_state in output.items():
                
                if node_state is None:
                    node_state = {}

                # To handle AIMessage serialization properly
                serialized_state = {}
                for k, v in node_state.items():
                    if k == "messages":
                        serialized_state[k] = [
                            {"content": m.content, "type": m.type} if hasattr(m, "content") else str(m)
                            for m in v
                        ]
                    else:
                        serialized_state[k] = v
                
                payload = {
                    "node": node_name,
                    "state": serialized_state
                }
                
                # Format for Server-Sent Events (SSE)
                yield f"data: {json.dumps(payload)}\n\n"
                
                # Optional small delay so the frontend animation is visibly sequential
                await asyncio.sleep(1.0)
                
    except Exception as e:
        logger.error(f"Error in visualizer stream: {e}")
        yield f"data: {json.dumps({'error': str(e)})}\n\n"

@router.get("/stream")
async def stream_workflow(message: str, db: AsyncSession = Depends(get_db)):
    """
    Execute the workflow and stream the state updates via Server-Sent Events.
    """
    return StreamingResponse(
        event_generator(message, db),
        media_type="text/event-stream"
    )
