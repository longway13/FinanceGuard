import json
import logging
from typing import Dict, Any
import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

def extract_response_from_messages(final_messages, logger=logger):
    """Extract appropriate response data from the agent's final messages"""
    
    if not final_messages:
        return {"type": "simple_dialogue", "response": "응답을 생성하지 못했습니다.", "status": "error", "message": "No response generated"}
    
    # Log message structure
    logger.info(f"Final messages count: {len(final_messages)}")
    
    # Look for ToolMessage with content as it contains the actual results
    for message in reversed(final_messages):
        if isinstance(message, object) and hasattr(message, "__class__") and message.__class__.__name__ == "ToolMessage":
            if hasattr(message, "content") and message.content:
                tool_name = message.name if hasattr(message, "name") else "unknown"
                logger.info(f"Found ToolMessage with name: {tool_name}")
                
                # Parse the content as JSON if possible
                try:
                    content_str = message.content
                    content = json.loads(content_str)
                    
                    # Handle different tool types
                    if tool_name == "find_case_tool":
                        return process_find_case_result(content)
                    elif tool_name == "simulate_dispute_tool":
                        return process_simulation_result(content)
                    elif tool_name == "web_search_tool":
                        return process_web_search_result(content)
                    
                    # Default format
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

def process_find_case_result(content):
    """Process find_case_tool results"""
    # First, check if content is already in the expected format
    if isinstance(content, list) and content:
        # Direct list of formatted cases
        formatted_cases = content
        return process_formatted_cases(formatted_cases[0])
            
    # Check for various dictionary formats
    elif isinstance(content, dict):
        # Check for cases key
        if "cases" in content:
            cases = content["cases"]
            if isinstance(cases, list) and cases:
                if isinstance(cases[0], str):
                    # List of formatted case strings
                    return process_formatted_cases(cases[0])
                elif isinstance(cases[0], dict):
                    # List of case objects
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
                return process_formatted_cases(formatted_cases[0])
        # Single case data directly in the root
        else:
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
    return process_formatted_cases(str(content))

def process_simulation_result(content):
    """Process simulate_dispute_tool results"""
    simulations = content.get("simulations", [])
    print(simulations)
    if not simulations:
        return {
            "type": "simple_dialogue", 
            "response": "시뮬레이션 결과가 없습니다.", 
            "status": "error", 
            "message": "No simulation results"
        }
        
    formatted_simulations = []
    for i, simulation in enumerate(simulations):
        # Default values
        situation = ""
        user_part = ""
        agent_part = ""
        
        # Remove ``` from start and end of the text if present
        simulation = simulation.strip()
        simulation = simulation.replace("```", "")
        
        pattern = r'상황:\s*(.*?)\s*사용자:\s*"?(.*?)"?\s*상담원:\s*"?(.*?)"?\s*$'
        match = re.search(pattern, simulation, re.DOTALL)
        
        formatted_simulations.append({
            "id": i,
            "situation": match.group(1).strip() if match else "",
            "user": match.group(2).strip() if match else "",
            "agent": match.group(3).strip() if match else ""
        })
    
    return {
        "type": "simulation", 
        "simulations": formatted_simulations,
        "status": "success", 
        "message": "Response Successful"
    }

def process_web_search_result(content):
    """Process web_search_tool results"""
    results = content.get("results", [])
    if not results:
        return {
            "type": "simple_dialogue", 
            "response": "검색 결과가 없습니다.", 
            "status": "error", 
            "message": "No search results"
        }
    
    # Combine results into a coherent response
    response_text = ""
    for result in results:
        title = result.get("title", "")
        content_text = result.get("content", "")
        if title and content_text:
            response_text += f"{title}:\n{content_text}\n\n"
    
    return {
        "type": "simple_dialogue", 
        "response": response_text or json.dumps(content, ensure_ascii=False), 
        "status": "success", 
        "message": "Response Successful"
    }
