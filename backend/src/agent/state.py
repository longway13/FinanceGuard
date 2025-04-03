from typing import Annotated, Any, List
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

class AgentState(TypedDict):
    """Define the state structure for the agent workflows"""
    messages: Annotated[List, add_messages]
    file_obj: Any  # For file uploads
    error: str
