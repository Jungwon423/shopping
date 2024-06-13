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
    # 'mtopjsonp1('와 마지막 ')'를 제거
    jsonp_str = jsonp_str.strip()
    if jsonp_str.startswith("mtopjsonp1(") and jsonp_str.endswith(")"):
        jsonp_str = jsonp_str[len("mtopjsonp1("):-1]
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

        response_data = {}
        
        def handle_response(response):
            if response.status == 200 and 'mtop.taobao.pcdetail.data.get' in response.url:
                response_data['product_info'] = response.json()
            elif response.status == 200 and 'mtop.taobao.detail.getdesc' in response.url:
                jsonp_str = response.text()
                print(jsonp_str)
                response_data['product_description'] = parse_jsonp(jsonp_str)
                print(parse_jsonp(jsonp_str))
                print(response_data['product_description'])

        # 네트워크 응답 이벤트를 캡처합니다.
        page.on('response', handle_response)

        # 제품 링크 열기
        page.goto(product_link)
        
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
        
        save_to_json(response_data['product_info'], 'network_product_info.json')
        save_to_json(response_data['product_description'], 'network_product_description.json')
        
        product_info_json = response_data['product_info']['data']
        product_description_json = response_data['product_description']
        
        actual_product_link = page.url
        product_id = get_product_id(actual_product_link)
        product_name = product_info_json['item']['title']
        thumbnail_urls = product_info_json['item']['images']
        product_option = []
        product_properties = product_info_json['componentsVO']['extensionInfoVO']['infos']
        detail_image_urls = extract_image_links_from_html(product_description_json['data']['components']['componentData']['desc_richtext_pc']['model']['text'])
        
        # 제품 정보를 JSON 파일로 저장
        product_info = {
            "product_id": product_id,
            "product_name": product_name,
            "thumbnail_urls": thumbnail_urls,
            "product_options": product_option,
            "product_properties": product_properties,
            "detail_image_urls": detail_image_urls
        }

        # TODO: 실제 user_id를 사용하여 저장 경로를 생성합니다.
        product_info_dir = os.path.join("images", 'test', product_id)
        os.makedirs(product_info_dir, exist_ok=True)

        save_to_json(product_info, os.path.join(product_info_dir, "product_info.json"))
        
        # 쿠키 및 로컬 스토리지 저장
        save_storage(context, 'storage_state.json')
        browser.close()

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

# get_product_info("https://item.taobao.com/item.htm?priceTId=2100c80717182171949451856e0c31&id=576815286685&ns=1&abbucket=6#detail")

# JSON 데이터 (여기에 JSON 데이터를 삽입합니다)
json_data = """
{
    "skuCore": {
            "sku2info": {
                "0": {
                    "logisticsTime": "付款后10天内发货",
                    "moreQuantity": "true",
                    "price": {
                        "priceActionText": "",
                        "priceActionType": "buy_in_mobile",
                        "priceMoney": "45000",
                        "priceText": "450-1080"
                    },
                    "quantity": "200",
                    "quantityText": "有货"
                },
                "4976877232879": {
                    "cartParam": {
                        "addCartCheck": "true"
                    },
                    "logisticsTime": "付款后10天内发货",
                    "moreQuantity": "true",
                    "price": {
                        "priceActionText": "",
                        "priceActionType": "buy_in_mobile",
                        "priceMoney": "78000",
                        "priceText": "780"
                    },
                    "quantity": "200",
                    "quantityText": "有货"
                },
                "4976877232881": {
                    "cartParam": {
                        "addCartCheck": "true"
                    },
                    "logisticsTime": "付款后10天内发货",
                    "moreQuantity": "true",
                    "price": {
                        "priceActionText": "",
                        "priceActionType": "buy_in_mobile",
                        "priceMoney": "45000",
                        "priceText": "450"
                    },
                    "quantity": "200",
                    "quantityText": "有货"
                },
                "4715115274405": {
                    "cartParam": {
                        "addCartCheck": "true"
                    },
                    "logisticsTime": "付款后10天内发货",
                    "moreQuantity": "true",
                    "price": {
                        "priceActionText": "",
                        "priceActionType": "buy_in_mobile",
                        "priceMoney": "108000",
                        "priceText": "1080"
                    },
                    "quantity": "200",
                    "quantityText": "有货"
                },
                "4976877232880": {
                    "cartParam": {
                        "addCartCheck": "true"
                    },
                    "logisticsTime": "付款后10天内发货",
                    "moreQuantity": "true",
                    "price": {
                        "priceActionText": "",
                        "priceActionType": "buy_in_mobile",
                        "priceMoney": "55000",
                        "priceText": "550"
                    },
                    "quantity": "200",
                    "quantityText": "有货"
                },
                "4716213653677": {
                    "cartParam": {
                        "addCartCheck": "true"
                    },
                    "logisticsTime": "付款后10天内发货",
                    "moreQuantity": "true",
                    "price": {
                        "priceActionText": "",
                        "priceActionType": "buy_in_mobile",
                        "priceMoney": "58000",
                        "priceText": "580"
                    },
                    "quantity": "200",
                    "quantityText": "有货"
                },
                "4225472291946": {
                    "cartParam": {
                        "addCartCheck": "true"
                    },
                    "logisticsTime": "付款后10天内发货",
                    "moreQuantity": "true",
                    "price": {
                        "priceActionText": "",
                        "priceActionType": "buy_in_mobile",
                        "priceMoney": "69000",
                        "priceText": "690"
                    },
                    "quantity": "200",
                    "quantityText": "有货"
                },
                "4869442741318": {
                    "cartParam": {
                        "addCartCheck": "true"
                    },
                    "logisticsTime": "付款后10天内发货",
                    "moreQuantity": "true",
                    "price": {
                        "priceActionText": "",
                        "priceActionType": "buy_in_mobile",
                        "priceMoney": "58000",
                        "priceText": "580"
                    },
                    "quantity": "200",
                    "quantityText": "有货"
                }
            },
            "skuItem": {
                "itemStatus": "0",
                "renderSku": "true",
                "unitBuy": "1"
            }
        },
    "skuBase": {
            "components": [],
            "props": [
                {
                    "hasImage": "true",
                    "name": "颜色分类",
                    "nameDesc": "（7）",
                    "pid": "1627207",
                    "values": [
                        {
                            "image": "https://gw.alicdn.com/bao/uploaded/i1/344550392/O1CN015HLm661Ela8t2z4lW_!!344550392.jpg",
                            "name": "款式一矮靠背大底盘",
                            "sortOrder": "0",
                            "vid": "27794997203"
                        },
                        {
                            "image": "https://gw.alicdn.com/bao/uploaded/i3/344550392/O1CN01FheqIj1Ela8wUMBww_!!344550392.jpg",
                            "name": "美发镜台",
                            "sortOrder": "2",
                            "vid": "14256905"
                        },
                        {
                            "image": "https://gw.alicdn.com/bao/uploaded/i4/344550392/O1CN01bsiMFb1Ela5IakATP_!!344550392.jpg",
                            "name": "款式二不锈钢底盘双杆脚踏",
                            "sortOrder": "3",
                            "vid": "27794997204"
                        },
                        {
                            "image": "https://gw.alicdn.com/bao/uploaded/i1/344550392/O1CN01nMPRJj1Ela5G3hvM3_!!344550392.jpg",
                            "name": "款式二不锈钢底盘单杆脚踏",
                            "sortOrder": "4",
                            "vid": "27794997205"
                        },
                        {
                            "image": "https://gw.alicdn.com/bao/uploaded/i2/344550392/O1CN01i89g0Y1Ela5B1l9xa_!!344550392.jpg",
                            "name": "款式三不锈钢底盘u型脚踏",
                            "sortOrder": "5",
                            "vid": "24069526118"
                        },
                        {
                            "image": "https://gw.alicdn.com/bao/uploaded/i4/344550392/O1CN01EM1RSF1Ela51nI8LY_!!344550392.jpg",
                            "name": "款式二黑色底盘",
                            "sortOrder": "6",
                            "vid": "26751570850"
                        },
                        {
                            "image": "https://gw.alicdn.com/bao/uploaded/i1/344550392/O1CN01cQKPrg1Ela0saLK0Q_!!344550392.jpg",
                            "name": "款式四",
                            "sortOrder": "7",
                            "vid": "5552051"
                        }
                    ]
                },
                {
                    "hasImage": "false",
                    "name": "套餐类型",
                    "pid": "5919063",
                    "values": [
                        {
                            "name": "官方标配",
                            "sortOrder": "1",
                            "vid": "6536025"
                        }
                    ]
                }
            ],
            "skus": [
                {
                    "propPath": "1627207:27794997203;5919063:6536025",
                    "skuId": "4225472291946"
                },
                {
                    "propPath": "1627207:14256905;5919063:6536025",
                    "skuId": "4715115274405"
                },
                {
                    "propPath": "1627207:27794997204;5919063:6536025",
                    "skuId": "4716213653677"
                },
                {
                    "propPath": "1627207:27794997205;5919063:6536025",
                    "skuId": "4869442741318"
                },
                {
                    "propPath": "1627207:24069526118;5919063:6536025",
                    "skuId": "4976877232879"
                },
                {
                    "propPath": "1627207:26751570850;5919063:6536025",
                    "skuId": "4976877232880"
                },
                {
                    "propPath": "1627207:5552051;5919063:6536025",
                    "skuId": "4976877232881"
                }
            ]
        }
}
"""

# 함수 호출 및 결과 출력
result = parse_sku_data(json_data)
for item in result:
    print(f"SKU ID: {item['sku_id']}")
    print(f"Price: {item['price']}")
    for option in item['options']:
        print(f"Option: {option['name']}")
        if option['image']:
            print(f"Image: {option['image']}")
    print("-----")