import requests
from flask import Flask, request, jsonify, Response
from flask_cors import CORS  # CORS 추가
from basic import *
from main_one import *
from main_two import *
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
import boto3
from botocore.config import Config
from datetime import datetime
from model import db, PDFFile

# Flask 웹 서버 생성
app = Flask(__name__)
app.json_encoder = OrderedJsonEncoder
pdf_counter = 0
# S3 설정
BUCKET_NAME = os.environ.get('BUCKET_NAME', 'wetube-gwanwoo')
s3 = boto3.client('s3',
    aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
    region_name='ap-northeast-2',
    config=Config(signature_version='s3v4')
)


@app.route('/api/pdf/upload', methods=['POST'])
def upload_pdf():
    """
    프론트엔드에서 PDF 파일 업로드 테스트를 위한 엔드포인트
    """
    global pdf_counter  # 전역 변수 사용
    print("Upload endpoint called")  # 요청이 들어왔는지 확인
    # print(request.files)
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
        
        API_KEY = get_upstage_api_key("conf.d/config.yaml")
        document_parser = DocumentParser(API_KEY)
        llm_summarizer = LLMSummarizer()
        pdf_processor = PDFProcessor(document_parser, llm_summarizer)
        file.seek(0)

        #여기서 summary 추출
        summary = pdf_processor.process_pdf(file)

        #여기서 highlight 추출
        API_KEY = get_upstage_api_key("conf.d/config.yaml")
        PROMPT_PATH = "prompt/highlight_prompt.txt"
        CASE_DB_PATH = "datasets/case_db.json"

        document_parser = DocumentParser(API_KEY)
        case_retriever = CaseLawRetriever(
            case_db_path=CASE_DB_PATH,
            embedding_path="datasets/precomputed_embeddings.npz"
        )
        llm_highlighter = ToxicClauseFinder(
            app = app,
            prompt_path=PROMPT_PATH,
            case_retriever=case_retriever
        )
        print("Starting document analysis...")
        if 'document' not in request.files:
            return jsonify({"error": "문서가 필요합니다."}), 400
        
        file = request.files['document']
        if not file.filename:
            return jsonify({"error": "빈 파일이 전송되었습니다."}), 400
            
        parse_result = document_parser.parse(file)
        text = json.loads(parse_result)
        text = text["content"]["text"]
        if not text:
            return jsonify({"error": "파싱된 텍스트가 없습니다."}), 400
        
        highlight_result = llm_highlighter.find(text)
        if not highlight_result:
            return jsonify({"error": "분석 결과가 없습니다."}), 400

        response_data = {
            "status": "success",
            "message": "Successfully uploaded file",
            "filename": filename,
            "file_url": file_path,
            "pdf_id": f"PDF_{pdf_counter}",
            "summary": summary,
            "highlight": highlight_result  # 원본 객체를 그대로 사용
        }

        response_json = json.dumps(response_data, cls=OrderedJsonEncoder, ensure_ascii=False)
        return app.response_class(
            response=response_json,
            status=200,
            mimetype='application/json'
        )

    except Exception as e:
        print(f"Error during file upload: {str(e)}")  # 에러 로깅
        return jsonify({"error": str(e)}), 500



@app.route('/api/user-query', methods=['POST'])
def process_query():
    pass


if __name__ == "__main__":
    get_openai_api_key()
    app.run(debug=True)