import requests
from flask import Flask, request, jsonify, Response
from basic import *
from main_one import *
from main_two import *
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from model import db, PDFFile

# Flask 웹 서버 생성
app = Flask(__name__)
app.json_encoder = OrderedJsonEncoder
# 환경설정: 데이터베이스와 업로드 폴더 지정
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///mydatabase.db'
app.config['UPLOAD_FOLDER'] = 'uploads'
db.init_app(app)

with app.app_context():
    db.create_all()
    
@app.route('/store_pdf', methods=['POST'])
def store_pdf():
    pdf_file = request.files.get('document')
    if not pdf_file:
        return jsonify({"status": "No PDF found"}), 400

    try:
        filename = secure_filename(pdf_file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        pdf_file.save(file_path)

        new_pdf = PDFFile(filename=filename, file_url=file_path)
        db.session.add(new_pdf)
        db.session.commit()

        response_data = json.dumps({
            "PDF_url": new_pdf.file_url,
            "id": new_pdf.id
        }, ensure_ascii=False)
        return Response(response_data, content_type="application/json; charset=utf-8")
    
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
    
@app.route('/get_pdf/<int:pdf_id>', methods=['GET'])
def get_pdf(pdf_id):
    pdf = PDFFile.query.get(pdf_id)
    if not pdf:
        return jsonify({"status": "PDF not found"}), 404

    response_data = {
         "id": pdf.id,
         "filename": pdf.filename,
         "file_url": pdf.file_url,
         "created_at": pdf.created_at.isoformat()
    }
    return jsonify(response_data)


@app.route('/summary_intro', methods=['POST'])
def summary_intro():
    """
    PDF를 받아서 Summary 기능을 수행하는 dummy 함수.
    """
    # Dummy implementation: Extract system prompt and PDF from request

    pdf_file = request.files['document']
    API_KEY = get_upstage_api_key()
    document_parser = DocumentParser(API_KEY)
    llm_summarizer = LLMSummarizer()
    pdf_processor = PDFProcessor(document_parser, llm_summarizer)
    pdf_file.seek(0)

    try:
        summary = pdf_processor.process_pdf(pdf_file)
        response_data = json.dumps({"summary": summary}, ensure_ascii=False)
        return Response(response_data, content_type="application/json; charset=utf-8")

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/highlight_sentences', methods=['POST'])
def highlight():
    """
    Prompt와 PDF를 받아서 PDF 내 하이라이트한 독소 조항 및 뭐 추출하는 dummy 함수.
    """
    API_KEY = get_upstage_api_key()
    PROMPT_PATH = "prompt/highlight_prompt.txt"
    CASE_DB_PATH = "datasets/case_db.json"
    try:
        document_parser = DocumentParser(API_KEY)
        case_retriever = CaseLawRetriever(
            case_db_path=CASE_DB_PATH,
            embedding_path="datasets/precomputed_embeddings.npz"
        )
        llm_highlighter = LLMHighlighter(
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


if __name__ == "__main__":
    get_openai_api_key()
    app.run(debug=True)