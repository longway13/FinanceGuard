"""Flask routes for the legal assistant API"""

import os
import json
import uuid
import logging
from flask import Flask, request, jsonify, Response, session
from werkzeug.utils import secure_filename

# Local imports
from ..agent.core import process_query
from ..tools.tool_registry import get_registered_tools
from src.config import UPLOADS_DIR

# Configure logging
logger = logging.getLogger(__name__)

# Create Flask app and configure it
app = Flask(__name__)
app.secret_key = os.urandom(24)  # For session management

# Create upload directory
if not os.path.exists(UPLOADS_DIR):
    os.makedirs(UPLOADS_DIR)
app.config['UPLOAD_FOLDER'] = UPLOADS_DIR

# Register tools
tools = get_registered_tools()

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


