from typing import TypedDict, List, Dict, Any
from langchain_core.messages import BaseMessage

class AgentState(TypedDict):
    messages: List[BaseMessage]
    evidence: List[Dict[str, Any]]
    tools_used: List[str]
    confidence: str
    answer: str
