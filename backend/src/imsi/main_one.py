import requests
from flask import Flask, request, jsonify, Response
from langchain.schema import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from src.imsi.basic import *
import json
import os
from werkzeug.utils import secure_filename


# LLM을 통해 요약을 생성하는 클래스
class LLMSummarizer:
    def __init__(self):
        # LLM 관련 설정 추가 가능 (예: API 키 등)
        get_openai_api_key("backend/conf.d/config.yaml")
        self.llm = ChatOpenAI(model_name='gpt-4o-mini',  # 'gpt-3.5-turbo' or 'gpt-4o-mini'
                      temperature=0,max_tokens=1500, max_retries=100)

    
    def generate_summary(self, text: str) -> str:
        """
        text: 파싱된 전체 텍스트
        반환: 생성된 요약 문자열
        
        """
        prompt_path = "backend/prompts/summarize_pdf.yaml"
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
