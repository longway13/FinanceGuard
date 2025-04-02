from typing import Dict, List, TypedDict, Any
from langgraph.graph import Graph, StateGraph
import numpy as np
from openai import OpenAI
import json
import os
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from highlight import CaseLawRetriever, DocumentParser, LLMHighlighter
import logging
from langchain_core.tools import tool
from pydantic import BaseModel, Field
import traceback


load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define schema for the simulation tool
class SimulationToolSchema(BaseModel):
    query: str = Field(..., description="User query about contract dispute simulation")
    file_obj: Any = Field(..., description="File object containing the contract document")

class SimulationState(TypedDict):
    query: str
    document_text: str
    toxic_clauses: List[dict]
    relevant_toxic_clauses: List[dict]  # Selected toxic clauses for simulations
    similar_cases: List[List[dict]]  # List of similar cases for each simulation
    selected_cases: List[dict]  # Selected cases for each simulation
    simulations: List[str]  # Results of each simulation
    error: str

def parse_document(state: SimulationState, document_parser: DocumentParser) -> SimulationState:
    """Parse the input PDF document"""
    try:
        # If document_text is already set, skip parsing
        if state.get("document_text"):
            logger.info("Document already parsed, skipping parse step")
            return state
            
        logger.info("Parsing document...")
        if not state.get("document_file"):
            state["error"] = "No document file provided"
            return state
            
        parse_result = document_parser.parse(state["document_file"])
        state["document_text"] = parse_result.get("content", {}).get("text", "")
        
        if not state["document_text"]:
            state["error"] = "Failed to extract text from document"
        
        return state
    except Exception as e:
        logger.error(f"Error parsing document: {e}")
        state["error"] = f"Document parsing error: {str(e)}"
        return state

def extract_toxic_clauses(state: SimulationState, llm_highlighter: LLMHighlighter) -> SimulationState:
    """Extract toxic clauses from the document text"""
    if state.get("error"):
        return state
        
    try:
        logger.info("Extracting toxic clauses...")
        highlight_result = llm_highlighter.highlight(state["document_text"])
        state["toxic_clauses"] = highlight_result
        
        if not state["toxic_clauses"]:
            state["error"] = "No toxic clauses found"
            
        return state
    except Exception as e:
        logger.error(f"Error extracting toxic clauses: {e}")
        state["error"] = f"Clause extraction error: {str(e)}"
        return state

def select_relevant_toxic_clauses(state: SimulationState, model: SentenceTransformer) -> SimulationState:
    """Select most relevant toxic clauses based on user query"""
    if state.get("error") or not state.get("toxic_clauses"):
        return state
        
    try:
        logger.info(f"Selecting relevant toxic clauses for query: {state['query']}")
        query_embedding = model.encode(state["query"])
        
        clause_similarities = []
        for clause in state["toxic_clauses"]:
            clause_text = clause.get("독소조항", "")
            if not clause_text:
                continue
                
            clause_embedding = model.encode(clause_text)
            similarity = np.dot(clause_embedding, query_embedding) / (
                np.linalg.norm(clause_embedding) * np.linalg.norm(query_embedding)
            )
            clause_similarities.append((clause, similarity))
        
        # Sort by similarity score
        clause_similarities.sort(key=lambda x: x[1], reverse=True)
        
        # Select top 2 most relevant toxic clauses for simulations
        state["relevant_toxic_clauses"] = [item[0] for item in clause_similarities[:2]]
        
        if not state["relevant_toxic_clauses"]:
            state["error"] = "Failed to find relevant toxic clauses"
            
        logger.info(f"Selected {len(state['relevant_toxic_clauses'])} relevant toxic clauses")
        return state
    except Exception as e:
        logger.error(f"Error selecting relevant toxic clauses: {e}")
        state["error"] = f"Clause selection error: {str(e)}"
        return state

def format_case(case_details: str, format_prompt: str, client: OpenAI) -> str:
    """Format case details using LLM"""
    try:
        logger.info("Formatting case details...")
        messages = [
            {"role": "system", "content": format_prompt},
            {"role": "user", "content": case_details}
        ]
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=1.0
        )
        
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Case formatting error: {str(e)}")
        return "판례 분석 실패"

def retrieve_cases_for_clauses(state: SimulationState, case_retriever: CaseLawRetriever, format_prompt: str, client: OpenAI) -> SimulationState:
    """Retrieve similar cases for each relevant toxic clause"""
    if state.get("error") or not state.get("relevant_toxic_clauses"):
        return state
        
    try:
        state["similar_cases"] = []
        
        # For each relevant toxic clause, find similar cases
        for toxic_clause in state["relevant_toxic_clauses"]:
            logger.info(f"Retrieving similar cases for toxic clause")
            clause_text = toxic_clause.get("독소조항", "")
            combined_query = f"{state['query']} {clause_text}"
            
            query_embedding = case_retriever.model.encode(combined_query)
            similarities = np.dot(case_retriever.case_embeddings, query_embedding) / (
                np.linalg.norm(case_retriever.case_embeddings, axis=1) * np.linalg.norm(query_embedding)
            )
            
            top_indices = np.argsort(similarities)[-10:][::-1]
            cases_for_clause = []
            
            for idx in top_indices:
                cases_for_clause.append({
                    "case": str(case_retriever.cases[idx]["value"]),
                    "similarity_score": float(similarities[idx]),
                    "index": idx,
                    "formatted_case": None  # We'll format only after selecting the best case
                })
                
            state["similar_cases"].append(cases_for_clause)
            
        logger.info(f"Retrieved similar cases for {len(state['similar_cases'])} toxic clauses")
        return state
    except Exception as e:
        logger.error(f"Error retrieving cases: {e}")
        state["error"] = f"Case retrieval error: {str(e)}"
        state["similar_cases"] = []
        return state

def select_best_cases(state: SimulationState, case_retriever: CaseLawRetriever, format_prompt: str, client: OpenAI) -> SimulationState:
    """Select the most relevant case for each set of similar cases and format them"""
    if state.get("error") or not state.get("similar_cases"):
        return state
        
    try:
        logger.info(f"Selecting best cases for query: {state['query']}")
        query_embedding = case_retriever.model.encode(state['query'])
        
        state["selected_cases"] = []
        
        for similar_cases_set in state["similar_cases"]:
            best_case = None
            highest_similarity = -1
            
            for case_data in similar_cases_set:
                case_text = str(case_data["case"])
                case_embedding = case_retriever.model.encode(case_text[:1024])
                
                similarity = np.dot(case_embedding, query_embedding) / (
                    np.linalg.norm(case_embedding) * np.linalg.norm(query_embedding)
                )
                
                if similarity > highest_similarity:
                    highest_similarity = similarity
                    best_case = case_data
            
            if best_case:
                # Format only the selected case
                formatted_case = format_case(best_case["case"], format_prompt, client)
                best_case["formatted_case"] = formatted_case
                state["selected_cases"].append(best_case)
                logger.info(f"Selected and formatted best case with similarity: {highest_similarity}")
            
        if not state["selected_cases"]:
            state["error"] = "Failed to select relevant cases"
            
        return state
    except Exception as e:
        logger.error(f"Error selecting best cases: {e}")
        state["error"] = f"Case selection error: {str(e)}"
        return state

def run_simulations(state: SimulationState, simulation_prompt: str, client: OpenAI) -> SimulationState:
    """Run dispute simulations for each toxic clause and selected case"""
    if state.get("error") or not state.get("selected_cases") or not state.get("relevant_toxic_clauses"):
        return state
        
    try:
        logger.info("Running dispute simulations...")
        state["simulations"] = []
        
        # Run a simulation for each toxic clause + case pair
        for i, (toxic_clause, selected_case) in enumerate(zip(
            state["relevant_toxic_clauses"][:len(state["selected_cases"])], 
            state["selected_cases"]
        )):
            toxic_clause_text = f"""
            독소조항:
            - 조항: {toxic_clause.get('독소조항', '')}
            - 이유: {toxic_clause.get('이유', '')}
            """
            
            # Use formatted case summary instead of raw case text
            case_summary = selected_case.get("formatted_case", "판례 분석 실패")
            
            context = f"""
                        1. 독소조항:
                        {toxic_clause_text}

                        2. 관련 판례:
                        {case_summary}
                      """
            
            messages = [
                {"role": "system", "content": simulation_prompt},
                {"role": "user", "content": context}
            ]
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",  
                messages=messages,
                temperature=1.0,
            )
            
            state["simulations"].append(response.choices[0].message.content.strip())
            logger.info(f"Completed simulation {i+1}")
        
        return state
    except Exception as e:
        logger.error(f"Error in simulations: {e}")
        state["error"] = f"Simulation error: {str(e)}"
        state["simulations"] = ["시뮬레이션을 실행하지 못했습니다."] * len(state.get("selected_cases", []))
        return state

def create_simulation_workflow(
    case_db_path: str,
    embedding_path: str,
    simulation_prompt_path: str,
    format_prompt_path: str,
    openai_api_key: str,
    upstage_api_key: str,
    highlight_prompt_path: str
) -> Graph:
    """Create the Langgraph workflow for dispute simulation"""
    
    # Load prompts
    with open(simulation_prompt_path, 'r', encoding='utf-8') as f:
        simulation_prompt = f.read()
    with open(format_prompt_path, 'r', encoding='utf-8') as f:
        format_prompt = f.read()
    
    # Initialize components
    case_retriever = CaseLawRetriever(case_db_path, embedding_path)
    case_retriever.load_cases()
    
    document_parser = DocumentParser(upstage_api_key)
    
    client = OpenAI(api_key=openai_api_key)
    
    llm_highlighter = LLMHighlighter(
        openai_api_key=openai_api_key,
        prompt_path=highlight_prompt_path,
        case_retriever=case_retriever
    )
    
    # Create the StateGraph
    workflow = StateGraph(SimulationState)
    
    # Add nodes
    workflow.add_node("parse", lambda state: parse_document(state, document_parser))
    workflow.add_node("extract", lambda state: extract_toxic_clauses(state, llm_highlighter))
    workflow.add_node("select_clauses", lambda state: select_relevant_toxic_clauses(state, case_retriever.model))
    workflow.add_node("retrieve", lambda state: retrieve_cases_for_clauses(state, case_retriever, format_prompt, client))
    workflow.add_node("select_cases", lambda state: select_best_cases(state, case_retriever, format_prompt, client))
    workflow.add_node("simulate", lambda state: run_simulations(state, simulation_prompt, client))
    
    # Add edges
    workflow.add_edge("parse", "extract")
    workflow.add_edge("extract", "select_clauses")
    workflow.add_edge("select_clauses", "retrieve")
    workflow.add_edge("retrieve", "select_cases")
    workflow.add_edge("select_cases", "simulate")
    
    # Set entry point
    workflow.set_entry_point("parse")
    
    return workflow.compile()

def run_simulation_from_file(
    file_obj,
    query: str,
    case_db_path: str,
    embedding_path: str,
    simulation_prompt_path: str,
    format_prompt_path: str,
    highlight_prompt_path: str
) -> Dict[str, Any]:
    """Run the simulation from a file object and query"""
    try:
        logger.info(f"Starting simulation for query: '{query}'")
        
        # Create workflow
        graph = create_simulation_workflow(
            case_db_path=case_db_path,
            embedding_path=embedding_path,
            simulation_prompt_path=simulation_prompt_path,
            format_prompt_path=format_prompt_path,
            openai_api_key=os.getenv('OPENAI_API_KEY'),
            upstage_api_key=os.getenv('UPSTAGE_API_KEY'),
            highlight_prompt_path=highlight_prompt_path
        )
        
        # Parse document first (outside the graph for simplicity with file handling)
        document_parser = DocumentParser(os.getenv('UPSTAGE_API_KEY'))
        parse_result = document_parser.parse(file_obj)
        document_text = parse_result.get("content", {}).get("text", "")
        
        if not document_text:
            return {"error": "Failed to extract text from document"}
        
        # Initial state
        initial_state = {
            "query": query,
            "document_text": document_text,
            "document_file": None,  # Not needed since we've already parsed
            "toxic_clauses": [],
            "relevant_toxic_clauses": [],
            "similar_cases": [],
            "selected_cases": [],
            "simulations": [],
            "error": ""
        }
        
        # Run graph
        result = graph.invoke(initial_state)
        
        # Check for errors
        if result.get("error"):
            logger.error(f"Graph execution completed with error: {result['error']}")
            return {"error": result["error"]}
        
        # Return results
        return {
            "simulations": result.get("simulations", []),
            "relevant_toxic_clauses": result.get("relevant_toxic_clauses", []),
            "selected_cases": result.get("selected_cases", [])
        }
        
    except Exception as e:
        logger.error(f"Uncaught error during graph execution: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {"error": f"실행 오류: {str(e)}"}
    
# Tool decorator for direct usage from other modules
@tool(args_schema=SimulationToolSchema, description="유저 쿼리와 계약 문서에 기반하여 계약 분쟁 시뮬레이션을 실행합니다.")
def simulate_dispute_tool(query: str, file_obj: Any) -> Dict[str, Any]:
    """Simulates a contract dispute scenario based on a contract document and user query."""
    try:
        logger.info(f"Running simulation for query: {query}")
        logger.info(f"File object type: {type(file_obj)}")
        
        if not file_obj:
            logger.error("No file object provided")
            return {"error": "계약서 파일이 제공되지 않았습니다. 파일을 업로드하세요."}
            
        # Ensure file is at beginning position
        try:
            if hasattr(file_obj, 'seek'):
                file_obj.seek(0)
                logger.info("File pointer reset to beginning")
        except Exception as e:
            logger.error(f"Error resetting file pointer: {e}")
        
        # If file_obj is a string (file path), open the file
        if isinstance(file_obj, str) and os.path.exists(file_obj):
            logger.info(f"Opening file from path: {file_obj}")
            file_obj = open(file_obj, 'rb')
        
        # Configuration paths
        CASE_DB_PATH = "../datasets/case_db.json"
        EMBEDDING_PATH = "../datasets/precomputed_embeddings.npz"
        SIMULATION_PROMPT_PATH = "../prompts/simulate_dispute.txt"
        FORMAT_PROMPT_PATH = "../prompts/format_output.txt"
        HIGHLIGHT_PROMPT_PATH = "../prompts/highlight_prompt.txt"
        
        # Check if paths exist
        for path in [CASE_DB_PATH, EMBEDDING_PATH, SIMULATION_PROMPT_PATH, FORMAT_PROMPT_PATH, HIGHLIGHT_PROMPT_PATH]:
            if not os.path.exists(path):
                logger.error(f"Path not found: {path}")
                return {"error": f"필요한 파일을 찾을 수 없습니다: {path}"}
        
        # Run simulation
        result = run_simulation_from_file(
            file_obj,
            query,
            CASE_DB_PATH,
            EMBEDDING_PATH,
            SIMULATION_PROMPT_PATH, 
            FORMAT_PROMPT_PATH,
            HIGHLIGHT_PROMPT_PATH
        )
        
        if "error" in result and result["error"]:
            logger.error(f"Simulation error: {result['error']}")
        else:
            logger.info("Simulation completed successfully")
            
        return result
    except Exception as e:
        logger.error(f"Error in simulation tool: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {"error": f"시뮬레이션 실행 중 오류 발생: {str(e)}"}

if __name__ == "__main__":
    # Configuration
    CASE_DB_PATH = "../datasets/case_db.json"
    EMBEDDING_PATH = "../datasets/precomputed_embeddings.npz"
    SIMULATION_PROMPT_PATH = "../prompts/simulate_dispute.txt"
    FORMAT_PROMPT_PATH = "../prompts/format_output.txt"
    HIGHLIGHT_PROMPT_PATH = "../prompts/highlight_prompt.txt"
    TEST_PDF_PATH = "/Users/limdongha/workspace/LegalFore/input_ex.pdf"  # 테스트용 PDF 파일 경로
    
    def run_test_simulation():
        logger.info("Starting test simulation...")
        
        # 테스트 쿼리
        test_query = "계약 해지 상황을 시뮬레이션해줘"
        
        try:
            # PDF 파일 열기
            with open(TEST_PDF_PATH, 'rb') as file_obj:
                # 시뮬레이션 실행
                result = run_simulation_from_file(
                    file_obj,
                    test_query,
                    CASE_DB_PATH,
                    EMBEDDING_PATH,
                    SIMULATION_PROMPT_PATH,
                    FORMAT_PROMPT_PATH,
                    HIGHLIGHT_PROMPT_PATH
                )
                
                # 결과 출력
                logger.info("\n=== Simulation Test Results ===")
                logger.info(f"Query: {test_query}")
                
                if "error" in result:
                    logger.error(f"Error: {result['error']}")
                    return
                
                # 관련 독소조항 출력
                logger.info("\n--- Relevant Toxic Clauses ---")
                for idx, clause in enumerate(result.get("relevant_toxic_clauses", []), 1):
                    logger.info(f"\nClause {idx}:")
                    logger.info(f"독소조항: {clause.get('독소조항', 'N/A')}")
                    logger.info(f"이유: {clause.get('이유', 'N/A')}")
                
                # 선택된 판례 출력
                logger.info("\n--- Selected Cases ---")
                for idx, case in enumerate(result.get("selected_cases", []), 1):
                    logger.info(f"\nCase {idx}:")
                    logger.info(f"Similarity Score: {case.get('similarity_score', 'N/A')}")
                    logger.info(f"Formatted Case: {case.get('formatted_case', 'N/A')}")
                
                # 시뮬레이션 결과 출력
                logger.info("\n--- Simulation Results ---")
                for idx, simulation in enumerate(result.get("simulations", []), 1):
                    logger.info(f"\nSimulation {idx}:")
                    logger.info(simulation)
                
        except FileNotFoundError:
            logger.error(f"Test PDF file not found at {TEST_PDF_PATH}")
        except Exception as e:
            logger.error(f"Test failed with error: {str(e)}")
            logger.error(traceback.format_exc())
    
    # 테스트 실행
    logger.info("=== Starting Langgraph Simulation Test ===")
    run_test_simulation()
    logger.info("=== Test Complete ===")
