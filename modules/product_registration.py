import http.client
from pymongo import MongoClient
import leaf_category
import process_images
import json
import product_sourcing_by_network
import os
from dotenv import load_dotenv
from openai import OpenAI
import re
import requests

# MongoDB 클라이언트 설정
client = MongoClient("mongodb://localhost:27017/")
db = client["SmartStore"]
product_collection = db["products"]
refined_product_collection = db["refined_products"]

# .env 파일을 로드합니다.
load_dotenv(override=True)

# OpenAI API 키 설정
openai_api_key = os.getenv('OPENAI_API_KEY')
print('openai_api_key:', openai_api_key)

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

def extract_image_links(dict):
    if 'desc_richtext_pc' in dict:
        return extract_image_links_from_html(dict['desc_richtext_pc']['model']['text'])
    else:
        image_links = []
        for key in dict:
            if key.startswith('detail_pic'):
                image_links.append(product_sourcing_by_network.ensure_https(dict[key]['model']['picUrl']))
        return image_links

def get_lowest_price_option(product_options):
    """
    주어진 product_options 객체에서 가장 가격이 낮은 상품의 price와 stockQuantity를 반환합니다.

    Args:
        product_options (dict): 제품 옵션 정보가 포함된 딕셔너리.

    Returns:
        dict: 가장 가격이 낮은 상품의 price와 stockQuantity.
    """
    # 옵션 목록에서 가장 낮은 가격의 상품 찾기
    lowest_price_option = min(product_options['optionCombinations'], key=lambda x: x['price'])
    
    # 결과를 dict 형태로 반환
    return {
        "price": lowest_price_option['price'],
        "stockQuantity": lowest_price_option['stockQuantity']
    }

def extract_product_info(product_id=None):
    documents = product_collection.find()
    
    document = documents[1]
    
    product_info_json = document['product_info']['data']
    product_description_json = document['product_detail']['data']
    
    actual_product_link = document['url']
    product_id = product_info_json['item']['itemId']
    product_name = product_info_json['item']['title']
    thumbnail_urls = product_info_json['item']['images']
    product_option = parse_sku_data_to_options(product_info_json)
    product_properties = product_info_json['componentsVO']['extensionInfoVO']['infos']
    detail_image_urls = extract_image_links(product_description_json['components']['componentData'])
    
    product_info = {
        "actual_product_link": actual_product_link,
        "product_id": product_id,
        "product_name": product_name,
        "thumbnail_urls": thumbnail_urls,
        "product_options": product_option,
        "product_properties": product_properties,
        "detail_image_urls": detail_image_urls
    }
    
    print(json.dumps(product_info, indent=4, ensure_ascii=False))
    
    return product_info

def create_seller_tag(product_name):
    client = OpenAI(api_key=openai_api_key)
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system", 
                "content": "You run an overseas fulfillment business that sources products from overseas e-commerce sites like Taobao and sells them back to Korean e-commerce sites. Your task is to take a given product name and think of 20 keywords that people in Korea might be searching for. Given the product name you need to generate keywords for, give me the keywords in the following JSON format. {{\"keywords\": \"List of keywords\"}}"
            },
            {
                "role": "user", 
                "content": product_name
            }
        ]
    )
    
    # 응답에서 JSON 형식의 문자열 추출
    response_text = re.search(r'\{.*?\}', response.choices[0].message.content, re.DOTALL).group(0)
    print(f'번역 결과 (JSON): {response_text}')
    
    # JSON 형식의 문자열을 파싱
    response_json = json.loads(response_text)
    
    generated_keywords = response_json["keywords"]
    print(f'생성된 키워드: {generated_keywords}')
    
    return [{"text": text} for text in generated_keywords]

def refine_product_info(product_info):
    
    # leaf category & name 생성
    leaf_category_and_name = leaf_category.create_leaf_category(product_info['product_name'])
    detail_content = process_images.create_detail_content_payload(product_info['detail_image_urls'])
    images = process_images.create_image_payload(product_info['thumbnail_urls'])
    price_and_stock = get_lowest_price_option(product_info['product_options'])
    
    return {
        "leafCategoryId": leaf_category_and_name['leaf_category'],
        "name": leaf_category_and_name['name'],
        "detailContent": detail_content,
        "images": images,
        "salePrice": price_and_stock['price'],
        "stockQuantity": price_and_stock['stockQuantity'],
        "optionInfo": product_info['product_options'],
        # TODO: productInfoProvidedNotice 추가
        "productInfoProvidedNotice": {
            "productInfoProvidedNoticeType": "ETC",
            "productInfoProvidedNoticeContent": {
                    "returnCostReason": "1",
                    "noRefundReason": "1",
                    "qualityAssuranceStandard": "1",
                    "compensationProcedure": "1",
                    "troubleShootingContents": "1",
                    "itemName": "상품상세 참조",
                    "modelName": "상품상세 참조",
                    "manufacturer": "상품상세 참조",
                    "customerServicePhoneNumber": "01034540252"
                }

        },
        "sellerTags": create_seller_tag(product_info['product_name'])
    }

def create_product_payload(product):
    payload = {
        "originProduct" : {
            "statusType" : "SALE",
            "leafCategoryId" : product["leafCategoryId"],
            "name" : product["name"],
            "detailContent" : product["detailContent"],
            "images" : product["images"],
            "salePrice" : product["salePrice"],
            "stockQuantity" : product["stockQuantity"],
            "deliveryInfo" : {
                "deliveryType" : "DELIVERY",
                "deliveryAttributeType" : "NORMAL",
                "deliveryCompany" : "CJGLS", # TODO: 배대지에서 입력받은 배송사를 입력
                "deliveryFee" : {
                    "deliveryFeeType" : "FREE",
                    "deliveryFeePayType" : "PREPAID",
                    "deliveryAreaType" : {
                        "deliveryAreaType" : "AREA_3",
                        "area2extraFee" : 5000,
                        "area3extraFee" : 5000 # TODO: 내가 놓쳤던 부분 --> 다시 확인
                    }
                },
                "claimDeliveryInfo" : {
                    "returnDeliveryFee" : 20000,
                    "exchangeDeliveryFee" : 40000,
                    "shippingAddressId" : "", # TODO: 배대지 출고지 주소 입력
                    "returnAddressId" : "" # TODO: 반품지 주소 입력 (우리 집?)
                }
            },
            "detailAttribute" : {
                "afterServiceInfo" : {
                    "afterServiceTelephoneNumber" : "01034540252",
                    "afterServiceGuideContent" : "톡톡이나 문자로 문의주시면 최대한 빠르게 답변 드리겠습니다."
                },
                "OriginAreaInfo" : {
                    "originAreaCode": "0200037",
                    "importer": "수입산",
                    "content": "중국산(수입산)", # TODO: 필수 아닌데 넣은 이유?
                },
                "sellerCodeInfo": {
                    "sellerManagementCode": "226502934", # TODO: 판매자 코드 어떤 값?
                },
                "optionInfo" : product["optionInfo"], # TODO: "useStockManagement": True 까먹지 말기
                "certificationTargetExcludeContent" : {
                    "kcExemptionType": "OVERSEAS",
                    "kcCertifiedProductExclusionYn": "KC_EXEMPTION_OBJECT",
                },
                "minorPurchasable": True,
                "productInfoProvidedNotice": product["productInfoProvidedNotice"],
                "seoInfo": {
                    "sellerTags": product["sellerTags"],
                }
            },
        },
        "smartstoreChannelProduct": {
            "naverShoppingRegistration": True,
            "channelProductDisplayStatusType": "ON",
        },
    }
    
    print(json.dumps(payload, indent=4, ensure_ascii=False))
    
    return payload

def register_product(BEARER_TOKEN, payload):
    conn = http.client.HTTPSConnection("api.commerce.naver.com")
    
    headers = {
    'Authorization': "Bearer " + BEARER_TOKEN,
    'content-type': "application/json"
    }

    conn.request("POST", "/external/v2/products", payload, headers)

    res = conn.getresponse()
    data = res.read()

    print(data.decode("utf-8"))

create_product_payload(refine_product_info(extract_product_info()))

def send_product_info_request(payload, bearer_token):
    """
    주어진 페이로드를 사용하여 Naver API에 POST 요청을 보냅니다.

    Args:
        payload (str): JSON 형식의 페이로드 문자열.
        bearer_token (str): API 인증을 위한 베어러 토큰.

    Returns:
        str: 응답 데이터의 디코딩된 문자열.
    """
    url = "https://api.commerce.naver.com/external/v2/products"
    headers = {
        'Authorization': f"Bearer {bearer_token}",
        'Content-Type': "application/json"
    }

    response = requests.post(url, headers=headers, data=payload)

    return response.text