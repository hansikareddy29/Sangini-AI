from typing import TypedDict, Any, List, Dict, Annotated
from langgraph.graph.message import add_messages

class SharedState(TypedDict, total=False):
    """
    The central state object passed between agents in the LangGraph workflow.
    Each agent reads from required sections and outputs updates to its specific section.
    """
    intent: str
    order: Dict[str, Any]
    inventory: Dict[str, Any]
    community: Dict[str, Any]
    allocation: Dict[str, Any]
    duplicate_check: Dict[str, Any]
    approval: Dict[str, Any]
    feasibility: Dict[str, Any]
    messages: Annotated[List[Any], add_messages]
