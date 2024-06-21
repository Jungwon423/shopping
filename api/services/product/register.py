import json
from pymongo import MongoClient
import requests

from api.services.product.create_product.category import create_leaf_category
from api.services.product.create_product.seller_tag import create_seller_tag
from api.services.product.create_product.thumbnail_image import create_image_payload
from api.utils.naver_oauth import get_access_token
from api.utils.upload_image import upload_image_to_naver
from api.services.product.create_product.detail_images import create_detail_content_payload, extract_image_links
from api.services.product.create_product.options import parse_sku_data_to_options_and_get_lowest

# MongoDB 클라이언트 설정
client = MongoClient("mongodb://localhost:27017/")
db = client["SmartStore"]
product_collection = db["products"]
refined_product_collection = db["refined_products"]

def extract_product_info(product_id=None):
    """
    MongoDB에서 제품 정보를 추출하여 JSON 형식으로 반환합니다.

    Args:
        product_id (str, optional): 특정 제품의 ID. 기본값은 None.

    Returns:
        dict: 추출된 제품 정보.
    """
    documents = product_collection.find()
    
    document = documents[1]
    
    product_info_json = document['product_info']['data']
    product_description_json = document['product_detail']['data']
    
    actual_product_link = document['url']
    product_id = product_info_json['item']['itemId']
    product_name = product_info_json['item']['title']
    thumbnail_urls = upload_image_to_naver(product_info_json['item']['images'])
    product_option = parse_sku_data_to_options_and_get_lowest(product_info_json)
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

def refine_product_info(product_info):
    """
    추출된 제품 정보를 정제하여 네이버 스마트스토어 API 형식에 맞는 데이터를 생성합니다.

    Args:
        product_info (dict): 추출된 제품 정보.

    Returns:
        dict: 정제된 제품 정보.
    """
    # leaf category & name 생성
    leaf_category_and_name = create_leaf_category(product_info['product_name'])
    detail_content = create_detail_content_payload(product_info['detail_image_urls'])
    images = create_image_payload(product_info['thumbnail_urls'])
    
    return {
        "leafCategoryId": leaf_category_and_name['leaf_category'],
        "name": leaf_category_and_name['name'],
        "detailContent": detail_content,
        "images": images,
        "salePrice": product_info['product_options']['price'],
        "stockQuantity": product_info['product_options']['stockQuantity'],
        "optionInfo": {
            "optionCombinationGroupNames": product_info['product_options']['optionCombinationGroupNames'],
            "optionCombinations": product_info['product_options']['optionCombinations'],
            "useStockManagement": True
        },
        # TODO: productInfoProvidedNotice 추가
        "productInfoProvidedNotice": {
            "productInfoProvidedNoticeType": "ETC",
            "etc": {
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
    """
    정제된 제품 정보를 기반으로 네이버 스마트스토어 API에 맞는 페이로드를 생성합니다.

    Args:
        product (dict): 정제된 제품 정보.

    Returns:
        dict: 네이버 스마트스토어 API에 맞는 페이로드.
    """
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
                "originAreaInfo" : {
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

def send_product_info_request(payload, client_id="3CCF8wa60QZFqM40L9KTme", client_secret="$2a$04$t58Bu4kYetpNCt7Cf7fQHO"):
    """
    주어진 페이로드를 사용하여 Naver API에 POST 요청을 보냅니다.

    Args:
        payload (dict): JSON 형식의 페이로드.
        client_id (str): 클라이언트 ID.
        client_secret (str): 클라이언트 시크릿.

    Returns:
        str: 응답 데이터의 디코딩된 문자열.
    """
    access_token = get_access_token(client_id, client_secret)

    url = "https://api.commerce.naver.com/external/v2/products"
    headers = {
        'Authorization': f"Bearer {access_token}",
        'Content-Type': "application/json"
    }

    response = requests.post(url, headers=headers, json=payload)
    
    print(response.text)

    return response.text

# 테스트 코드

product_info = extract_product_info()
refined_product_info = refine_product_info(product_info)
payload = create_product_payload(refined_product_info)
response = send_product_info_request(payload)