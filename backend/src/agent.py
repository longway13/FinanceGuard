from typing import Dict, List, TypedDict, Any, Literal, Annotated
from langgraph.graph import StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langgraph.prebuilt import tools_condition
from openai import OpenAI
from langchain_openai import ChatOpenAI  
import os
import uuid
from dotenv import load_dotenv
from tool_dispute_simulator import simulate_dispute_tool
from tool_find_case import find_case_tool
from tool_chat_web import web_search_tool
import logging
import sys
import json
from flask import Flask, request, jsonify, Response, session

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask 웹 서버 생성
app = Flask(__name__)
app.secret_key = os.urandom(24)  # For session management

# Create upload directory
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "uploads")
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Define the state type for our agent
class AgentState(TypedDict):
    messages: Annotated[List, add_messages]
    file_obj: Any  # For file uploads
    error: str
    
# Path for formatting prompt
FORMAT_PROMPT_PATH = "../prompts/format_output.txt"

def create_legal_assistant_agent() -> StateGraph:
    """Create the LangGraph workflow for the legal assistant agent"""
    
    # Define the tools
    tools = [find_case_tool, simulate_dispute_tool, web_search_tool]
    
    # Create LangChain ChatOpenAI instance
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=1.0,
        openai_api_key=os.getenv('OPENAI_API_KEY')
    )
    
    # Bind tools to the LLM - this automatically handles tool descriptions
    llm_with_tools = llm.bind_tools(tools)
    
    # Define chatbot node using the bound LLM
    def chatbot(state: AgentState):
        # Get user messages
        messages = state["messages"]
        file_obj = state.get("file_obj")
        
        # Log if file is present
        if file_obj:
            logger.info("File object is present in chatbot node")
            logger.info(f"Messages structure: {type(messages)}, length: {len(messages)}")
            for i, msg in enumerate(messages):
                logger.info(f"Message {i}: {type(msg)}, content: {msg}")
        
        # Get user's last message - improved extraction logic
        last_user_message = None
        for msg in reversed(messages):
            # Handle dictionary format
            if isinstance(msg, dict) and msg.get("role") == "user":
                last_user_message = msg.get("content", "")
                logger.info(f"Extracted user message from dict: {last_user_message}")
                break
            # Handle object format
            elif hasattr(msg, "role") and msg.role == "user":
                if hasattr(msg, "content"):
                    last_user_message = msg.content
                    logger.info(f"Extracted user message from object: {last_user_message}")
                    break
            # Direct string format (fallback)
            elif isinstance(msg, str):
                last_user_message = msg
                logger.info(f"Extracted user message from string: {last_user_message}")
                break
        
        # Use the first message if extraction failed
        if last_user_message is None and messages and len(messages) > 0:
            if isinstance(messages[0], dict) and "content" in messages[0]:
                last_user_message = messages[0]["content"]
                logger.info(f"Fallback: Using first message content: {last_user_message}")
            elif hasattr(messages[0], "content"):
                last_user_message = messages[0].content
                logger.info(f"Fallback: Using first message content: {last_user_message}")
            elif isinstance(messages[0], str):
                last_user_message = messages[0]
                logger.info(f"Fallback: Using first message as string: {last_user_message}")
        
        logger.info(f"Final user query: {last_user_message}")
        
        # Use the bound LLM
        try:
            response = llm_with_tools.invoke(messages)
            logger.info(f"LLM response type: {type(response).__name__}")
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
            ai_message["tool_calls"] = response.tool_calls
            logger.info(f"Tool calls detected: {len(response.tool_calls)}")
            for tc in response.tool_calls:
                logger.info(f"Tool call: {tc.get('name') if isinstance(tc, dict) else tc.name}")
        else:
            # Check if we should force a tool call for simulation when file is present
            has_simulation_keywords = False
            if last_user_message:
                keywords = ["계약", "시뮬레이션", "해지", "분석", "검토"]
                has_simulation_keywords = any(keyword in last_user_message for keyword in keywords)
            
            if file_obj and (has_simulation_keywords or last_user_message is None):
                logger.info("Forcing simulation tool call based on file presence")
                query_text = last_user_message or "계약 해지 상황 시뮬레이션"
                
                # Store file_obj in state so it's accessible to the CustomToolNode
                ai_message["tool_calls"] = [{
                    "name": "simulate_dispute_tool",
                    "id": "forced_simulation",
                    "args": {"query": query_text, "file_obj": file_obj}
                }]
        
        return {"messages": [ai_message]}
    
    # Initialize OpenAI client (for formatter)
    client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    
    # Load format prompt from file
    with open(FORMAT_PROMPT_PATH, 'r', encoding='utf-8') as f:
        format_prompt = f.read()
    logger.info(f"Successfully loaded format prompt from {FORMAT_PROMPT_PATH}")
    
    
    # Override the ToolNode with a custom implementation that properly handles file objects
    class CustomToolNode(ToolNode):
        def __call__(self, state):
            # Get the messages from the state
            messages = state.get("messages", [])
            file_obj = state.get("file_obj")
            
            if file_obj:
                logger.info("File object is available in CustomToolNode")
            else:
                logger.warning("No file object available in CustomToolNode")
            
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
                tool = None
                for t in self.tools:
                    if t.name == tool_name:
                        tool = t
                        break
                
                if not tool:
                    logger.error(f"Tool not found: {tool_name}")
                    continue
                    
                try:
                    # Create a copy of args to avoid modifying the original
                    final_args = dict(tool_args) if isinstance(tool_args, dict) else {}
                    
                    # Special handling for simulation tool
                    if tool_name == "simulate_dispute_tool" and file_obj:
                        logger.info("Adding file_obj to simulation tool arguments")
                        # Add file_obj to the arguments
                        final_args["file_obj"] = file_obj
                        
                        # Make sure query is in args
                        if "query" not in final_args and isinstance(tool_args, dict):
                            final_args["query"] = tool_args.get("query", "계약서 시뮬레이션")
                            
                        logger.info(f"Final simulation args keys: {final_args.keys()}")
                        result = tool.invoke(final_args)
                        logger.info(f"Simulation result: {type(result)}")
                    else:
                        result = tool.invoke(tool_args)
                        
                    # Create a tool message
                    from langchain_core.messages import ToolMessage
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
    
    # Create formatter node for final responses
    def format_response(state: AgentState) -> AgentState:
        """Format the final response"""
        if state.get("error"):
            return state
            
        try:
            logger.info("Formatting final response...")
            messages = state["messages"]
            
            # If the last message doesn't have tool results, return as is
            if "tool_calls" not in messages[-1]:
                logger.info("No tool calls to format, returning as is")
                return state
            
            # Format results from tools
            last_message = messages[-1].content if messages[-1].content else "결과를 처리 중입니다."
            
            # Use format prompt from file to format response
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
    
    # Create the StateGraph
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("chatbot", chatbot)
    workflow.add_node("tools", CustomToolNode(tools=tools))  # Use our custom tool node
    workflow.add_node("formatter", format_response)
    
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

def process_query(query: str, pdf_path=None) -> dict:
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
                    "type": "simple_dialogue",
                    "response": f"PDF 파일을 열 수 없습니다: {str(e)}",
                    "status": "error",
                    "message": f"Could not open PDF file: {str(e)}"
                }
        elif query and any(keyword in query for keyword in ["계약", "시뮬레이션", "해지"]) and not pdf_path:
            return {
                "type": "simple_dialogue",
                "response": "계약서 분석을 위해서는 먼저 PDF 파일을 업로드해 주세요.",
                "status": "error",
                "message": "PDF file required for contract analysis"
            }
                    
        # Create the agent
        agent = create_legal_assistant_agent()
        
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
        
        # Extract the final response message
        final_messages = result.get("messages", [])
        
        if not final_messages:
            return {"type": "simple_dialogue", "response": "응답을 생성하지 못했습니다.", "status": "error", "message": "No response generated"}
        
        logger.info(f"Final messages count: {len(final_messages)}")
        for i, msg in enumerate(final_messages):
            msg_type = type(msg).__name__
            logger.info(f"Message {i}: type={msg_type}")
            if hasattr(msg, "content"):
                logger.info(f"Message {i} content length: {len(str(msg.content))}")
        
        # Look for ToolMessage with content as it contains the actual results
        for message in reversed(final_messages):
            if isinstance(message, object) and hasattr(message, "__class__") and message.__class__.__name__ == "ToolMessage":
                if hasattr(message, "content") and message.content:
                    tool_name = message.name if hasattr(message, "name") else "unknown"
                    logger.info(f"Found ToolMessage with name: {tool_name}")
                    
                    # Log the actual content structure for debugging
                    logger.info(f"Tool message content: {message.content[:200]}...")
                    
                    # Parse the content as JSON if possible
                    try:
                        content_str = message.content
                        content = json.loads(content_str)
                        logger.info(f"Parsed content structure: {type(content).__name__}, keys: {content.keys() if isinstance(content, dict) else 'N/A'}")
                        
                        # Handle different tool types with appropriate formats
                        if tool_name == "find_case_tool":
                            # First, check if content is already in the expected format
                            if isinstance(content, list) and content:
                                # Direct list of formatted cases
                                formatted_cases = content
                                logger.info(f"Found {len(formatted_cases)} cases in list format")
                                return process_formatted_cases(formatted_cases[0])
                                
                            # Check for various dictionary formats
                            elif isinstance(content, dict):
                                # Check for cases key
                                if "cases" in content:
                                    cases = content["cases"]
                                    if isinstance(cases, list) and cases:
                                        if isinstance(cases[0], str):
                                            # List of formatted case strings
                                            logger.info(f"Found {len(cases)} cases as strings")
                                            return process_formatted_cases(cases[0])
                                        elif isinstance(cases[0], dict):
                                            # List of case objects
                                            logger.info(f"Found {len(cases)} cases as objects")
                                            if "formatted_case" in cases[0]:
                                                return process_formatted_cases(cases[0]["formatted_case"])
                                            else:
                                                # Try to use any available case data
                                                case_data = cases[0]
                                                return {
                                                    "type": "cases",
                                                    "response": {
                                                        "title": case_data.get("case_name", case_data.get("title", "")),
                                                        "summary": case_data.get("summary", ""),
                                                        "key points": case_data.get("key_points", ""),
                                                        "judge result": case_data.get("judgment", case_data.get("result", ""))
                                                    },
                                                    "status": "success",
                                                    "message": "Response Successful"
                                                }
                                # Check for formatted_cases key
                                elif "formatted_cases" in content:
                                    formatted_cases = content["formatted_cases"]
                                    if isinstance(formatted_cases, list) and formatted_cases:
                                        logger.info(f"Found {len(formatted_cases)} formatted cases")
                                        return process_formatted_cases(formatted_cases[0])
                                # Single case data directly in the root
                                else:
                                    logger.info("Trying to extract case data from root object")
                                    return {
                                        "type": "cases",
                                        "response": {
                                            "title": content.get("case_name", content.get("title", "")),
                                            "summary": content.get("summary", ""),
                                            "key points": content.get("key_points", ""),
                                            "judge result": content.get("judgment", content.get("result", ""))
                                        },
                                        "status": "success",
                                        "message": "Response Successful"
                                    }
                            
                            # Fallback - try to parse the content as a single formatted case
                            logger.info("Using fallback case parsing method")
                            return process_formatted_cases(content_str)
                            
                        elif tool_name == "simulate_dispute_tool":
                            # Handle simulation results (format 2)
                            simulations = content.get("simulations", [])
                            if simulations:
                                formatted_simulations = []
                                for i, simulation in enumerate(simulations):
                                    # Extract situation, user, agent parts from the simulation text
                                    # Default values if parsing fails
                                    situation = ""
                                    user_part = ""
                                    agent_part = ""
                                    
                                    # Try to parse the simulation text
                                    if "상황:" in simulation:
                                        parts = simulation.split("상황:", 1)
                                        if len(parts) > 1:
                                            situation_parts = parts[1].split("\n\n", 1)
                                            if situation_parts:
                                                situation = situation_parts[0].strip()
                                    
                                    if "당신:" in simulation:
                                        parts = simulation.split("당신:", 1)
                                        if len(parts) > 1:
                                            user_parts = parts[1].split("\n\n", 1)
                                            if user_parts:
                                                user_part = user_parts[0].strip()
                                    
                                    if "보험사:" in simulation:
                                        parts = simulation.split("보험사:", 1)
                                        if len(parts) > 1:
                                            agent_part = parts[1].strip()
                                    
                                    formatted_simulations.append({
                                        "id": i,
                                        "situation": situation,
                                        "user": user_part,
                                        "agent": agent_part
                                    })
                                
                                return {
                                    "type": "simulation", 
                                    "simulations": formatted_simulations,
                                    "status": "success", 
                                    "message": "Response Successful"
                                }
                        
                        elif tool_name == "web_search_tool":
                            # Handle web search results (format 1)
                            results = content.get("results", [])
                            if results:
                                # Combine results into a coherent response
                                response_text = ""
                                for result in results:
                                    title = result.get("title", "")
                                    content_text = result.get("content", "")
                                    if title and content_text:
                                        response_text += f"{title}:\n{content_text}\n\n"
                                
                                return {
                                    "type": "simple_dialogue", 
                                    "response": response_text or content_str, 
                                    "status": "success", 
                                    "message": "Response Successful"
                                }
                            
                        # Return default format if specific handling not implemented
                        return {
                            "type": "simple_dialogue", 
                            "response": json.dumps(content, indent=2, ensure_ascii=False), 
                            "status": "success", 
                            "message": "Response Successful"
                        }
                            
                    except json.JSONDecodeError:
                        logger.error(f"Failed to decode JSON: {message.content[:100]}...")
                        # If not JSON, try to parse as formatted case directly
                        return process_formatted_cases(message.content)
        
        # If no ToolMessage with content, check for assistant messages
        for message in reversed(final_messages):
            # Handle both dictionary-like objects and other message types
            role = None
            content = None
            
            if hasattr(message, "role"):
                role = message.role
            elif isinstance(message, dict):
                role = message.get("role")
            
            if hasattr(message, "content"):
                content = message.content
            elif isinstance(message, dict) and "content" in message:
                content = message.get("content")
                
            if role == "assistant" and content:
                return {
                    "type": "simple_dialogue", 
                    "response": content, 
                    "status": "success", 
                    "message": "Response Successful"
                }
                
        # If we reach here, we couldn't find any useful content
        return {
            "type": "simple_dialogue", 
            "response": "응답을 생성하지 못했습니다. 다른 질문을 시도하거나, 계약서 관련 질문인 경우 '계약 해지 조항 분석해줘'와 같이 더 구체적으로 질문해 보세요.", 
            "status": "error", 
            "message": "No valid response content found"
        }
        
    except Exception as e:
        logger.error(f"Uncaught error during agent execution: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {
            "type": "simple_dialogue", 
            "response": f"시스템 오류: {str(e)}", 
            "status": "error", 
            "message": str(e)
        }

# Helper function to process formatted case text
def process_formatted_cases(formatted_case):
    """Extract structured data from a formatted case text"""
    logger.info("Processing formatted case text")
    
    # Default values
    title = ""
    summary = ""
    key_points = ""
    judge_result = ""
    
    try:
        # Check if it's already a dictionary
        if isinstance(formatted_case, dict):
            return {
                "type": "cases",
                "response": {
                    "title": formatted_case.get("title", ""),
                    "summary": formatted_case.get("summary", ""),
                    "key points": formatted_case.get("key_points", ""),
                    "judge result": formatted_case.get("judgment", formatted_case.get("result", ""))
                },
                "status": "success",
                "message": "Response Successful"
            }
            
        # Parse text format
        if "제목:" in formatted_case:
            parts = formatted_case.split("제목:", 1)
            if len(parts) > 1:
                title_part = parts[1].split("\n", 1)
                if title_part:
                    title = title_part[0].strip()
        
        if "요약:" in formatted_case:
            parts = formatted_case.split("요약:", 1)
            if len(parts) > 1:
                summary_part = parts[1].split("\n\n", 1)
                if summary_part:
                    summary = summary_part[0].strip()
                else:
                    # Try with single newline
                    summary_part = parts[1].split("\n", 1)
                    if summary_part:
                        summary = summary_part[0].strip()
        
        if "주요 쟁점:" in formatted_case:
            parts = formatted_case.split("주요 쟁점:", 1)
            if len(parts) > 1:
                key_points_part = parts[1].split("\n\n", 1)
                if key_points_part:
                    key_points = key_points_part[0].strip()
                else:
                    # Try with single newline
                    key_points_part = parts[1].split("\n", 1)
                    if key_points_part:
                        key_points = key_points_part[0].strip()
        
        if "판결:" in formatted_case:
            parts = formatted_case.split("판결:", 1)
            if len(parts) > 1:
                judge_result = parts[1].strip()
                
        # If we still don't have data, try to parse the whole text
        if not (title or summary or key_points or judge_result):
            logger.info("Trying alternative parsing")
            # Just use the entire text as summary if we can't parse it
            summary = formatted_case
                
        return {
            "type": "cases",
            "response": {
                "title": title,
                "summary": summary,
                "key points": key_points,
                "judge result": judge_result
            },
            "status": "success",
            "message": "Response Successful"
        }
    except Exception as e:
        logger.error(f"Error processing formatted case: {e}")
        return {
            "type": "simple_dialogue",
            "response": formatted_case,  # Return the raw text as fallback
            "status": "success",
            "message": "Showing raw case data"
        }

# Flask routes
@app.route('/', methods=['GET'])
def index():
    return '''
    <html>
    <head>
        <title>법률 조언 시스템</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; }
            h1 { color: #2c3e50; text-align: center; margin-bottom: 30px; }
            .container { display: flex; gap: 20px; }
            .query-section { flex: 3; padding: 20px; border: 1px solid #ddd; border-radius: 8px; }
            .upload-section { flex: 2; padding: 20px; border: 1px solid #ddd; border-radius: 8px; }
            .query-form { margin-bottom: 20px; }
            .query-input { width: 80%; padding: 10px; border: 1px solid #ccc; border-radius: 4px; }
            .submit-btn { padding: 10px 15px; background-color: #3498db; color: white; border: none; cursor: pointer; border-radius: 4px; }
            .submit-btn:hover { background-color: #2980b9; }
            .response-area { border: 1px solid #ddd; padding: 20px; min-height: 300px; max-height: 500px; overflow-y: auto; white-space: pre-wrap; border-radius: 4px; }
            .file-info { margin-top: 15px; padding: 10px; background-color: #f8f9fa; border-radius: 4px; }
            .file-status { color: #27ae60; font-weight: bold; }
            .dropzone { border: 2px dashed #ccc; border-radius: 5px; padding: 25px; text-align: center; margin: 15px 0; }
            .dropzone:hover { border-color: #3498db; background-color: #f8f9fa; }
            .case-title { font-weight: bold; font-size: 1.2em; color: #2c3e50; margin-bottom: 10px; }
            .case-section { margin-bottom: 15px; }
            .case-label { font-weight: bold; color: #3498db; }
            .simulation-item { margin-bottom: 20px; border-left: 4px solid #3498db; padding-left: 15px; }
            .simulation-situation { font-weight: bold; margin-bottom: 10px; }
            .simulation-dialog { margin-left: 15px; margin-bottom: 8px; }
        </style>
    </head>
    <body>
        <h1>법률 조언 시스템</h1>
        
        <div class="container">
            <div class="query-section">
                <h2>질의응답</h2>
                <div class="query-form">
                    <form id="queryForm">
                        <input type="text" id="queryInput" class="query-input" placeholder="예: '이 계약서에서 계약 해지 상황을 시뮬레이션해 줘' 또는 '최근 특허 침해 판례를 알려줘'" required>
                        <button type="submit" class="submit-btn">질문하기</button>
                    </form>
                </div>
                <h3>응답:</h3>
                <div id="responseArea" class="response-area">여기에 응답이 표시됩니다...</div>
            </div>
            
            <div class="upload-section">
                <h2>계약서 업로드</h2>
                <div class="dropzone" id="dropZone">
                    <p>PDF 파일을 여기에 끌어다 놓거나 클릭하여 업로드하세요</p>
                    <form id="uploadForm" enctype="multipart/form-data">
                        <input type="file" id="pdfFile" name="file" accept=".pdf" style="display:none">
                        <button type="button" id="selectFile" class="submit-btn">파일 선택</button>
                    </form>
                </div>
                <div class="file-info" id="fileInfo">
                    <span class="file-status">상태: </span>파일이 업로드되지 않았습니다.
                </div>
            </div>
        </div>

        <script>
            // Upload functionality
            const dropZone = document.getElementById('dropZone');
            const fileInput = document.getElementById('pdfFile');
            const selectFileBtn = document.getElementById('selectFile');
            const fileInfo = document.getElementById('fileInfo');
            const uploadForm = document.getElementById('uploadForm');
            
            // Open file dialog when clicking the select button
            selectFileBtn.addEventListener('click', () => {
                fileInput.click();
            });
            
            // Handle file selection
            fileInput.addEventListener('change', () => {
                if (fileInput.files.length > 0) {
                    uploadFile(fileInput.files[0]);
                }
            });
            
            // Drag and drop functionality
            dropZone.addEventListener('dragover', (e) => {
                e.preventDefault();
                dropZone.style.backgroundColor = '#f0f8ff';
            });
            
            dropZone.addEventListener('dragleave', () => {
                dropZone.style.backgroundColor = '';
            });
            
            dropZone.addEventListener('drop', (e) => {
                e.preventDefault();
                dropZone.style.backgroundColor = '';
                if (e.dataTransfer.files.length > 0) {
                    uploadFile(e.dataTransfer.files[0]);
                }
            });
            
            // Function to upload file
            function uploadFile(file) {
                if (!file.name.endsWith('.pdf')) {
                    alert('PDF 파일만 업로드 가능합니다.');
                    return;
                }
                
                const formData = new FormData();
                formData.append('file', file);
                
                fileInfo.innerHTML = '<span class="file-status">상태: </span>업로드 중...';
                
                fetch('/upload', {
                    method: 'POST',
                    body: formData,
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        fileInfo.innerHTML = `<span class="file-status">상태: </span>업로드 완료 - ${file.name}`;
                    } else {
                        fileInfo.innerHTML = `<span class="file-status">상태: </span>업로드 실패 - ${data.error || '알 수 없는 오류'}`;
                    }
                })
                .catch(error => {
                    fileInfo.innerHTML = `<span class="file-status">상태: </span>업로드 실패 - ${error.message}`;
                });
            }
            
            // Function to format case data
            function formatCaseData(caseData) {
                let formattedHtml = '';
                
                if (caseData.title) {
                    formattedHtml += `<div class="case-title">${caseData.title}</div>`;
                }
                
                if (caseData.summary) {
                    formattedHtml += `<div class="case-section"><span class="case-label">요약:</span> ${caseData.summary}</div>`;
                }
                
                if (caseData["key points"]) {
                    formattedHtml += `<div class="case-section"><span class="case-label">주요 쟁점:</span> ${caseData["key points"]}</div>`;
                }
                
                if (caseData["judge result"]) {
                    formattedHtml += `<div class="case-section"><span class="case-label">판결:</span> ${caseData["judge result"]}</div>`;
                }
                
                return formattedHtml || "판례 정보를 불러올 수 없습니다.";
            }
            
            // Function to format simulation data
            function formatSimulationData(simulations) {
                let formattedHtml = '';
                
                simulations.forEach((sim, index) => {
                    formattedHtml += `<div class="simulation-item">`;
                    
                    if (sim.situation) {
                        formattedHtml += `<div class="simulation-situation">상황 ${index + 1}: ${sim.situation}</div>`;
                    }
                    
                    if (sim.user) {
                        formattedHtml += `<div class="simulation-dialog"><strong>당신:</strong> ${sim.user}</div>`;
                    }
                    
                    if (sim.agent) {
                        formattedHtml += `<div class="simulation-dialog"><strong>보험사:</strong> ${sim.agent}</div>`;
                    }
                    
                    formattedHtml += '</div>';
                });
                
                return formattedHtml || "시뮬레이션 결과가 없습니다.";
            }
            
            // Query form handling
            document.getElementById('queryForm').addEventListener('submit', async function(e) {
                e.preventDefault();
                
                const query = document.getElementById('queryInput').value;
                const responseArea = document.getElementById('responseArea');
                
                responseArea.textContent = "처리 중...";
                
                try {
                    const response = await fetch('/api/user-query', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({ query: query }),
                    });
                    
                    const data = await response.json();
                    
                    // Handle different response types
                    switch (data.type) {
                        case "cases":
                            // Format case data as HTML
                            responseArea.innerHTML = formatCaseData(data.response);
                            break;
                            
                        case "simulation":
                            // Format simulation data as HTML
                            responseArea.innerHTML = formatSimulationData(data.simulations);
                            break;
                            
                        case "simple_dialogue":
                        default:
                            // Simple text response
                            responseArea.textContent = data.response;
                            break;
                    }
                } catch (error) {
                    responseArea.textContent = "오류가 발생했습니다: " + error;
                }
            });
        </script>
    </body>
    </html>
    '''

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"success": False, "error": "No file part"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"success": False, "error": "No selected file"}), 400
    
    if file and file.filename.endswith('.pdf'):
        try:
            # Generate unique filename to prevent collisions
            unique_filename = str(uuid.uuid4()) + '.pdf'
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            file.save(file_path)
            
            # Remove old file if exists
            if 'pdf_file_path' in session and os.path.exists(session['pdf_file_path']):
                try:
                    os.remove(session['pdf_file_path'])
                except:
                    pass
                    
            # Store the file path in session for later use
            session['pdf_file_path'] = file_path
            session['original_filename'] = file.filename
            
            return jsonify({"success": True, "filename": file.filename})
        except Exception as e:
            logger.error(f"Error saving file: {e}")
            return jsonify({"success": False, "error": str(e)}), 500
    else:
        return jsonify({"success": False, "error": "Only PDF files are allowed"}), 400

@app.route('/reset', methods=['POST'])
def reset_session():
    # Remove the stored file if it exists
    if 'pdf_file_path' in session:
        try:
            os.remove(session['pdf_file_path'])
        except:
            pass
    
    # Clear the session
    session.clear()
    return jsonify({"success": True})

@app.route('/api/user-query', methods=['POST'])
def user_query():
    # Get the query from JSON request
    if request.is_json:
        data = request.get_json()
        query = data.get("query")
    else:
        query = request.form.get("query")
    
    if not query:
        return jsonify({
            "type": "simple_dialogue", 
            "response": "쿼리가 제공되지 않았습니다.", 
            "status": "error", 
            "message": "Query not provided"
        }), 400
    
    try:
        # Get the file path from the session
        pdf_path = session.get('pdf_file_path')
        
        # Process the query with the file path
        response = process_query(query, pdf_path)
        
        response_data = json.dumps(response, ensure_ascii=False)
        return Response(response_data, content_type="application/json; charset=utf-8")
    except Exception as e:
        logger.error(f"Error processing query: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({
            "type": "simple_dialogue", 
            "response": f"오류: {str(e)}", 
            "status": "error", 
            "message": str(e)
        }), 500

# Keep the original query endpoint for backward compatibility
@app.route('/query', methods=['POST'])
def query_agent():
    return user_query()

# Example usage
if __name__ == "__main__":
    # Run as web server if executed directly
    print("Starting web server on http://127.0.0.1:5000")
    app.run(debug=True)
