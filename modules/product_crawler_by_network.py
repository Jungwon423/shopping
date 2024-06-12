from dotenv import load_dotenv
import os
import json
from playwright.sync_api import sync_playwright
import time
from urllib.parse import urlparse, parse_qs
import random

# .env 파일을 로드합니다.
load_dotenv()

# OpenAI API 키 설정
openai_api_key = os.getenv('OPENAI_API_KEY')

def save_storage(context, path='storage_state.json'):
    """
    주어진 브라우저 컨텍스트의 저장 상태를 JSON 파일로 저장합니다.

    Parameters:
    context (BrowserContext): 현재 브라우저 컨텍스트
    path (str): 저장할 파일의 경로 (기본값은 'storage_state.json')
    """
    storage = context.storage_state()
    with open(path, 'w') as file:
        json.dump(storage, file)

def load_storage(browser, path='storage_state.json'):
    """
    저장된 상태 파일을 사용하여 새로운 브라우저 컨텍스트를 생성합니다.

    Parameters:
    browser (Browser): 브라우저 인스턴스
    path (str): 저장된 상태 파일의 경로 (기본값은 'storage_state.json')

    Returns:
    BrowserContext: 새로운 브라우저 컨텍스트
    """
    # 파일이 존재하지 않으면 빈 저장 상태로 파일 생성
    if not os.path.exists(path):
        empty_storage = {
            "cookies": [],
            "origins": []
        }
        with open(path, 'w', encoding='utf-8') as file:
            json.dump(empty_storage, file, ensure_ascii=False, indent=4)
            
    # 저장된 상태를 사용하여 새로운 컨텍스트 생성
    context = browser.new_context(storage_state=path)
    return context

def save_to_json(data, filename):
    """
    데이터를 JSON 파일로 저장합니다.

    Parameters:
    data (dict or list): JSON으로 저장할 데이터
    filename (str): 저장할 파일의 경로
    """
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
        
################################################################

def get_product_info(product_link):
    """
    주어진 제품 링크에서 제품 정보를 추출합니다.

    Parameters:
    product_link (str): 제품 페이지의 URL

    Returns:
    str: 추출된 제품 정보
    """
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=False)
        context = load_storage(browser)
        page = context.new_page()
        page.set_viewport_size({'width': 1920, 'height': 1080})

        response_data = []
        
        def handle_response(response):
            if response.status == 200 and 'mtop.taobao.pcdetail.data.get' in response.url:
                print(response.url)
                print('@@@@@@@@')
                response_data.append(response.json())

        # 네트워크 응답 이벤트를 캡처합니다.
        page.on('response', handle_response)

        # 제품 링크 열기
        page.goto(product_link)
        
        # 특정 네트워크 응답을 기다림      
        with page.expect_response(
            lambda response: "mtop.taobao.pcdetail.data.get" in response.url
        ) as response_info:
            response = response_info.value
        
        time.sleep(3 + random.random()*3)
        
        save_to_json(response_data, 'network_responses.json')
        
        # 쿠키 및 로컬 스토리지 저장
        save_storage(context, 'storage_state.json')
        browser.close()

get_product_info("https://item.taobao.com/item.htm?priceTId=2100c80717182171949451856e0c31&id=576815286685&ns=1&abbucket=6#detail")