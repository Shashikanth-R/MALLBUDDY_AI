import os
import json
import logging
import re
from google import genai
from google.genai import types
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

from app.services.admin_ai.schemas import AgentState
from app.services.admin_ai.prompts import SYSTEM_PROMPT
from app.services.admin_ai.tools import TOOLS_MAP

logger = logging.getLogger(__name__)

def get_gemini_client():
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is not set")
    return genai.Client(api_key=api_key)

def call_agent(state: AgentState):
    """LangGraph node to invoke Gemini and decide tools or generate answer."""
    logger.info("Invoking Admin BI Agent node...")
    
    # Map messages to Gemini dict structure to be completely safe across SDK changes
    contents = []
    for msg in state['messages']:
        if isinstance(msg, HumanMessage):
            contents.append({"role": "user", "parts": [{"text": msg.content}]})
        elif isinstance(msg, AIMessage):
            parts = []
            if msg.content:
                parts.append({"text": msg.content})
            if msg.additional_kwargs.get('function_calls'):
                for fc in msg.additional_kwargs['function_calls']:
                    name = fc.name if hasattr(fc, 'name') else fc.get('name')
                    args = fc.args if hasattr(fc, 'args') else fc.get('args')
                    parts.append({
                        "function_call": {
                            "name": name,
                            "args": dict(args) if args else {}
                        }
                    })
            contents.append({"role": "model", "parts": parts})
        elif isinstance(msg, ToolMessage):
            contents.append({
                "role": "tool",
                "parts": [{
                    "function_response": {
                        "name": msg.name,
                        "response": {"result": msg.content}
                    }
                }]
            })

    # Define tools list for Gemini model
    tools_list = list(TOOLS_MAP.values())

    try:
        client = get_gemini_client()
        response = client.models.generate_content(
            model='models/gemini-3.6-flash',
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                tools=tools_list,
                temperature=0.0
            )
        )
    except Exception as e:
        logger.error(f"Gemini API invocation failed: {e}")
        # Carry tools_used and evidence through so prior call_tools results are preserved.
        return {
            'messages': [AIMessage(content="Error calling Gemini AI: " + str(e))],
            'answer': "Error calling Gemini AI. Evidence collected is returned below.",
            'confidence': 'low',
            'tools_used': list(state.get('tools_used', [])),
            'evidence': list(state.get('evidence', [])),
        }

    # Inspect function calls from model response
    function_calls = None
    if response.function_calls:
        function_calls = response.function_calls

    if function_calls:
        logger.info(f"Model requested tool calls: {[fc.name for fc in function_calls]}")
        # Model wants to call tools — do not emit tools_used/evidence yet; call_tools will update them.
        new_msg = AIMessage(content="", additional_kwargs={'function_calls': function_calls})
        return {'messages': [new_msg]}
    else:
        # Model generated final text response. Carry accumulated observability fields through.
        logger.info("Model generated final response")
        answer = response.text or ""

        # Parse confidence rating from answer
        match = re.search(r'CONFIDENCE\s*[:\n]?\s*(High|Medium|Low)', answer, re.IGNORECASE)
        confidence = match.group(1).lower() if match else 'low'

        new_msg = AIMessage(content=answer)
        return {
            'messages': [new_msg],
            'answer': answer,
            'confidence': confidence,
            'tools_used': list(state.get('tools_used', [])),
            'evidence': list(state.get('evidence', [])),
        }

def call_tools(state: AgentState):
    """LangGraph node to execute requested tools and record evidence."""
    last_message = state['messages'][-1]
    tool_messages = []
    evidence = list(state.get('evidence', []))
    tools_used = list(state.get('tools_used', []))

    if last_message.additional_kwargs.get('function_calls'):
        for fc in last_message.additional_kwargs['function_calls']:
            tool_name = fc.name if hasattr(fc, 'name') else fc.get('name')
            tool_args = fc.args if hasattr(fc, 'args') else fc.get('args')
            tool_args_dict = dict(tool_args) if tool_args else {}
            
            logger.info(f"Executing tool {tool_name} with args: {tool_args_dict}")
            
            # Execute tool safely
            if tool_name in TOOLS_MAP:
                try:
                    result = TOOLS_MAP[tool_name](**tool_args_dict)
                except Exception as e:
                    logger.error(f"Failed to execute tool {tool_name}: {e}")
                    result = json.dumps({"error": str(e)})
            else:
                logger.error(f"Requested tool {tool_name} not found in TOOLS_MAP")
                result = json.dumps({"error": f"Tool '{tool_name}' not supported"})

            # Append to evidence list
            try:
                parsed_res = json.loads(result)
            except Exception:
                parsed_res = result

            evidence.append({
                'tool': tool_name,
                'args': tool_args_dict,
                'result': parsed_res
            })
            
            if tool_name not in tools_used:
                tools_used.append(tool_name)

            tool_messages.append(ToolMessage(
                content=result,
                name=tool_name,
                tool_call_id=tool_name
            ))

    return {
        'messages': tool_messages,
        'evidence': evidence,
        'tools_used': tools_used
    }

def should_continue(state: AgentState) -> str:
    """Conditional edge router function."""
    last_message = state['messages'][-1]
    if last_message.additional_kwargs.get('function_calls'):
        return "continue"
    return "end"
