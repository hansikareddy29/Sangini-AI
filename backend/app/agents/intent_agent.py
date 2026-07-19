import json
from app.services.gemini_services import ask_gemini
from app.schemas.state_schema import SharedState
from pydantic import BaseModel, Field

class IntentClassification(BaseModel):
    intent: str = Field(..., description="The classified intent: PLACE_ORDER, MODIFY_ORDER, STATUS_QUERY, or GENERAL_CHAT")
    explanation: str = Field(..., description="Brief explanation of why this intent was chosen")

def classify_intent(messages: list) -> str:
    """
    Uses the LLM to classify the user's intent based on the conversation history.
    """
    if not messages:
        return "GENERAL_CHAT"
        
    # Format the conversation history for the prompt
    history_str = ""
    for msg in messages:
        role = getattr(msg, "type", msg.get("role", "unknown")) if hasattr(msg, "get") else getattr(msg, "type", "user")
        content = getattr(msg, "content", msg.get("content", "")) if hasattr(msg, "get") else getattr(msg, "content", "")
        history_str += f"{role.upper()}: {content}\n"

    prompt = f"""You are the Intent Routing Agent for Sangini AI, a platform that helps Women Self Help Groups (SHGs) manage their businesses.

Your job is to analyze the conversation history and determine the user's CURRENT intent based on their latest message.

Categories:
1. PLACE_ORDER: The user is placing a new order or asking to buy something for the first time.
2. MODIFY_ORDER: The user is adding to, removing from, or changing an existing order (e.g. "add 12 papads", "make it 20 instead").
3. STATUS_QUERY: The user is asking about the status of their order or when it will be delivered.
4. GENERAL_CHAT: The user is just saying hello, asking a general question, or saying thank you.

Your output must be EXACTLY valid JSON matching this schema:
{IntentClassification.model_json_schema()}

Conversation History:
{history_str}
"""

    raw_response = ask_gemini(prompt)
    
    cleaned_response = raw_response.strip()
    if cleaned_response.startswith("```json"):
        cleaned_response = cleaned_response[7:]
    if cleaned_response.endswith("```"):
        cleaned_response = cleaned_response[:-3]
        
    try:
        parsed = json.loads(cleaned_response.strip())
        return parsed.get("intent", "GENERAL_CHAT")
    except Exception as e:
        return "GENERAL_CHAT"

async def intent_node(state: SharedState) -> dict:
    """
    LangGraph node for detecting user intent.
    """
    intent = classify_intent(state.get("messages", []))
    return {"intent": intent}
