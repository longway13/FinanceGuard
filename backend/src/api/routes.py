"""Flask routes for the legal assistant API"""

import os
import json
import uuid
import logging
from flask import Flask, request, jsonify, Response, session
from werkzeug.utils import secure_filename
import boto3
from botocore.config import Config
import requests
from datetime import datetime
import io

# Local imports
from ..agent.core import process_query
from ..tools.tool_registry import get_registered_tools
from ..imsi.main_one import *
from ..imsi.main_two import *
from ..imsi.basic import *
from ..imsi.model import db, PDFFile

# Configure logging
logger = logging.getLogger(__name__)

# Create Flask app and configure it
app = Flask(__name__)
app.secret_key = os.urandom(24)  # For session management
pdf_counter = 0

# Register tools
tools = get_registered_tools()

# S3 설정
BUCKET_NAME = os.environ.get('BUCKET_NAME', 'wetube-gwanwoo')
s3 = boto3.client('s3',
    aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
    region_name='ap-northeast-2',
    config=Config(signature_version='s3v4')
)

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
        response = process_query(query, tools, pdf_path)
        
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

# 아래는 테스트 위한 HTML 페이지 / 라우터
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
            .response-area { border: 1px solid #ddd; padding: 20px; min-height: 300px; max-height: 500px; overflow-y: auto; font-family: monospace; font-size: 14px; white-space: pre-wrap; border-radius: 4px; }
            .file-info { margin-top: 15px; padding: 10px; background-color: #f8f9fa; border-radius: 4px; }
            .file-status { color: #27ae60; font-weight: bold; }
            .dropzone { border: 2px dashed #ccc; border-radius: 5px; padding: 25px; text-align: center; margin: 15px 0; }
            .dropzone:hover { border-color: #3498db; background-color: #f8f9fa; }
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
                <h3>응답 (JSON 원본):</h3>
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
                
                fetch('/api/pdf/upload', {
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
                    
                    // Get the raw response text to avoid automatic parsing
                    const rawText = await response.text();
                    
                    try {
                        // Try to parse and pretty-print the JSON
                        const data = JSON.parse(rawText);
                        responseArea.textContent = JSON.stringify(data, null, 2);
                    } catch (parseError) {
                        // If parsing fails, just show the raw text
                        responseArea.textContent = rawText;
                    }
                    
                    console.log("Displayed raw API response");
                } catch (error) {
                    console.error("API error:", error);
                    responseArea.textContent = `Error: ${error.message}`;
                }
            });
        </script>
    </body>
    </html>
    '''

@app.route('/api/pdf/upload', methods=['POST'])
def upload_pdf():
    """
    프론트엔드에서 PDF 파일 업로드를 위한 엔드포인트
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
        
        API_KEY = get_upstage_api_key("backend/conf.d/config.yaml")
        document_parser = DocumentParser(API_KEY)
        llm_summarizer = LLMSummarizer()
        pdf_processor = PDFProcessor(document_parser, llm_summarizer)

        #여기서 summary 추출
        response = s3.get_object(Bucket=BUCKET_NAME, Key="pdf/0") #key에 따라 다양한 파일 받아올 수 있음
        file = response['Body'] 
        file_obj = io.BytesIO(file.read())
        file_obj.seek(0) 

        parse_result, summary = pdf_processor.process_pdf(file_obj)


        PROMPT_PATH = "backend/prompts/highlight_prompt.txt"
        CASE_DB_PATH = "backend/datasets/case_db.json"

        document_parser = DocumentParser(API_KEY)

        case_retriever = CaseLawRetriever(
            case_db_path=CASE_DB_PATH,
            embedding_path="backend/datasets/precomputed_embeddings.npz"
        )

        llm_highlighter = LLMHighlighter(
            app = app,
            prompt_path=PROMPT_PATH,
            case_retriever=case_retriever
        )
        print("Starting document analysis...")

        text = parse_result
        if not text:
            return jsonify({"error": "파싱된 텍스트가 없습니다."}), 400
        
        highlight_result = llm_highlighter.highlight(text)

        if not highlight_result:
            return jsonify({"error": "분석 결과가 없습니다."}), 400
        
        high_json = json.dumps(highlight_result, ensure_ascii=False, indent=2)
        # 변환
        converted = []
        for item in high_json:
            converted.append({
                "toxic_clause": item["독소조항"],
                "reason": item["이유"],
                "related_case_formatted": item["유사판례_정리"],
                "related_case_raw": item["유사판례_원문"],
                "similarity": item["유사도"]
            })
        print("finished")
        response_data = {
            "status": "success",
            "message": "Successfully uploaded file",
            "filename": filename,
            "file_url": file_path,
            "pdf_id": f"PDF_{pdf_counter}",
            "summary": summary,
            "highlight": converted  # 원본 객체를 그대로 사용
        }

        response_json = json.dumps(response_data, cls=OrderedJsonEncoder, ensure_ascii=False)

        return jsonify({"success": True, "response" : response_json}), 200

    except Exception as e:
        print(f"Error during file upload: {str(e)}")  # 에러 로깅
        return jsonify({"error": str(e)}), 500

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
