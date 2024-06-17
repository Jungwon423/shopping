import http.client
from pymongo import MongoClient
import leaf_category

# MongoDB 클라이언트 설정
client = MongoClient("mongodb://localhost:27017/")
db = client["SmartStore"]
product_collection = db["products"]
refined_product_collection = db["refined_products"]

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
                image_links.append(dict[key]['model']['picUrl'])
        return image_links

def extract_product_info(product_id=None):
    documents = product_collection.find()
    
    document = documents[4]
    
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
    
    print(product_info)
    
    return product_info

def refine_product_info(product_info):
    
    # leaf category & name 생성
    leaf_category_and_name = leaf_category.create_leaf_category(product_info['product_name'])
    
    return {
        "leafCategoryId": leaf_category_and_name['leaf_category'],
        "name": leaf_category_and_name['name'],
        "detailContent": "",
        "images": "",
        "salePrice": 0,
        "stockQuantity": 0,
        "optionInfo": {},
        "productInfoProvidedNotice": "",
        "sellerTags": ""
    }

def create_product_payload(product):
    return {
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
            },
        },
        "smartstoreChannelProduct": {
            "naverShoppingRegistration": True,
            "channelProductDisplayStatusType": "ON",
        },
    }

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

extract_product_info()