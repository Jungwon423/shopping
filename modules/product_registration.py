import http.client

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