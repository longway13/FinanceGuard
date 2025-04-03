from typing import Dict, List, Any
from langchain_core.tools import tool
from pydantic import BaseModel, Field
from src.tools.highlight import ToxicClauseFinder, CaseLawRetriever, DocumentParser
import os
import json
import traceback
import logging
from ..config import CASE_DB_PATH, EMBEDDING_PATH, HIGHLIGHT_PROMPT_PATH, OPENAI_API_KEY, UPSTAGE_API_KEY, FORMAT_PROMPT_PATH

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Define schema for the toxic clause search tool
class ToxicClauseToolSchema(BaseModel):
    query: str = Field(..., description="User query about toxic clauses in contracts")
    file_obj: Any = Field(..., description="File object containing the contract document")

@tool(args_schema=ToxicClauseToolSchema, description="계약서 내의 독소조항들을 찾아 반환합니다. 사용자가 계약서에서 독소조항, 불공정한 조항, 일방적인 조항, 또는 위험 조항을 찾아달라고 요청할 때 사용하세요.")
def find_toxic_clauses_tool(query: str, file_obj: Any) -> List[Dict[str, Any]]:
    """
    Analyzes contract document to find toxic clauses based on user query.
    
    Args:
        query: The user's query about toxic clauses
        file_obj: The contract document file object to analyze
    
    Returns:
        A list of toxic clauses found in the document with English field names
    """
    try:
        logger.info(f"Finding toxic clauses for query: {query}")
        
        # Check if file_obj is None or invalid
        if file_obj is None:
            logger.error("File object is None")
            return [{"error": "계약서 파일이 없습니다. 파일을 먼저 업로드해주세요."}]
        
        # Ensure file pointer is at beginning
        if hasattr(file_obj, 'seek'):
            file_obj.seek(0)
            logger.info("Reset file pointer to beginning")
        else:
            logger.warning(f"File object does not have seek method. Type: {type(file_obj)}")
            
        # Parse document
        logger.info("Parsing document...")
        document_parser = DocumentParser(UPSTAGE_API_KEY)
        parse_result = document_parser.parse(file_obj)
        document_text = parse_result.get("content", {}).get("text", "")
        
        if not document_text:
            logger.error("Failed to extract text from document")
            return [{"error": "문서에서 텍스트를 추출할 수 없습니다."}]
        
        # Initialize the case retriever
        try:
            logger.info("Initializing case retriever...")
            case_retriever = CaseLawRetriever(
                case_db_path=CASE_DB_PATH,
                embedding_path=EMBEDDING_PATH
            )
            case_retriever.load_cases()
        except FileNotFoundError as e:
            logger.error(f"Error loading case database or embeddings: {e}")
            return [{"error": f"판례 데이터베이스 로딩 오류: {str(e)}"}]
        
        # Initialize the toxic clause finder
        logger.info("Initializing toxic clause finder...")
        toxic_finder = ToxicClauseFinder(
            openai_api_key=OPENAI_API_KEY,
            prompt_path=HIGHLIGHT_PROMPT_PATH,
            case_retriever=case_retriever
        )
        
        # Find toxic clauses in the document
        logger.info("Finding toxic clauses in document...")
        toxic_clauses = toxic_finder.find(document_text)
        
        if not toxic_clauses:
            logger.info("No toxic clauses found")
            return [{"message": "독소조항을 찾을 수 없습니다."}]
        
        # Convert the Korean keys to English keys
        logger.info("Converting Korean keys to English keys...")
        converted_clauses = []
        for item in toxic_clauses:
            converted_item = {
                "toxic_clause": item.get("독소조항", ""),
                "reason": item.get("이유", ""),
                "related_case_formatted": item.get("유사판례_정리", ""),
                "related_case_raw": item.get("유사판례_원문", ""),
                "similarity": item.get("유사도", 0.0)
            }
            converted_clauses.append(converted_item)
        
        logger.info(f"Successfully converted {len(converted_clauses)} toxic clauses")
        return converted_clauses
        
    except Exception as e:
        logger.error(f"Error in find_toxic_clauses_tool: {str(e)}")
        logger.error(traceback.format_exc())
        return [{"error": f"독소조항 분석 오류: {str(e)}"}]
