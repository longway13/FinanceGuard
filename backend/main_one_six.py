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
                "금융소비자의 권익보호",
                "금융소비자의 요구가 정당한 것으로 판단될 경우"
            ]
        }




         
        # sample response data
        return jsonify(mock_response_data), 200
        
    except Exception as e:
        print(f"Error during file upload: {str(e)}")  # 에러 로깅
        return jsonify({"error": str(e)}), 500

@app.route('/api/chat', methods=['POST'])
def chat():
    """
    Chat 관련 더미 데이터 보내기 API 
    """
    # simulation
    mock_simulation = {
        "type": "simulation",
        "message" : "투자 상품에 대한 시물레이션 대화입니다.",
        "simulations": [
  {
    "id": 1,
    "situation": "3년 후에 투자 상품의 수익률이 기존 보장율보다 떨어짐.",
    "user": "최근 수익률을 확인해보니 보장율보다 낮던데, 이유가 뭔가요?",
    "consultant": "안녕하세요, 고객님. 시장 금리 하락 등의 영향으로 수익률이 일시적으로 보장율보다 낮게 나타날 수 있습니다. 자세한 내용을 확인해 드릴까요?"
  },
  {
    "id": 2,
    "situation": "수익률이 내가 원하는 만큼 나오지 않아서 해지하고 싶은 경우",
    "user": "기대했던 수익이 안 나와서 해지하고 싶은데, 어떻게 해야 하나요?",
    "consultant": "해지는 가능하지만, 상품에 따라 수수료나 손실이 발생할 수 있어요. 원하시면 해지 절차와 유의사항을 안내해 드릴게요."
  }
]
    }


#     # case
    mock_dispute_case = {
        "type": "cases",
        "message": "금융 분쟁 사례들입니다.",
        "disputes": [
  {
      "title": '수익률 미달로 인한 투자상품 해지 요청 분쟁',
      "summary": '고객이 가입한 투자상품의 수익률이 예상보다 낮아 해지를 요청했으나, 은행 측이 해지 수수료 및 손실 발생 가능성을 충분히 고지하지 않아 분쟁이 발생함.',
      "key points": 
        '- 고객은 안정적인 수익을 기대하고 상품에 가입함\n' +
        '- 상품 설명 시 최저 보장 수익률만 강조되고, 하락 가능성에 대한 설명 부족\n' +
        '- 해지 시 수수료 및 원금 손실 발생\n' +
        '- 금융사는 상품설명서 제공을 이유로 책임 없음 주장',
      "judge result": 
        "금융감독원은 고객에게 수익률 변동 가능성에 대한 설명이 충분하지 않았다고 판단하여, 손실액의 60% 배상을 권고함."
    },
  {
      "title": '고위험 파생상품 가입 시 설명 부족으로 인한 손실 분쟁',
      "summary": '고객이 고위험 파생상품에 가입한 후 큰 손실을 입었으며, 상품의 위험성과 구조에 대해 제대로 안내받지 못했다고 주장함.',
      "key points": 
        '- 고객은 은퇴자금으로 안전한 상품을 원했으나, 고위험 상품 권유받음\n' +
        '- 상품 구조가 복잡하고 손실 가능성이 큼\n' +
        '- 설명서 제공은 있었지만 이해를 위한 충분한 설명이 부족함\n' +
        '- 투자성향 분석 결과와 상품 위험도 불일치',
      "judge result": 
        "금융분쟁조정위원회는 설명의무 위반을 인정하고, 고객 손실의 70%를 금융회사가 배상하라는 조정을 내림."
    },
  {
      "title": '예금 상품 전환 시 동의 절차 누락 분쟁',
      "summary": '고객이 만기 도래 예금 상품이 자동으로 다른 상품으로 전환된 것에 대해 사전 동의가 없었다며 이의를 제기함.',
      "key points": 
        '- 기존 예금 만기 후 고지 없이 자동으로 수익률 낮은 상품으로 전환됨\n' +
        '- 고객은 만기 전 연락을 받지 못했다고 주장\n' +
        '- 은행은 약관에 자동전환 조항이 포함되어 있다고 설명\n' +
        '- 사전 고지 및 확인 절차의 적절성 논란',
      "judge result": 
        "금융감독원은 고객의 사전 동의 없는 자동 전환은 부당하다고 보고, 기존 상품 기준으로 재계약 처리하도록 권고함."
    }
]}
    
    # # simple dialogue
    # mock_simple_dialogue = {
    #     "type": "simple_dialogue",
    #     "message": "키위는 맛있습니다.",
    #     "status" : "success"
    # }

    # 독소조항들
    # mock_highlights  
    
    mock_highlights = {
        "type": "highlights",
        "rationale": "이 금융 상품은 다양한 수수료가 복잡하게 얽혀 있으며, 일부 조항은 소비자에게 불리한 조건을 포함하고 있습니다. 특히 중도 해지, 유지 수수료, 운용 수수료가 과도하게 책정되어 있어 주의가 필요합니다.",
        "highlights": [
        "집합투자증권",
        "예금성 상품과 구별되는 특징",
    ]
  }
    
    return jsonify(mock_simulation), 200



if __name__ == "__main__":
    app.run(debug=True)