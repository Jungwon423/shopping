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
