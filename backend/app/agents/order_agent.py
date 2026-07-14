import json
from app.services.gemini_services import ask_gemini
from app.agents.prompts import ORDER_AGENT_PROMPT
from app.schemas.order_schema import OrderExtraction

from datetime import datetime

def extract_order(customer_message: str) -> OrderExtraction:
    """
    Takes a natural language message from a customer,
    uses the LLM to extract items, quantities, and deadlines,
    and returns a structured OrderExtraction Pydantic model.
    """
    
    current_date_str = datetime.now().strftime("%Y-%m-%d")
    date_context = f"\n\nCurrent Date: {current_date_str}\n"
    
    # Construct the full prompt by appending the required schema and the user's message
    schema_instructions = f"\n\nYour output must match this JSON schema exactly:\n{OrderExtraction.model_json_schema()}\n\n"
    user_input = f"Customer Message: '{customer_message}'"
    
    full_prompt = ORDER_AGENT_PROMPT + date_context + schema_instructions + user_input
    
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
