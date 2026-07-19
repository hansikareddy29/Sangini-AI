import os
import uuid
import logging
from typing import Dict, Any
from fastapi import APIRouter, Request, Response, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_db
from app.workflows.main_workflow import graph as workflow_graph
from app.schemas.state_schema import SharedState

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhook", tags=["WhatsApp"])

META_VERIFY_TOKEN = os.getenv("META_VERIFY_TOKEN", "sangini_secret_token")

# In-memory dictionary to store active threads mapping: phone_number -> thread_id
# For a production app, this would be in Redis or PostgreSQL.
ACTIVE_THREADS: Dict[str, str] = {}

@router.get("")
async def verify_webhook(request: Request):
    """
    Handles Meta's webhook verification challenge.
    """
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode and token:
        if mode == "subscribe" and token == META_VERIFY_TOKEN:
            logger.info("WEBHOOK_VERIFIED")
            return Response(content=challenge, status_code=200)
        else:
            raise HTTPException(status_code=403, detail="Verification token mismatch")
    
    raise HTTPException(status_code=400, detail="Missing parameters")

@router.post("")
async def receive_whatsapp_message(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Receives incoming WhatsApp messages from Meta.
    """
    # Parse the incoming JSON
    try:
        body = await request.json()
    except Exception:
        return Response(status_code=400)

    # We must return 200 OK to Meta immediately, but FastAPI will handle the response 
    # after processing. In a true production app, we'd use background tasks here.
    
    # Check if this is a WhatsApp status update or a message
    if body.get("object") == "whatsapp_business_account":
        for entry in body.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                
                # Check for messages
                if "messages" in value:
                    for message in value["messages"]:
                        # Extract the sender's phone number and the text
                        customer_phone = message.get("from")
                        msg_type = message.get("type")
                        
                        if msg_type == "text":
                            text = message.get("text", {}).get("body", "")
                            
                            # Prefix with '+' if Meta stripped it, or leave as is if we standardise
                            if not customer_phone.startswith("+"):
                                customer_phone = f"+{customer_phone}"
                            
                            logger.info(f"Received message from {customer_phone}: {text}")
                            
                            # Process the message through our orchestrator
                            await process_incoming_message(customer_phone, text, db)
                            
    return Response(status_code=200)

async def process_incoming_message(customer_phone: str, text: str, db: AsyncSession):
    """
    Routes the message to start a new LangGraph flow or resume a paused one.
    """
    thread_id = ACTIVE_THREADS.get(customer_phone)
    
    if thread_id:
        # Resume existing paused workflow
        logger.info(f"Resuming existing workflow {thread_id} for {customer_phone}")
        config = {
            "configurable": {
                "thread_id": thread_id,
                "db": db,
                "customer_phone": customer_phone
            }
        }
        
        # Check if the graph is actually paused
        state_info = workflow_graph.get_state(config)
        if len(state_info.next) == 0:
            logger.warning(f"Thread {thread_id} was not paused. Starting fresh.")
            # Clear it and start fresh
            del ACTIVE_THREADS[customer_phone]
            await start_new_workflow(customer_phone, text, db)
            return

        # Inject user message
        workflow_graph.update_state(
            config, 
            {"messages": [{"role": "user", "content": text}]}
        )
        
        # Resume
        await workflow_graph.ainvoke(None, config)
        
        # Check if it paused again
        new_state_info = workflow_graph.get_state(config)
        if len(new_state_info.next) == 0:
            # Completed! Clean up thread
            if customer_phone in ACTIVE_THREADS:
                del ACTIVE_THREADS[customer_phone]
    else:
        # Start new workflow
        await start_new_workflow(customer_phone, text, db)

async def start_new_workflow(customer_phone: str, text: str, db: AsyncSession):
    new_thread_id = str(uuid.uuid4())
    logger.info(f"Starting new workflow {new_thread_id} for {customer_phone}")
    
    initial_state: SharedState = {
        "messages": [{"role": "user", "content": text}],
        "order": {},
        "inventory": {},
        "community": {},
        "allocation": {}
    }
    
    config = {
        "configurable": {
            "thread_id": new_thread_id,
            "db": db,
            "customer_phone": customer_phone
        }
    }
    
    await workflow_graph.ainvoke(initial_state, config)
    
    # Check if it paused
    state_info = workflow_graph.get_state(config)
    if len(state_info.next) > 0:
        ACTIVE_THREADS[customer_phone] = new_thread_id
