from playwright.sync_api import sync_playwright
import json
import re
import os
from openai import OpenAI
from dotenv import load_dotenv
import time
import random

# .env 파일을 로드합니다.
load_dotenv()

# OpenAI API 키 설정
openai_api_key = os.getenv('OPENAI_API_KEY')

def save_storage(context, path='storage_state.json'):
    """
    주어진 브라우저 컨텍스트의 저장 상태를 JSON 파일로 저장합니다.

    Parameters:
    context: 현재 브라우저 컨텍스트
    path (str): 저장할 파일의 경로 (기본값은 'storage_state.json')
    """
    storage = context.storage_state()
    with open(path, 'w') as file:
        json.dump(storage, file)

def load_storage(browser, path='storage_state.json'):
    """
    저장된 상태 파일을 사용하여 새로운 브라우저 컨텍스트를 생성합니다.

    Parameters:
    browser: 브라우저 인스턴스
    path (str): 저장된 상태 파일의 경로 (기본값은 'storage_state.json')

    Returns:
    새로운 브라우저 컨텍스트
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

def parse_chinese_number(string):
    """
    주어진 문자열에서 중국어 숫자를 파싱하여 정수로 변환합니다.
    '千', '万', '亿' 단위를 처리합니다.

    Parameters:
    string (str): 중국어 숫자가 포함된 문자열

    Returns:
    int: 변환된 정수
    """
    # 중국어 숫자 단위에 대한 매핑
    units = {
        '千': 1000,
        '万': 10000,
        '亿': 100000000
    }
    
    match = re.search(r'(\d+)([千万亿]?)', string)
    
    if not match:
        return 0

    number = int(match.group(1))
    unit = match.group(2)
    
    if unit in units:
        number *= units[unit]

    return number

def ensure_https(url):
    """
    주어진 URL이 https://로 시작하지 않으면 https://로 시작하도록 변환합니다.

    Parameters:
    url (str): 변환할 URL

    Returns:
    str: 변환된 URL
    """
    if not url.startswith("https://"):
        if url.startswith("//"):
            return "https:" + url
        else:
            return "https://" + url
    return url

def sort_products_by_sales(simple_product_info) -> list:
    """
    판매량 기준으로 제품을 정렬합니다.

    Parameters:
    simple_product_info (dict): 제품 정보가 포함된 딕셔너리

    Returns:
    list: 판매량 순으로 정렬된 제품 리스트
    """
    candidate_products = []

    for product_info in simple_product_info['data']['itemsArray']:
        product = {
            "href": ensure_https(product_info['auctionURL']),
            "title": product_info['title'],
            "sales": parse_chinese_number(product_info['realSales']),
        }
        candidate_products.append(product)

    # JSON 파일에 저장 (테스트용)
    with open("candidate_products.json", "w", encoding="utf-8") as f:
        json.dump(candidate_products, f, ensure_ascii=False, indent=4)
    
    # sales 값 기준으로 정렬
    sorted_products = sorted(candidate_products, key=lambda x: x['sales'], reverse=True)
    
    return sorted_products

def translate_to_chinese(text):
    """
    주어진 한국어 텍스트를 중국어로 번역합니다.

    Parameters:
    text (str): 한국어 텍스트

    Returns:
    str: 중국어 번역된 텍스트
    """
    client = OpenAI(api_key=openai_api_key)
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a translator working for Immacus and your job is to translate product search keywords given in Korean into Chinese. Given the Korean keywords you need to translate, translate them into Chinese in the following JSON format. {“translated_text”: “Your translation into Chinese”}"},
            {"role": "user", "content": text}
        ]
    )
    
    # 응답에서 JSON 형식의 문자열 추출
    response_text = response.choices[0].message.content
    print(f'번역 결과 (JSON): {response_text}')
    
    # JSON 형식의 문자열을 파싱
    response_json = json.loads(response_text)
    translated_text = response_json["translated_text"]
    print(f'번역 결과: {translated_text}')
    
    return translated_text

def parse_jsonp(jsonp_str):
    """
    JSONP 문자열을 JSON 객체로 변환합니다.

    Parameters:
    jsonp_str (str): JSONP 문자열

    Returns:
    dict: JSON 객체
    """
    jsonp_str = jsonp_str.strip()
    pattern = r'^mtopjsonp\d+\('
    match = re.match(pattern, jsonp_str)
    if match:
        jsonp_str = jsonp_str[match.end():-1]
        try:
            return json.loads(jsonp_str)
        except json.JSONDecodeError as e:
            print(f"JSON decoding failed: {e}")
    return None

def get_top_selling_product_links(keywords) -> dict:
    """
    주어진 키워드로 검색된 상품들 중 많이 팔린 상품의 링크를 반환합니다.

    Parameters:
    keywords (List[str]): 검색할 키워드의 List

    Returns:
    dict: 각 키워드에 대한 상위 판매 상품 링크
    """
    results = {}
    
    # 키워드를 중국어로 번역
    translated_keywords = [translate_to_chinese(keyword) for keyword in keywords]
    
    # 네트워크 응답을 저장할 변수
    global simple_product_info
    
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=False)
        context = load_storage(browser)
        page = context.new_page()
        page.set_viewport_size({'width': 1920, 'height': 1080})
        
        page.goto('https://www.taobao.com/')

        # TODO: 로그인 처리
        # 현재 로그인은 처리되었다고 가정하고 진행합니다.
        
        print('로그인 처리가 완료되었습니다.')
        
        search_input_selector = 'input[class*="rax-textinput"][class*="searchbar-input"]'
        search_button_selector = '#search-box'
        
        page.wait_for_selector(search_input_selector, timeout=5000)
        print('검색창이 로드되었습니다.')
        page.wait_for_selector(search_button_selector, timeout=5000)
        print('검색 버튼이 로드되었습니다.')
        
        def handle_response(response):
            """
            네트워크 응답을 처리하여 제품 정보를 추출합니다.

            Parameters:
            response: Playwright 응답 객체
            """
            global simple_product_info
            if response.status == 200 and 'h5api.m.taobao.com/h5/mtop.relationrecommend.wirelessrecommend.recommend' in response.url:
                simple_product_info = parse_jsonp(response.text())
        
        # 네트워크 응답 이벤트를 처리하는 핸들러 등록
        page.on('response', handle_response)
        
        try:
            page.fill(search_input_selector, translated_keywords[0])
            print('1번째 키워드를 입력했습니다.')
            page.click(search_button_selector)
            print('검색 버튼을 클릭했습니다.')
        except Exception as e:
            print(f'1번째 키워드를 입력하는 도중 오류가 발생했습니다: {e}')
        
        # 첫 번째 키워드 검색 결과 페이지 로드 대기
        with page.expect_response(
            lambda response: "h5api.m.taobao.com/h5/mtop.relationrecommend.wirelessrecommend.recommend" in response.url
        ) as response_info:
            response_info.value
        
        time.sleep(3 + random.random() * 3)
        
        # 48개의 제품을 판매량 순으로 정렬
        results[keywords[0]] = sort_products_by_sales(simple_product_info)
            
        # 남은 키워드로 검색
        search_input_selector = 'input#q'
        search_button_selector = 'button#button'
        
        for keyword, translated_keyword in zip(keywords[1:], translated_keywords[1:]):
            try:
                # 검색창 로드 대기
                page.wait_for_selector(search_input_selector, timeout=5000)
                print('검색창이 로드되었습니다.')
                
                # 검색 버튼 로드 대기
                page.wait_for_selector(search_button_selector, timeout=5000)
                print('검색 버튼이 로드되었습니다.')
                
                # input 태그에 값 입력
                page.fill(search_input_selector, translated_keyword)
                print(f'키워드를 입력했습니다: {keyword}, 번역된 키워드: {translated_keyword}')
                
                # 버튼 클릭
                page.click(search_button_selector)
                print('검색 버튼을 클릭했습니다.')
                
                # 검색 결과 페이지 로드 대기
                with page.expect_response(
                    lambda response: "h5api.m.taobao.com/h5/mtop.relationrecommend.wirelessrecommend.recommend" in response.url
                ) as response_info:
                    response_info.value
                
                time.sleep(3 + random.random() * 3)
                
                # 상위 판매 상품 링크 선택
                top_products = sort_products_by_sales(simple_product_info)
                results[keyword] = top_products
                
            except Exception as e:
                print(f'키워드 "{keyword}"를 입력하는 도중 오류가 발생했습니다: {e}')
        
        # 쿠키 및 로컬 스토리지 저장
        save_storage(context, 'storage_state.json')

        # 브라우저 종료
        browser.close()

    return results

def filter_high_rating_products(product_dict, min_rating=4.7):
    """
    높은 평점을 가진 제품을 필터링합니다.

    Parameters:
    product_dict (dict): 각 카테고리의 제품 목록을 포함한 딕셔너리
    min_rating (float): 최소 평점 기준 (기본값은 4.7)

    Returns:
    dict: 높은 평점을 가진 제품만 포함한 딕셔너리
    """
    high_rating_products = {category: [] for category in product_dict}
    
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=False)
        context = load_storage(browser)
        page = context.new_page()
        page.set_viewport_size({'width': 1920, 'height': 1080})
        
        for category, products in product_dict.items():
            for product in products:
                page.goto(product['href'])
                
                # 셀러의 평점을 가져옵니다.
                rating_selectors = [
                    ".ShopHeaderNew--starNum--2ws_MMR",
                    ".OverallScore--starNum--2WdQduP",
                    ".OverallScore--evaluateItemCore--X5zZj5q font"
                ]
                
                rating = None
                for selector in rating_selectors:
                    try:
                        page.wait_for_selector(selector, timeout=3000)
                        rating_element = page.query_selector(selector)
                        if rating_element:
                            rating_text = rating_element.inner_text()
                            try:
                                rating = float(rating_text)
                                break
                            except ValueError:
                                continue
                    except:
                        continue
                
                if rating and rating >= min_rating:
                    high_rating_products[category].append(product)
                
        # 쿠키 및 로컬 스토리지 저장
        save_storage(context, 'storage_state.json')

        # 브라우저 종료
        browser.close()
        
        # 각 카테고리별로 제품을 10개 이하로 제한합니다.
        for category in high_rating_products:
            high_rating_products[category] = high_rating_products[category][:10]
    
    return high_rating_products

# 이하 코드는 테스트 코드입니다.
# keywords = [
#     "미용실의자",
#     "트롤리 책장",
#     "일체형 스키복",
#     "미니 원피스",
#     "미용사 앞치마",
#     "우드 건조대",
#     "비파괴스캐너",
#     "명상 의자",
#     "캠핑용 실링팬",
#     "고양이집"
# ]

# results = get_top_selling_product_links(keywords)
# filtered_results = filter_high_rating_products(results)

# results 딕셔너리를 JSON 파일에 저장 (테스트용)
# with open("results.json", "w", encoding="utf-8") as f:
#     json.dump(results, f, ensure_ascii=False, indent=4)
    
# with open("filtered_results.json", "w", encoding="utf-8") as f:
#     json.dump(filtered_results, f, ensure_ascii=False, indent=4)
