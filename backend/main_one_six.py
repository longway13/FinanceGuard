import requests
from flask import Flask, request, jsonify, Response
from langchain.schema import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from basic import *
import json
import os
from werkzeug.utils import secure_filename

# PDF 파일을 외부 파싱 API를 통해 처리하는 클래스
class DocumentParser:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.url = "https://api.upstage.ai/v1/document-digitization"
    
    def parse(self, file_obj) -> dict:
        """
        file_obj: 파일 객체 (예: Flask의 request.files['document'])
        반환: API 응답 JSON을 dict로 반환
        """
        headers = {"Authorization": f"Bearer {self.api_key}"}
        # API에서는 파일 객체를 그대로 받을 수 있음.
        files = {"document": file_obj}
        # 필요에 따라 추가 옵션 지정 (예: OCR 강제 적용, base64 인코딩 옵션, 모델 선택 등)
        data = {"ocr": "force", "base64_encoding": "[]", "model": "document-parse", "output_formats" : "['text']"}
        
        response = requests.post(self.url, headers=headers, files=files, data=data)
        
        return response.text

# LLM을 통해 요약을 생성하는 클래스
class LLMSummarizer:
    def __init__(self):
        # LLM 관련 설정 추가 가능 (예: API 키 등)
        get_api_key("conf.d/config.yaml")
        self.llm = ChatOpenAI(model_name='gpt-4o-mini',  # 'gpt-3.5-turbo' or 'gpt-4o-mini'
                      temperature=0,max_tokens=1500, max_retries=100)

    
    def generate_summary(self, text: str) -> str:
        """
        text: 파싱된 전체 텍스트
        반환: 생성된 요약 문자열
        
        """
        prompt_path = "prompt/summarize_pdf.yaml"
        prompt = load_message(prompt_path)
        prefix = load_prefix(prompt_path)
        prompt = '\n\n'.join([prompt, prefix])
        prompt = prompt.format(**{
            "content": text
        })
        human_message = HumanMessage(content=prompt)
        required_keys = [
            "Overall Summary", "Purpose", "Cost", "Revenue", "Contract Duration",
            "Contractor's Responsibilities", "Key Findings"
        ]

        while True:
            try:
                print("sumarizing...")
                response = self.llm.generate([[human_message]])
                response = response.generations[0][0].text
                print(response)

                # 멀티라인 대응 파서
                parsed = {}
                current_key = None
                current_value_lines = []

                for line in response.strip().split("\n"):
                    if ":" in line:
                        # 이전 key가 있다면 저장
                        if current_key:
                            parsed[current_key] = "\n".join(current_value_lines).strip()
                        # 새 key-value 시작
                        key, value = line.split(":", 1)
                        current_key = key.strip()
                        current_value_lines = [value.strip()]
                    else:
                        # 기존 value에 이어붙임
                        if current_key:
                            current_value_lines.append(line.strip())

                # 마지막 키 처리
                if current_key:
                    parsed[current_key] = "\n".join(current_value_lines).strip()

                for key in required_keys:
                    if key not in parsed:
                        raise ValueError(f"누락된 항목: {key}")
                break

            except Exception as e:
                print(e)
                print("Retrying...")
                parsed = "요약에 문제가 있습니다."

        return parsed


# DocumentParser와 LLMSummarizer를 조합해 PDF를 처리하는 클래스
class PDFProcessor:
    def __init__(self, parser: DocumentParser, summarizer: LLMSummarizer):
        self.parser = parser
        self.summarizer = summarizer
    
    def process_pdf(self, file_obj) -> str:
        """
        file_obj: 업로드된 PDF 파일 객체
        반환: LLM으로 생성한 summary
        """
        parse_result = self.parser.parse(file_obj)

        # API의 반환 구조에 따라 파싱된 텍스트를 추출합니다.
        # 여기서는 "parsed_text" 또는 "text" 키로 가정합니다.
        
        parse_result = json.loads(parse_result)
        parse_result = parse_result["content"]["text"]
        # print(parse_result)

        # text = parse_result.get("parsed_text") or parse_result.get("text") or ""

        if not parse_result:
            parse_result = "파싱된 텍스트가 없습니다."
        summary = self.summarizer.generate_summary(parse_result)
        return summary

# Flask 웹 서버 생성
app = Flask(__name__)

# 실제 API 키로 변경하세요.
API_KEY = "up_CcTX5JkVdEfu3Slmphq4HkAwdNhrh"
document_parser = DocumentParser(API_KEY)
llm_summarizer = LLMSummarizer()
pdf_processor = PDFProcessor(document_parser, llm_summarizer)

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
def upload_pdf():
    """
    프론트엔드에서 PDF 파일(FormData의 'document' 필드)이 전송되면 처리합니다.
    """
    if 'document' not in request.files:
        return jsonify({"error": "파일이 전송되지 않았습니다."}), 400
    
    file = request.files['document']
    
    # Save uploaded file to disk
    upload_dir = "uploads"
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)
    filename = secure_filename(file.filename)
    file_path = os.path.join(upload_dir, filename)
    file.save(file_path)

    # Save file path to a JSON file
    json_file_path = "uploaded_files.json"
    if os.path.exists(json_file_path):
        with open(json_file_path, "r", encoding="utf-8") as f:
            file_list = json.load(f)
    else:
        file_list = []
    file_list.append(file_path)
    with open(json_file_path, "w", encoding="utf-8") as f:
        json.dump(file_list, f, ensure_ascii=False, indent=2)

    # Reset file pointer before further processing
    file.seek(0)
    
    try:
        summary = pdf_processor.process_pdf(file)
        
        response_data = json.dumps({"summary": summary}, ensure_ascii=False)
        return Response(response_data, content_type="application/json; charset=utf-8")
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)