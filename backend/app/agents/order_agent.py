import json
from app.services.gemini_services import ask_gemini
from app.agents.prompts import ORDER_AGENT_PROMPT
from app.schemas.order_schema import OrderExtraction
from app.schemas.state_schema import SharedState

from datetime import datetime

from sqlalchemy import select
from app.models.models import Product

def extract_order(customer_message: str, catalog: list[str]) -> OrderExtraction:
    """
    Takes a natural language message from a customer,
    uses the LLM to extract items, quantities, and deadlines,
    and returns a structured OrderExtraction Pydantic model.
    """
    
    current_date_str = datetime.now().strftime("%Y-%m-%d")
    date_context = f"\n\nCurrent Date: {current_date_str}\n"
    catalog_context = f"Our current catalog is: {', '.join(catalog)}. If the user mispells an item (like 'papd'), map it to the correct catalog item.\n"
    
    # Construct the full prompt by appending the required schema and the user's message
    schema_instructions = f"\n\nYour output must match this JSON schema exactly:\n{OrderExtraction.model_json_schema()}\n\n"
    user_input = f"Customer Message: '{customer_message}'"
    
    full_prompt = ORDER_AGENT_PROMPT + catalog_context + date_context + schema_instructions + user_input
    
    # Call Gemini
    raw_response = ask_gemini(full_prompt)
    
    # Clean up the response in case Gemini includes markdown like ```json ... ```
    cleaned_response = raw_response.strip()
    if cleaned_response.startswith("```json"):
        cleaned_response = cleaned_response[7:]
    if cleaned_response.endswith("```"):
        cleaned_response = cleaned_response[:-3]
    
    # Parse JSON and validate with Pydantic
    try:
        parsed_json = json.loads(cleaned_response.strip())
        validated_order = OrderExtraction(**parsed_json)
        return validated_order
    except Exception as e:
        # In a real production scenario, we'll add retry logic or fallback to human
        raise ValueError(f"Failed to parse order from LLM response. Error: {e}\nRaw Response: {raw_response}")

from langchain_core.runnables import RunnableConfig
from app.websocket.manager import manager

async def process_order_node(state: SharedState, config: RunnableConfig) -> dict:
    """
    LangGraph node for processing an order.
    Extracts the customer message from state and returns the parsed order data.
    """
    db = config["configurable"]["db"]
    messages = state.get("messages", [])
    if not messages:
        return {"order": {"error": "No messages found in state."}}
    
    # Assume the last message contains the customer query
    last_msg = messages[-1]
    last_message = getattr(last_msg, "content", last_msg.get("content", "")) if hasattr(last_msg, "get") else getattr(last_msg, "content", "")
    
    try:
        # Fetch catalog to help LLM correct spellings
        result = await db.execute(select(Product.name))
        catalog = result.scalars().all()
        
        extraction = extract_order(last_message, catalog)
        
        # Admin log
        if extraction.orders:
            items_str = ", ".join([f"{item.quantity} {item.item}" for item in extraction.orders])
            await manager.broadcast_admin_log("OrderAgent", f"Received new request for {items_str}")
            
        return {"order": {"extracted_items": extraction.model_dump()}}
    except Exception as e:
        return {"order": {"error": str(e)}}
