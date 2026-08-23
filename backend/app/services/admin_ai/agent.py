from langgraph.graph import StateGraph, END
from app.services.admin_ai.schemas import AgentState
from app.services.admin_ai.graph import call_agent, call_tools, should_continue

# Initialize LangGraph state graph
workflow = StateGraph(AgentState)

# Add agent and tools node
workflow.add_node("agent", call_agent)
workflow.add_node("execute_tools", call_tools)

# Define edge pathways
workflow.set_entry_point("agent")
workflow.add_conditional_edges(
    "agent",
    should_continue,
    {
        "continue": "execute_tools",
        "end": END
    }
)
workflow.add_edge("execute_tools", "agent")

# Compile graph
compiled_graph = workflow.compile()

def run_admin_ai(message: str):
    """Entrypoint to execute the Admin AI BI agent graph.
    
    Args:
        message: The natural language question from the admin.
        
    Returns:
        A dict containing:
            answer: The generated explanation.
            evidence: List of tools outputs collected.
            tools_used: List of tool names called.
            confidence: Parse confidence level ('high', 'medium', 'low').
    """
    from langchain_core.messages import HumanMessage
    
    initial_state = {
        'messages': [HumanMessage(content=message)],
        'evidence': [],
        'tools_used': [],
        'confidence': 'low',
        'answer': ''
    }
    
    result = compiled_graph.invoke(initial_state)
    return {
        'answer': result.get('answer', ''),
        'evidence': result.get('evidence', []),
        'tools_used': result.get('tools_used', []),
        'confidence': result.get('confidence', 'low')
    }
