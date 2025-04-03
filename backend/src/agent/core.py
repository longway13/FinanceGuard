import os
import json
import logging
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
from openai import OpenAI

# LangGraph imports
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import tools_condition
from langchain_core.messages import ToolMessage
from langchain_openai import ChatOpenAI
from src.config import FORMAT_PROMPT_PATH


# Local imports
from .state import AgentState
from .processors import extract_response_from_messages

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CustomToolNode:
    """Custom implementation of ToolNode that properly handles file objects"""
    
    def __init__(self, tools: list) -> None:
        self.tools = tools
        self.tools_dict = {tool.name: tool for tool in tools}
        
    def __call__(self, state):
        # Get the messages and file from the state
        messages = state.get("messages", [])
        file_obj = state.get("file_obj")
        
        if not messages:
            return state
            
        # Get the last message which should contain tool calls
        message = messages[-1]
        
        # Check if there are no tool calls
        if (not hasattr(message, "tool_calls") and 
            not (isinstance(message, dict) and message.get("tool_calls"))):
            return state
            
        # Extract tool calls
        tool_calls = (message.tool_calls if hasattr(message, "tool_calls") 
                     else message.get("tool_calls", []))
        
        # No tool calls found
        if not tool_calls:
            return state
            
        # Process each tool call
        results = []
        for tool_call in tool_calls:
            tool_name = tool_call.get("name") if isinstance(tool_call, dict) else tool_call.name
            tool_args = tool_call.get("args") if isinstance(tool_call, dict) else tool_call.args
            tool_id = tool_call.get("id") if isinstance(tool_call, dict) else tool_call.id
            
            logger.info(f"Executing tool: {tool_name}")
            
            # Find the right tool
            tool = self.tools_dict.get(tool_name)
            
            if not tool:
                logger.error(f"Tool not found: {tool_name}")
                continue
                
            try:
                # Create a copy of args to avoid modifying the original
                final_args = dict(tool_args) if isinstance(tool_args, dict) else {}
                
                # Special handling for simulation tool
                if tool_name == "simulate_dispute_tool" and file_obj:
                    logger.info("Adding file_obj to simulation tool arguments")
                    final_args["file_obj"] = file_obj
                    
                    # Make sure query is in args
                    if "query" not in final_args and isinstance(tool_args, dict):
                        final_args["query"] = tool_args.get("query", "계약서 시뮬레이션")
                        
                    result = tool.invoke(final_args)
                else:
                    result = tool.invoke(tool_args)
                    
                # Create a tool message
                results.append(
                    ToolMessage(
                        content=json.dumps(result, ensure_ascii=False),
                        name=tool_name,
                        tool_call_id=tool_id,
                    )
                )
            except Exception as e:
                logger.error(f"Error executing tool {tool_name}: {e}")
                import traceback
                logger.error(traceback.format_exc())
                
                # For simulation errors, return a more helpful message
                if tool_name == "simulate_dispute_tool":
                    error_msg = {
                        "simulations": [
                            f"계약서 분석 중 오류가 발생했습니다: {str(e)}",
                            "파일이 올바르게 업로드되었는지 확인하시고, 다시 시도해 주세요."
                        ]
                    }
                    results.append(
                        ToolMessage(
                            content=json.dumps(error_msg, ensure_ascii=False),
                            name=tool_name,
                            tool_call_id=tool_id,
                        )
                    )
                else:
                    results.append(
                        ToolMessage(
                            content=f"Error: {str(e)}",
                            name=tool_name,
                            tool_call_id=tool_id,
                        )
                    )
        
        return {"messages": results}

def create_formatter(format_prompt_path=FORMAT_PROMPT_PATH):
    """Create a response formatter function"""
    
    # Initialize OpenAI client
    client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    
    # Load format prompt from file
    try:
        with open(format_prompt_path, 'r', encoding='utf-8') as f:
            format_prompt = f.read()
        logger.info(f"Successfully loaded format prompt from {format_prompt_path}")
    except Exception as e:
        logger.error(f"Failed to load format prompt: {e}")
        format_prompt = "Summarize the following information in a clear, concise manner:"
    
    def format_response(state: AgentState) -> AgentState:
        """Format the final response"""
        if state.get("error"):
            return state
            
        try:
            logger.info("Formatting final response...")
            messages = state["messages"]
            
            # If the last message doesn't have tool results, return as is
            if not messages or (hasattr(messages[-1], "tool_calls") and not messages[-1].tool_calls):
                logger.info("No tool calls to format, returning as is")
                return state
            
            # Format results from tools
            last_message_content = messages[-1].content if hasattr(messages[-1], "content") else ""
            last_message = last_message_content if last_message_content else "결과를 처리 중입니다."
            
            # Use format prompt to format response
            try:
                messages_for_formatting = [
                    {"role": "system", "content": format_prompt},
                    {"role": "user", "content": last_message}
                ]
                
                summary_response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=messages_for_formatting,
                    temperature=0.7,
                )
                
                formatted_response = summary_response.choices[0].message.content.strip()
                messages.append({"role": "assistant", "content": formatted_response})
                logger.info("Successfully formatted response")
            except Exception as e:
                logger.error(f"Error formatting response: {e}")
                messages.append({"role": "assistant", "content": f"결과 포맷팅 실패: {str(e)}"})
            
            return {"messages": messages}
        except Exception as e:
            logger.error(f"Error in format_response: {e}")
            state["error"] = f"포맷팅 오류: {str(e)}"
            state["messages"].append({"role": "assistant", "content": "응답 생성 중 오류가 발생했습니다."})
            return state
            
    return format_response

def create_chatbot_node(tools):
    """Create the chatbot node for the agent"""
    
    # Create LangChain ChatOpenAI instance
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=1.0,
        openai_api_key=os.getenv('OPENAI_API_KEY')
    )
    
    # Bind tools to the LLM
    llm_with_tools = llm.bind_tools(tools)
    
    def chatbot(state: AgentState):
        # Get user messages
        messages = state["messages"]
        file_obj = state.get("file_obj")
        
        # Log if file is present
        if file_obj:
            logger.info("File object is present in chatbot node")
        
        # Get user's last message - improved extraction logic
        last_user_message = None
        for msg in reversed(messages):
            # Handle dictionary format
            if isinstance(msg, dict) and msg.get("role") == "user":
                last_user_message = msg.get("content", "")
                break
            # Handle object format
            elif hasattr(msg, "role") and msg.role == "user":
                if hasattr(msg, "content"):
                    last_user_message = msg.content
                    break
            # Direct string format (fallback)
            elif isinstance(msg, str):
                last_user_message = msg
                break
        
        # Use the first message if extraction failed
        if last_user_message is None and messages and len(messages) > 0:
            if isinstance(messages[0], dict) and "content" in messages[0]:
                last_user_message = messages[0]["content"]
            elif hasattr(messages[0], "content"):
                last_user_message = messages[0].content
            elif isinstance(messages[0], str):
                last_user_message = messages[0]
        
        # Log the message before processing
        logger.info(f"Processing message: {last_user_message}")
        
        # Use the bound LLM
        try:
            response = llm_with_tools.invoke(messages)
            # Log the response for debugging
            logger.info("LLM Response:")
            logger.info(f"Response type: {type(response)}")
            logger.info(f"Response content: {response.content if hasattr(response, 'content') else response}")
            if hasattr(response, "tool_calls"):
                logger.info(f"Tool calls: {response.tool_calls}")
        except Exception as e:
            logger.error(f"Error invoking LLM: {e}")
            response = {"content": "Unable to process the query. Please try again."}
        
        # Convert LangChain message format to the format expected by the state
        ai_message = {
            "role": "assistant",
            "content": response.content if hasattr(response, "content") else str(response),
        }
        
        # If there are tool calls, add them to the message
        if hasattr(response, "tool_calls") and response.tool_calls:
            logger.info(f"Adding tool calls to message: {response.tool_calls}")
            ai_message["tool_calls"] = response.tool_calls
        else:
            logger.info("No tool calls in response")
        
        return {"messages": [ai_message]}
    
    return chatbot

def create_legal_assistant_agent(tools) -> StateGraph:
    """Create the LangGraph workflow for the legal assistant agent"""
    
    # Create nodes
    chatbot_node = create_chatbot_node(tools)
    tool_node = CustomToolNode(tools=tools)
    formatter_node = create_formatter()
    
    # Create the StateGraph
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("chatbot", chatbot_node)
    workflow.add_node("tools", tool_node)
    workflow.add_node("formatter", formatter_node)
    
    # Define edges using tools_condition from langgraph.prebuilt
    workflow.add_conditional_edges(
        "chatbot",
        tools_condition,
    )
    
    # Edge from tools to formatter
    workflow.add_edge("tools", "formatter")
    
    # Set entry point
    workflow.set_entry_point("chatbot")
    
    return workflow.compile()

def process_query(query: str, tools: List, pdf_path: Optional[str] = None) -> dict:
    """Process a user query and return the response in the appropriate format"""
    try:
        logger.info(f"Processing query: '{query}'")
        file_obj = None
        
        # Open file if path is provided and exists
        if pdf_path and os.path.exists(pdf_path):
            try:
                file_obj = open(pdf_path, 'rb')
                logger.info(f"Opened PDF file: {pdf_path}")
            except Exception as e:
                logger.error(f"Error opening PDF file: {e}")
                return {
                    "type": "error",
                    "response": f"PDF 파일을 열 수 없습니다: {str(e)}",
                    "status": "error",
                    "message": f"Could not open PDF file: {str(e)}"
                }
                    
        # Create the agent
        agent = create_legal_assistant_agent(tools)
        
        # Initial state with messages
        initial_state = {
            "messages": [{"role": "user", "content": query}],
            "file_obj": file_obj,
            "error": ""
        }
        
        # Run the agent
        result = agent.invoke(initial_state)
        logger.info(f"Agent execution completed, result keys: {result.keys()}")
        
        # Close file if opened
        if file_obj:
            file_obj.close()
        
        # Extract the final response
        return extract_response_from_messages(result.get("messages", []))
        
    except Exception as e:
        logger.error(f"Uncaught error during agent execution: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {
            "type": "error", 
            "response": f"시스템 오류: {str(e)}", 
            "status": "error", 
            "message": str(e)
        }
