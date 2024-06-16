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

def parse_sku_data(json_data):
    data = json.loads(json_data)

    # 1. 가격 정보 추출
    sku_info = data['skuCore']['sku2info']
    sku_prices = {}
    for sku_id, info in sku_info.items():
        price_text = info['price']['priceText']
        sku_prices[str(sku_id)] = price_text  # Ensure sku_id is treated as string

    # 2. 옵션 및 이미지 정보 추출
    props = data['skuBase']['props']
    option_dict = {}
    for prop in props:
        name = prop['name']
        values = prop['values']
        for value in values:
            option_dict[value['vid']] = {
                'name': value['name'],
                'image': value.get('image', None)
            }

    # 3. SKU ID와 옵션 매핑 정보 추출
    skus = data['skuBase']['skus']
    sku_options = {}
    for sku in skus:
        sku_id = sku['skuId']
        prop_path = sku['propPath'].split(';')
        options = [option_dict[vid.split(':')[1]] for vid in prop_path]
        sku_options[sku_id] = options

    # 최종 출력
    result = []
    for sku_id, options in sku_options.items():
        sku_data = {
            "sku_id": sku_id,
            "price": sku_prices.get(sku_id, 'N/A'),
            "options": []
        }
        for option in options:
            option_data = {
                "name": option['name'],
                "image": option['image']
            }
            sku_data["options"].append(option_data)
        result.append(sku_data)
    return result

def parse_sku_data_to_options(json_data):
    data = json.loads(json_data)
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
        
        option_combination = {
            "id": sku_id,
            "optionName1": options.get(props[0]['name'], ""),
            "optionName2": options.get(props[1]['name'], ""),
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
                print(f"Response URL: {response.json()}")
                response_product_info = response.json()
            elif response.status == 200 and 'mtop.taobao.detail.getdesc' in response.url:
                print('@@@@@@@@@')
                print(f"Response URL: {response.text()}")
                jsonp_str = response.text()
                response_product_description = parse_jsonp(jsonp_str)

        # 네트워크 응답 이벤트를 캡처합니다.
        page.on('response', handle_response)
        
        for product_link in product_links:
            # 제품 링크 열기
            page.goto(product_link)
            
            # 로그인 팝업 끄기
            try:
                page.wait_for_selector('.baxia-dialog-close', timeout=3000)
                page.click('.baxia-dialog-close')
            except TimeoutError:
                # 셀렉터가 나타나지 않으면 아무 작업도 하지 않음
                pass
            
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
            product_description_json = response_product_description
            
            actual_product_link = page.url
            product_id = get_product_id(actual_product_link)
            product_name = product_info_json['item']['title']
            thumbnail_urls = product_info_json['item']['images']
            product_option = parse_sku_data_to_options(product_description_json)
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

get_product_info(["https://click.simba.taobao.com/cc_im?p=%C3%C0%C8%DD%C9%B3%C1%FA%D2%CE&s=1179920772&k=1549&e=MiHjIFDBKE6Dzf%2FvITO7sEZmLfqffUJeXjqNsSnrLV9lUd1Vq2tWy7oMOwWssTWQ07wOSSJWEfuKPnWyyGNr3x977EgpOixF09x%2BHZac%2BWA1mPkbBSlcKgR94erwJwidH1dovqwCAnLsPk33hZ7F1mN6FIQ9PZWnduUwk9AF0bcmof0KrXLpyqEt65sK%2FmY3TPnbPfS7k44sTBvquacd%2FsAd9yQ%2FZmMXFBZN6aRXE2kydiFfNuW%2BrCpxkFzvWX2sNZBrIQr16fUirfRmSc8XSna15O8ifaQHOpiYACmp7JeKIkl5WRNdM9LmJ1k8HY9YlTEjbJDiZ91%2Bdo5PIIjLxB7L5jThhRlV%2BqZUTaSfopvJqIbbjtP3ujJaBbP8Z0CzpM1TEmkg0FnVK0Pj9b0IfsCBhYqJZ%2BSxOQ1e3CmBWQWyacRRtnM52ziZqMLxrxPZwGJoh8jUfZAJaDYoVwABaTJlaJyTu%2FNnbTQJ5Jlx0Iwm9QCgFUfF6mJs%2B8NYZGSzo%2FJXgONmdylIF3Flw2CQpy%2BUH%2F%2FA5X4HVwGlKOVi0x2hHClDNzXoHKcpuO7g7IU0q1%2Fo%2FnaIIthiJ%2FfG%2B1fx2dzYVNcbY7YbKVZOC7mG74lmXmli3fCriT9z6PaimQdhXs9nITR5ti6lXr1XU4beOWEJprHuE5QfJdhSxNbJWMTS%2FAwFLht78wUrs5F1BwCRe4yRmHvnzW0uOsthIZB5ckkUP5Jnl%2F1G1JgEzoPUFo6Q38vsKo6L%2FKfX0uTrwJzcqOVOMq5ygu5%2BiVoL%2F7IaS2uIODJ%2BFXBxx5vklnSRWWx4jaLf1rfv4Bwf4YDRKXw7GrGhdNBKVHpDksBn8lrd%2Fvg4j5%2Bj8WdImQZrUXyLodne%2BWNHIPp4qyOjakjKOYuKQHi8vySCI6TmgeIkSchCHj1veAdbRD8VZtKlnfsn27Uci1tGLFCL6bHm1VRtHTpYQy1F6%2FtyeiyxalesylsFNAp0eTKV8BTDjApK2VAHPn39nYJhfDf8mCI6bXobhgECiD5bds0411lUlpcv7qUT5pb%2FNmBLlNfXNvIfRRaZzimELXVW6Hz6EIXsBxeQKJb%2F60C7SIZW5nUKFqGqLhhYf2nF1pqOXITDHjgySh6Imnr8j0yCLLCzcm0BYZbVFIbVfErnPmyrZC85DV7cKYFZBeW1a%2BV4ez7ZE2r%2Bw3V%2Ffcjd9RjMJ0vwHufELjGENhoR6pgHV1ABypxq31JyixvKY1BEwS0u4%2BfFDIUHp9IfU4nM9vQneUEaHxp0Itix2iiCDu8o5DEi7TpBM3SUiqqr9ak8ENdvElb81%2FcItDY8U8YDMXfBcYPJRfTfc9kh39L885DS%2BVCqOFI5DHyMtwmFb8mohtuO0%2Fe6HwmwOwtUIU1LpZGlJRHB1Qw392PkEhgJeaLV3h2YuB8JO%2BholEkEvzh9yZGW%2FKnc5DAF2EnaZYtXAaUo5WLTHdu3RZ0zFIoJTMI8hNv3ZhezPeAUvb7cLu1PyjTVj8XnkanyLQvAEzMUtxL46nh9htvH73IvQ%2BA9SyeUqQxxVys%3D#detail", "https://item.taobao.com/item.htm?id=576815286685&ns=1&abbucket=6#detail"])