from dotenv import load_dotenv
import os
import json
from playwright.sync_api import sync_playwright
import time
from urllib.parse import urlparse, parse_qs
import random
import re

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

def load_from_json(filename='network_responses.json'):
    with open(filename, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data

def parse_jsonp(jsonp_str):
    # 'mtopjsonp' 뒤의 숫자와 '('를 제거하고 마지막 ')'를 제거
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

def extract_image_links_from_html(html):
    image_links = []
    start = 0

    while True:
        # <img 태그 찾기
        img_tag_start = html.find('<img', start)
        if img_tag_start == -1:
            break

        # src 속성 찾기
        src_start = html.find('src="', img_tag_start)
        if src_start == -1:
            break
        src_start += len('src="')

        # src 속성 값의 끝 찾기
        src_end = html.find('"', src_start)
        if src_end == -1:
            break

        # src 값 추출
        image_url = html[src_start:src_end]
        image_links.append(image_url)

        # 다음 img 태그를 찾기 위해 시작 위치 업데이트
        start = src_end

    return image_links

def parse_sku_data_to_options(json_data):
    
    data = json_data
    result = {
        "optionCombinationGroupNames": {},
        "optionCombinations": []
    }
    
    props = data['skuBase']['props']
    skus_info = data['skuCore']['sku2info']
    skus_properties = data['skuBase']['skus']
    
    # Mapping option group names
    for index, prop in enumerate(props):
        result['optionCombinationGroupNames'][f'optionGroupName{index + 1}'] = prop['name']
    
    # Extracting sku details and options
    for sku_property in skus_properties:
        sku_id = sku_property['skuId']
        
        # Check if sku_id exists in skus_info
        if sku_id not in skus_info:
            continue
        
        sku_info = skus_info[sku_id]
        price = int(sku_info['price']['priceMoney'])
        stock_quantity = int(sku_info['quantity'])
        
        # Splitting propPath and extracting option values
        prop_path = sku_property['propPath'].split(';')
        options = {}
        for prop in prop_path:
            prop_id, val_id = prop.split(':')
            for prop_item in props:
                if prop_item['pid'] == prop_id:
                    for val in prop_item['values']:
                        if val['vid'] == val_id:
                            options[prop_item['name']] = val['name']
        
        # Creating option combination dictionary
        option_combination = {
            "id": sku_id,
            "optionName1": options.get(props[0]['name'], "") if len(props) > 0 else "",
            "optionName2": options.get(props[1]['name'], "") if len(props) > 1 else "",
            "optionName3": options.get(props[2]['name'], "") if len(props) > 2 else "",
            "optionName4": options.get(props[3]['name'], "") if len(props) > 3 else "",
            "stockQuantity": stock_quantity,
            "price": price,
            "sellerManagerCode": "",
            "usable": True
        }
        result['optionCombinations'].append(option_combination)
    
    return result

def get_product_id(product_link):
    """
    주어진 제품 링크에서 제품 ID를 추출합니다.

    Parameters:
    product_link (str): 제품 페이지의 URL

    Returns:
    str: 추출된 제품 ID
    """
    # URL을 파싱합니다.
    parsed_url = urlparse(product_link)
    
    # 쿼리 문자열을 파싱하여 딕셔너리로 변환합니다.
    query_params = parse_qs(parsed_url.query)
    
    # 'id' 매개변수에서 제품 ID를 추출합니다.
    product_id = query_params.get('id', [None])[0]
    
    print(f"Product ID: {product_id}")
    
    return product_id

################################################################

def get_product_info(product_links):
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

        global response_product_info
        global response_product_description
        
        def handle_response(response):
            global response_product_info
            global response_product_description
            if response.status == 200 and 'mtop.taobao.pcdetail.data.get' in response.url:
                response_product_info = response.json()
            elif response.status == 200 and 'mtop.taobao.detail.getdesc' in response.url:
                jsonp_str = response.text()
                response_product_description = parse_jsonp(jsonp_str)

        # 네트워크 응답 이벤트를 캡처합니다.
        page.on('response', handle_response)
        
        for product_link in product_links:
            # 제품 링크 열기
            page.goto(product_link)
            
            # # 로그인 팝업 끄기
            # try:
            #     page.wait_for_selector('.baxia-dialog-close', timeout=3000)
            #     page.click('.baxia-dialog-close')
            # except TimeoutError:
            #     # 셀렉터가 나타나지 않으면 아무 작업도 하지 않음
            #     pass
            
            # 특정 네트워크 응답을 기다림      
            with page.expect_response(
                lambda response: "mtop.taobao.pcdetail.data.get" in response.url
            ) as response_info:
                response = ''

            with page.expect_response(
                lambda response: "mtop.taobao.detail.getdesc" in response.url
            ) as response_info:
                response = ''
            
            time.sleep(3 + random.random()*3)
            
            product_info_json = response_product_info['data']
            product_description_json = response_product_description['data']
            
            actual_product_link = page.url
            product_id = get_product_id(actual_product_link)
            product_name = product_info_json['item']['title']
            thumbnail_urls = product_info_json['item']['images']
            product_option = parse_sku_data_to_options(product_info_json)
            product_properties = product_info_json['componentsVO']['extensionInfoVO']['infos']
            detail_image_urls = extract_image_links_from_html(product_description_json['data']['components']['componentData']['desc_richtext_pc']['model']['text'])
            
            # 제품 정보를 JSON 파일로 저장
            product_info = {
                "product_id": product_id, # taobao product ID
                "product_name": product_name, # name
                "thumbnail_urls": thumbnail_urls,
                "product_options": product_option,
                "product_properties": product_properties,
                "detail_image_urls": detail_image_urls # images
            }

            # TODO: 실제 user_id를 사용하여 저장 경로를 생성합니다.
            product_info_dir = os.path.join("images", 'test', product_id)
            os.makedirs(product_info_dir, exist_ok=True)

            save_to_json(product_info, os.path.join(product_info_dir, "product_info.json"))
        
        # 쿠키 및 로컬 스토리지 저장
        save_storage(context, 'storage_state.json')
        browser.close()