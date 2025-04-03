import requests
from flask import Flask, request, jsonify, Response
from flask_cors import CORS  # CORS 추가
from langchain.schema import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from basic import *
import json
import os
from werkzeug.utils import secure_filename
import boto3
from botocore.config import Config
from datetime import datetime

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
CORS(app)
# 실제 API 키로 변경하세요.
API_KEY = "up_CcTX5JkVdEfu3Slmphq4HkAwdNhrh"
document_parser = DocumentParser(API_KEY)
llm_summarizer = LLMSummarizer()
pdf_processor = PDFProcessor(document_parser, llm_summarizer)
pdf_counter = 0

# S3 설정
BUCKET_NAME = os.environ.get('BUCKET_NAME', 'wetube-gwanwoo')
s3 = boto3.client('s3',
    aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
    region_name='ap-northeast-2',
    config=Config(signature_version='s3v4')
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

@app.route('/api/pdf-upload', methods=['POST'])
def upload_pdf():
    """
    프론트엔드에서 PDF 파일 업로드 테스트를 위한 엔드포인트
    """
    global pdf_counter  # 전역 변수 사용
    print("Upload endpoint called")  # 요청이 들어왔는지 확인
    print(request.files)
    if 'file' not in request.files:
        print("No document in request.files")  # 파일이 없는 경우 로깅
        return jsonify({"error": "파일이 전송되지 않았습니다."}), 400
    
    file = request.files['file']
    print(f"Received file: {file.filename}")  # 파일 이름 로깅
    
    if file.filename == '':
        print("No selected file")  # 파일이 선택되지 않은 경우 로깅
        return jsonify({"error": "선택된 파일이 없습니다."}), 400
    
    if not file.filename.lower().endswith('.pdf'):
        print(f"Invalid file type: {file.filename}")  # 잘못된 파일 타입 로깅
        return jsonify({"error": "PDF 파일만 업로드 가능합니다."}), 400
    
    try:
        # 파일 저장
        filename = secure_filename(file.filename)

        # Save file to S3
        s3_path = f"pdf/{pdf_counter}"
        s3.upload_fileobj(
            file,
            BUCKET_NAME,
            s3_path,
            ExtraArgs={
                'ContentType': 'application/pdf',
                'ACL': 'public-read'
            }
        )
        # Sample file url
        file_path = f"https://wetube-gwanwoo.s3.ap-northeast-2.amazonaws.com/pdf/{pdf_counter}"
        pdf_counter += 1  # 카운터 증가
        
        response_data = {
            "status": "success",
            "message": "Successfully uploaded file",
            "filename": filename,
            "file_url": file_path,
            "pdf_id": f"PDF_{pdf_counter}"
        }

        # Mock response data for frontend testing
        mock_response_data = {
            "status": "success",
            "message": "Successfully uploaded file",
            "filename": filename,
            "file_url": file_path,
            "pdf_id": pdf_counter,
            "summary": "이 금융 상품은 안정적인 수익을 추구하는 중위험 투자 상품입니다. 장기 자산 증식을 목적으로 하는 펀드 상품으로, 분기별 자산 재배분을 통해 위험을 관리하며 시장 상황에 따라 탄력적으로 포트폴리오를 조정합니다. 안정적인 배당 수익을 추구하면서도 연 5-7%의 기대 수익률을 목표로 하고 있습니다. 최소 투자금액은 100만원이며, 장기 투자자들에게 적합한 상품입니다.",
            "key_values": {
                "annualReturn": "연 5-7%",
                "volatility": "보통위험",
                "managementFee": "1.5%",
                "minimumInvestment": "100만원",
                "lockupPeriod": "12개월",
                "riskLevel": "보통위험"
            },
            "key_findings": [
                "분기별 자산 재배분을 통한 위험 관리",
                "시장 상황에 따른 탄력적인 포트폴리오 조정",
                "안정적인 배당 수익 추구"
            ],
            "highlights": [
                {
                    "id": "highlight_1",
                    "content": {
                        "text": "연평균 수익률"
                    },
                    "position": {
                        "pageNumber": 1,
                        "boundingRect": {
                            "x1": 100,
                            "y1": 100,
                            "x2": 300,
                            "y2": 120
                        }
                    },
                    "comment": "중요 위험 고지 사항"
                },
                {
                    "id": "highlight_2",
                    "content": {
                        "text": "투자자 유의사항"
                    },
                    "position": {
                        "pageNumber": 2,
                        "boundingRect": {
                            "x1": 150,
                            "y1": 200,
                            "x2": 350,
                            "y2": 220
                        }
                    },
                    "comment": "투자에 신중"
                }
            ]
        }
        
        # sample response data
        return jsonify(mock_response_data), 200
        
    except Exception as e:
        print(f"Error during file upload: {str(e)}")  # 에러 로깅
        return jsonify({"error": str(e)}), 500



if __name__ == "__main__":
    app.run(debug=True)