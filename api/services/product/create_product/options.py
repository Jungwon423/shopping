def parse_sku_data_to_options(json_data):
    
    data = json_data
    result = {
        "optionCombinationGroupNames": {},
        "optionCombinations": [],
        "useStockManagement": True
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
        "stockQuantity": lowest_price_option['stockQuantity'],
        "optionCombinationGroupNames": {},
        "optionCombinations": [],
        "useStockManagement": True
    }

def parse_sku_data_to_options_and_get_lowest(json_data):
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
    
    # Mapping option group names
    for index, prop in enumerate(props):
        result['optionCombinationGroupNames'][f'optionGroupName{index + 1}'] = prop['name']
    
    lowest_price = float('inf')
    lowest_price_stock = 0
    all_prices = []
    
    # First pass: find the lowest price
    for sku_id in skus_info:
        price = int(skus_info[sku_id]['price']['priceMoney'])
        all_prices.append(price)
        if price < lowest_price:
            lowest_price = price
            lowest_price_stock = int(skus_info[sku_id]['quantity'])
    
    # Set the threshold price (1.5 times the lowest price)
    threshold_price = lowest_price * 1.5
    
    # Second pass: extract sku details and options
    for sku_property in skus_properties:
        sku_id = sku_property['skuId']
        
        # Check if sku_id exists in skus_info
        if sku_id not in skus_info:
            continue
        
        sku_info = skus_info[sku_id]
        price = int(sku_info['price']['priceMoney'])
        stock_quantity = int(sku_info['quantity'])
        
        # Skip this option if its price exceeds the threshold
        if price > threshold_price:
            continue
        
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
            "stockQuantity": stock_quantity,
            "price": price - lowest_price
        }
        
        # Add optionName1, optionName2, optionName3, and optionName4 only if they are not empty strings
        if len(props) > 0 and options.get(props[0]['name'], ""):
            option_combination["optionName1"] = options[props[0]['name']]
        if len(props) > 1 and options.get(props[1]['name'], ""):
            option_combination["optionName2"] = options[props[1]['name']]
        if len(props) > 2 and options.get(props[2]['name'], ""):
            option_combination["optionName3"] = options[props[2]['name']]
        if len(props) > 3 and options.get(props[3]['name'], ""):
            option_combination["optionName4"] = options[props[3]['name']]
        
        result['optionCombinations'].append(option_combination)
    
    # Set the lowest price and its stock quantity
    result['price'] = lowest_price
    result['stockQuantity'] = lowest_price_stock
    
    return result