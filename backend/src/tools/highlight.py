import requests
from flask import Flask, request, jsonify
from openai import OpenAI
import json
import os
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
import numpy as np
from tqdm import tqdm
from collections import OrderedDict
from src.config import UPSTAGE_API_KEY, OPENAI_API_KEY, CASE_DB_PATH, HIGHLIGHT_PROMPT_PATH, FORMAT_PROMPT_PATH


load_dotenv()

class DocumentParser:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.url = "https://api.upstage.ai/v1/document-ai/document-parse"
    
    def parse(self, file_obj) -> dict:
        headers = {"Authorization": f"Bearer {self.api_key}"}
        files = {"document": file_obj}
        data = {
            "ocr": "force", 
            "coordinates": False, 
            "chart_recognition": True, 
            "output_formats": "['text']", 
            "base64_encoding": "[]", 
            "model": "document-parse" 
        }
        response = requests.post(self.url, headers=headers, files=files, data=data)
        # response.encoding = 'utf-8'
        return response.json()


class CaseLawRetriever:
    def __init__(self, case_db_path: str, embedding_path: str = None):
        self.case_db_path = case_db_path
        self.embedding_path = embedding_path or case_db_path.replace('.json', '_embeddings.npz')
        self.model = None
        self.cases = None
        self.case_embeddings = None
        self.case_texts = None
        
    def _init_model(self):
        if self.model is None:
            print("Loading sentence transformer model...")
            self.model = SentenceTransformer("nlpai-lab/KURE-v1")
    
    def load_cases(self):
        print("Loading case database...")
        with open(self.case_db_path, 'r', encoding='utf-8') as f:
            self.cases = json.load(f)
            
        # 미리 계산된 임베딩이 있는지 확인
        if os.path.exists(self.embedding_path):
            print("Loading pre-computed embeddings...")
            loaded = np.load(self.embedding_path, allow_pickle=True)
            self.case_texts = loaded['texts']
            self.case_embeddings = loaded['embeddings']
            self._init_model()  # 모델 초기화 추가
        else:
            # 기존 방식대로 실시간 계산
            self._init_model()
            print("Computing embeddings...")
            self.case_embeddings = []
            self.case_texts = []
            for case in tqdm(self.cases, desc="Processing cases"):
                self.case_texts.append(case['key'])
                self.case_embeddings.append(self.model.encode(case['key']))
            self.case_embeddings = np.array(self.case_embeddings)
            
            # Save embeddings for future use
            print("Saving embeddings for future use...")
            np.savez(
                self.embedding_path,
                texts=np.array(self.case_texts, dtype=object),
                embeddings=self.case_embeddings
            )
        
        print(f"Loaded {len(self.cases)} cases successfully")
    
    def find_similar_case(self, toxic_clause: str) -> dict:
        if self.model is None or self.cases is None:
            self.load_cases()
            
        if not isinstance(toxic_clause, str):
            raise ValueError(f"toxic_clause must be a string, got {type(toxic_clause)}")
            
        query_embedding = self.model.encode(toxic_clause)
        similarities = np.dot(self.case_embeddings, query_embedding) / (
            np.linalg.norm(self.case_embeddings, axis=1) * np.linalg.norm(query_embedding)
        )
        most_similar_idx = np.argmax(similarities)
        return {
            'case': self.cases[most_similar_idx]['value'],
            'similarity_score': float(similarities[most_similar_idx])
        }

class LLMHighlighter:
    def __init__(self, openai_api_key: str, prompt_path: str, case_retriever: CaseLawRetriever):
        self.prompt_path = prompt_path
        with open(prompt_path, 'r', encoding='utf-8') as f:
            self.system_prompt = f.read()
        self.client = OpenAI(api_key=openai_api_key)
        self.case_retriever = case_retriever
        with open(FORMAT_PROMPT_PATH, 'r', encoding='utf-8') as f:
            self.format_prompt = f.read()
    
    def format_case(self, case_details: str) -> str:  # 반환 타입을 dict에서 str로 변경
        """Format case details using LLM"""
        # Check if input is actually a legal case
        if not case_details or len(case_details.strip()) < 10:  # Arbitrary minimum length for valid legal text
            return "유효한 판례 정보가 필요합니다."
            
        # Check if the input appears to be a non-legal query
        if len(case_details.split()) < 5 and not any(legal_term in case_details for legal_term in ["판례", "법원", "계약", "조항"]):
            return "계약서 분석과 관련된 내용만 처리할 수 있습니다."
            
        messages = [
            {"role": "system", "content": self.format_prompt},
            {"role": "user", "content": case_details}
        ]
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=1.0
            )
            
            # LLM 응답을 그대로 문자열로 반환
            result = response.choices[0].message.content.strip()
            if not result:
                return "판례 분석 결과가 없습니다."
            return result
            
        except Exception as e:
            app.logger.error(f"Case formatting error: {str(e)}")
            return f"판례 분석 중 오류가 발생했습니다: {str(e)}"

    def highlight(self, text: str) -> list:
        """
        text: PDF 전체 텍스트
        반환: 독소 조항 분석 결과 리스트
        """
        print("Analyzing document with LLM...")
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": text}
        ]
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini", 
                messages=messages,
                temperature=1.0
            )
            
            result = response.choices[0].message.content
            # app.logger.info(f"Raw GPT response: {result}")  # 디버깅을 위한 로깅 추가
            
            # Remove code block markers if they exist
            result = result.replace('```json', '').replace('```', '').strip()
            
            # JSON 시작과 끝 위치 찾기
            start_idx = result.find('[')
            end_idx = result.rfind(']') + 1
            
            if (start_idx == -1 or end_idx == 0):
                app.logger.error("No JSON array found in response")
                return []
                
            # JSON 부분만 추출
            json_str = result[start_idx:end_idx]
            
            try:
                parsed_result = json.loads(json_str)
                if not isinstance(parsed_result, list):
                    app.logger.error("Parsed result is not a list")
                    return []
                
                print("Finding similar cases...")
                # 결과 재구성 - 키 순서 변경
                reordered_result = []
                for item in tqdm(parsed_result, desc="Finding similar cases"):
                    similar_case = self.case_retriever.find_similar_case(item["독소조항"])
                    # Format the case details
                    formatted_case = self.format_case(str(similar_case["case"]))
                    
                    reordered_item = {
                        "독소조항": item["독소조항"],
                        "이유": item["이유"],
                        "유사판례_정리": formatted_case,  # formatted_case는 이제 문자열
                        "유사판례_원문": similar_case["case"],
                        "유사도": similar_case["similarity_score"]
                    }
                    # OrderedDict를 사용하여 키 순서 보장
                    ordered_item = OrderedDict()
                    for key in ["독소조항", "이유", "유사판례_정리", "유사판례_원문", "유사도"]:
                        ordered_item[key] = reordered_item[key]
                    reordered_result.append(ordered_item)
                
                print("Analysis complete!")
                return reordered_result
                
            except json.JSONDecodeError as je:
                app.logger.error(f"JSON parsing error: {str(je)}")
                return []
            
        except Exception as e:
            app.logger.error(f"LLM Analysis error: {str(e)}")
            return []

##############################################
# Flask 웹 서버 및 /highlight 엔드포인트      #
##############################################
class OrderedJsonEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, OrderedDict):
            return {key: obj[key] for key in obj}
        return super().default(obj)

app = Flask(__name__)
app.json_encoder = OrderedJsonEncoder

API_KEY = UPSTAGE_API_KEY
# PROMPT_PATH = "/Users/limdongha/workspace/LegalFore/FinanceGuard/backend/prompts/highlight_prompt.txt"
# CASE_DB_PATH = "/Users/limdongha/workspace/LegalFore/FinanceGuard/backend/datasets/case_db.json"

document_parser = DocumentParser(API_KEY)
case_retriever = CaseLawRetriever(
    case_db_path=CASE_DB_PATH,
    embedding_path="../datasets/precomputed_embeddings.npz"
)
llm_highlighter = LLMHighlighter(
    openai_api_key=OPENAI_API_KEY,
    prompt_path=HIGHLIGHT_PROMPT_PATH,
    case_retriever=case_retriever
)

@app.route('/', methods=['GET'])
def index():
    return '''
    <html>
    <head><title>PDF Upload</title></head>
    <body>
        <h1>Upload PDF File for Parsing</h1>
        <form action=\"/upload\" method=\"post\" enctype=\"multipart/form-data\">
            <input type=\"file\" name=\"document\" accept=\"application/pdf\">
            <input type=\"submit\" value=\"Upload\">
        </form>
    </body>
    </html>
    '''

@app.route('/upload', methods=['POST'])
def highlight_pdf():
    try:
        print("Starting document analysis...")
        if 'document' not in request.files:
            return jsonify({"error": "문서가 필요합니다."}), 400
        
        file = request.files['document']
        if not file.filename:
            return jsonify({"error": "빈 파일이 전송되었습니다."}), 400
            
        parse_result = document_parser.parse(file)
        text = parse_result.get("content", {}).get("text", "")
        if not text:
            return jsonify({"error": "파싱된 텍스트가 없습니다."}), 400
        
        highlight_result = llm_highlighter.highlight(text)
        if not highlight_result:
            return jsonify({"error": "분석 결과가 없습니다."}), 400
            
        # OrderedDict 순서를 보존하기 위해 dumps를 직접 사용
        return app.response_class(
            response=json.dumps(highlight_result, cls=OrderedJsonEncoder, ensure_ascii=False),
            status=200,
            mimetype='application/json'
        )
        
    except Exception as e:
        app.logger.error(f"Error processing request: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)