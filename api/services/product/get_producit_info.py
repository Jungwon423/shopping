# MongoDB 클라이언트 설정
from datetime import datetime
from pymongo import MongoClient


client = MongoClient("mongodb://localhost:27017/")
db = client["SmartStore"]
raw_product_collection = db["products_raw_data"]
processed_product_collection = db["products_processed_data"]


def format_product_data(products):
    formatted_products = []

    for product in products:
        if product.get('status') == 'processed':
            payload = product.get('payload', {})
            origin_product = payload.get('originProduct', {})
            detail_attribute = origin_product.get('detailAttribute', {})
            delivery_info = origin_product.get('deliveryInfo', {})
            delivery_fee = delivery_info.get('deliveryFee', {})
            sale_price = origin_product.get('salePrice', 0)

            # 대표 이미지 설정
            image_url = origin_product.get('images', {}).get('representativeImage', {}).get('url', '')

            # 가격 범위 계산
            option_combinations = detail_attribute.get('optionInfo', {}).get('optionCombinations', [])
            if option_combinations:
                prices = [option.get('price', 0) + sale_price for option in option_combinations]
                price_min = min(prices)
                price_max = max(prices)
                price = f"{price_min:,.2f}원~{price_max:,.2f}원"
            else:
                price = f"{sale_price:,.2f}원"

            # 배송비 계산
            shipping_fee = f"{delivery_fee.get('deliveryFeePayType', '0')}원"
            overseas_shipping_fee = f"{delivery_fee.get('deliveryAreaType', {}).get('area3extraFee', 0)}원"

            formatted_product = {
                "imageUrl": image_url,
                "productName": origin_product.get('name', ''),
                "price": price,
                "shippingFee": f"{delivery_fee.get('deliveryFeePayType', '0원')} (반품 {delivery_info.get('claimDeliveryInfo', {}).get('returnDeliveryFee', 0)}원, 교환 {delivery_info.get('claimDeliveryInfo', {}).get('exchangeDeliveryFee', 0)}원)",
                "overseasShippingFee": overseas_shipping_fee,
                "costPrice": f"{sale_price:,.2f}원",
                "exchangeRate": "¥1 = 191.55208원",  # 예시 환율
                "productId": product.get('product_id', ''),
                "site": "Taobao.com",  # 예시 사이트
                "date": product.get('created_time', datetime.now()).strftime('%Y/%m/%d')
            }

            formatted_products.append(formatted_product)
        else:
            # "status" field만 반환
            formatted_products.append({"status": product.get('status')})

    return formatted_products