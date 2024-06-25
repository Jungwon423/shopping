import json
import os
import re
from dotenv import load_dotenv
from openai import OpenAI

# .env 파일을 로드합니다.
load_dotenv(override=True)

# OpenAI API 키 설정
openai_api_key = os.getenv('OPENAI_API_KEY')

def parse_sku_data_to_options_and_get_lowest(json_data):
    """
    JSON 데이터를 기반으로 제품 옵션을 추출하고, 가장 낮은 가격의 상품 정보를 포함한 결과를 반환합니다.

    Args:
        json_data (dict): 제품 SKU 데이터가 포함된 JSON 객체.

    Returns:
        dict: 추출된 제품 옵션과 가장 낮은 가격의 상품 정보를 포함한 딕셔너리.
    """
    data = json_data
    result = {
        "optionCombinationGroupNames": {},
        "optionCombinations": [],
        "useStockManagement": True,
        "price": None,
        "stockQuantity": None
    }
    
    props = data['skuBase']['props']
    skus_info = data['skuCore']['sku2info']
    skus_properties = data['skuBase']['skus']
    
    # 옵션 그룹 이름 매핑
    for index, prop in enumerate(props):
        result['optionCombinationGroupNames'][f'optionGroupName{index + 1}'] = prop['name']
    
    lowest_price = float('inf')
    lowest_price_stock = 0
    all_prices = []
    
    # 첫 번째 패스: 가장 낮은 가격 찾기
    for sku_id in skus_info:
        price = int(skus_info[sku_id]['price']['priceMoney'])
        all_prices.append(price)
        if price < lowest_price:
            lowest_price = price
            lowest_price_stock = int(skus_info[sku_id]['quantity'])
    
    # 임계 가격 설정 (가장 낮은 가격의 1.5배)
    threshold_price = lowest_price * 1.5
    
    # 두 번째 패스: SKU 세부 정보 및 옵션 추출
    for sku_property in skus_properties:
        sku_id = sku_property['skuId']
        
        # sku_id가 skus_info에 존재하는지 확인
        if sku_id not in skus_info:
            continue
        
        sku_info = skus_info[sku_id]
        price = int(sku_info['price']['priceMoney'])
        stock_quantity = int(sku_info['quantity'])
        
        # 가격이 임계 값을 초과하면 이 옵션을 건너뜀
        if price > threshold_price:
            continue
        
        # propPath 분리 및 옵션 값 추출
        prop_path = sku_property['propPath'].split(';')
        options = {}
        for prop in prop_path:
            prop_id, val_id = prop.split(':')
            for prop_item in props:
                if prop_item['pid'] == prop_id:
                    for val in prop_item['values']:
                        if val['vid'] == val_id:
                            options[prop_item['name']] = val['name']
        
        # 옵션 조합 딕셔너리 생성
        option_combination = {
            "stockQuantity": stock_quantity,
            "price": price - lowest_price
        }
        
        # 옵션 이름이 빈 문자열이 아닌 경우에만 추가
        if len(props) > 0 and options.get(props[0]['name'], ""):
            option_combination["optionName1"] = options[props[0]['name']]
        if len(props) > 1 and options.get(props[1]['name'], ""):
            option_combination["optionName2"] = options[props[1]['name']]
        if len(props) > 2 and options.get(props[2]['name'], ""):
            option_combination["optionName3"] = options[props[2]['name']]
        if len(props) > 3 and options.get(props[3]['name'], ""):
            option_combination["optionName4"] = options[props[3]['name']]
        
        result['optionCombinations'].append(option_combination)
    
    # 가장 낮은 가격과 해당 재고 수량 설정
    result['price'] = lowest_price
    result['stockQuantity'] = lowest_price_stock
    
    return result

def process_options(raw_option_data):
    """
    주어진 옵션 데이터를 기반으로 한국에서 이해하기 쉽게 수정된 옵션 데이터를 생성합니다.

    Args:
        raw_option_data (dict): 옵션 데이터를 포함한 딕셔너리.

    Returns:
        dict: 수정된 옵션 데이터를 포함한 딕셔너리.
    """
    client = OpenAI(api_key=openai_api_key)
    
    print('원본:', json.dumps(raw_option_data, indent=4, ensure_ascii=False))
    
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {
                "role": "system", 
                "content": '''You run an overseas fulfillment business that sources products from overseas e-commerce sites like Taobao and sells them back to Korean e-commerce sites. Your task is to modify the option names in Korean to make them understandable to Korean consumers given the optionGroupName and optionCombination. Given an object containing information about product options, provide me with the option information in the following JSON format, preserving the shape of the object and modified in Korean.
{{\"processed_option_data\": \"The object you modified\"}}
!IMPORTANT : Create an object with the following format : 
"optionCombinationGroupNames" : {
    "optionGroupName1": "modified option group name",
    "optionGroupName2": ......
},
"optionCombinations": List of
    {
        "optionName1": "modified option name",
        "optionName2": "......
    }'''
            },
            {
                "role": "user", 
                "content": json.dumps(raw_option_data)
            }
        ]
    )
    
    print('응답:', response.choices[0].message.content)
    
    # 응답에서 JSON 형식의 문자열 추출
    response_text = response.choices[0].message.content
    
    # JSON 형식의 문자열을 찾기 위한 정규 표현식
    json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
    
    if not json_match:
        raise ValueError("JSON 형식의 데이터를 응답에서 찾을 수 없습니다.")
    
    json_str = json_match.group(0)
    
    # JSON 형식의 문자열을 파싱
    response_json = json.loads(json_str)
    
    processed_option_data = response_json["processed_option_data"]
    
    print('번역 결과:', json.dumps(processed_option_data, indent=4, ensure_ascii=False))
    
    return processed_option_data

def translate_with_gpt3(text):
    """
    주어진 중국어 텍스트를 GPT-3.5를 사용하여 한국어로 번역합니다.
    
    Args:
        text (str): 번역할 중국어 텍스트.
        
    Returns:
        str: 번역된 한국어 텍스트.
    """
    client = OpenAI(api_key=openai_api_key)
    
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are in charge of translating Chinese to Korean for a company that sources products from Taobao and sells them on a Korean e-commerce platform. Given the option information of the product in chinese, you need to translate them into Korean in the following JSON format. {“translated_text”: “Your translation into Korean}"},
            {"role": "user", "content": text}
        ],
        temperature=0
    )
    
    # 응답에서 JSON 형식의 문자열 추출
    response_text = re.search(r'\{.*?\}', response.choices[0].message.content, re.DOTALL).group(0)
    
    # JSON 형식의 문자열을 파싱
    response_json = json.loads(response_text)
    
    translated_text = response_json["translated_text"]
    print(f'번역 결과: {translated_text}')
    
    return translated_text

def process_product_options(product_options):
    """
    제품 옵션 데이터를 처리하여 가격을 변환하고 번역된 옵션 정보를 적용합니다.

    Args:
        product_options (dict): 제품 옵션 데이터를 포함한 딕셔너리.

    Returns:
        dict: 번역된 옵션 정보를 포함한 제품 옵션 딕셔너리.
    """
    # Step 1: 가격 변환
    product_options['price'] = product_options['price'] / 100
    for option in product_options['optionCombinations']:
        option['price'] = option['price'] / 100

    # Step 2: 필요한 값 추출
    raw_option_data = {
        'raw_optionCombinationGroupNames': {},
        'raw_optionCombinations': []
    }

    for key, value in product_options['optionCombinationGroupNames'].items():
        raw_option_data['raw_optionCombinationGroupNames'][key] = value

    for option in product_options['optionCombinations']:
        raw_option = {
            'optionName1': option['optionName1']
        }
        if 'optionName2' in option:
            raw_option['optionName2'] = option['optionName2']
        if 'optionName3' in option:
            raw_option['optionName3'] = option['optionName3']
        if 'optionName4' in option:
            raw_option['optionName4'] = option['optionName4']
        raw_option_data['raw_optionCombinations'].append(raw_option)

    # Step 3: 번역 적용
    processed_option_data = {
        'processed_optionCombinationGroupNames': {},
        'processed_optionCombinations': []
    }

    for key, value in raw_option_data['raw_optionCombinationGroupNames'].items():
        processed_option_data['processed_optionCombinationGroupNames'][key] = translate_with_gpt3(value)

    for option in raw_option_data['raw_optionCombinations']:
        processed_option = {}
        for key, value in option.items():
            processed_option[key] = translate_with_gpt3(value)
        processed_option_data['processed_optionCombinations'].append(processed_option)

    # Step 4: 번역된 값 적용
    product_options['optionCombinationGroupNames'] = processed_option_data['processed_optionCombinationGroupNames']

    for i, option in enumerate(product_options['optionCombinations']):
        if i < len(processed_option_data['processed_optionCombinations']):
            processed_option = processed_option_data['processed_optionCombinations'][i]
            option['optionName1'] = processed_option['optionName1']
            if 'optionName2' in option and 'optionName2' in processed_option:
                option['optionName2'] = processed_option['optionName2']
            if 'optionName3' in option and 'optionName3' in processed_option:
                option['optionName3'] = processed_option['optionName3']
            if 'optionName4' in option and 'optionName4' in processed_option:
                option['optionName4'] = processed_option['optionName4']
    
    print('번역된 옵션:', json.dumps(product_options, indent=4, ensure_ascii=False))

    return product_options

# # 테스트 코드
# product_options = {
#     "optionCombinationGroupNames": {
#         "optionGroupName1": "颜色分类"
#     },
#     "optionCombinations": [
#         {
#             "stockQuantity": 200,
#             "price": 52955,
#             "optionName1": "MZ-051B"
#         },
#         {
#             "stockQuantity": 200,
#             "price": 81435,
#             "optionName1": "MZ-051D"
#         },
#         {
#             "stockQuantity": 200,
#             "price": 52955,
#             "optionName1": "MZ-051A蓝灰色"
#         },
#         {
#             "stockQuantity": 11,
#             "price": 71467,
#             "optionName1": "MZ-051D连体沙发（特价款）"
#         },
#         {
#             "stockQuantity": 200,
#             "price": 52955,
#             "optionName1": "MZ-051A灰色"
#         },
#         {
#             "stockQuantity": 200,
#             "price": 0,
#             "optionName1": "面料颜色尺寸定制请联系客服"
#         }
#     ],
#     "useStockManagement": True,
#     "price": 167765,
#     "stockQuantity": 200
# }

# processed_options = process_product_options(product_options)
