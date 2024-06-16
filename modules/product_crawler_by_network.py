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
                response_product_info = response.json()
            elif response.status == 200 and 'mtop.taobao.detail.getdesc' in response.url:
                jsonp_str = response.text()
                response_product_description = parse_jsonp(jsonp_str)

        # 네트워크 응답 이벤트를 캡처합니다.
        page.on('response', handle_response)
        
        for product_link in product_links:
            # 제품 링크 열기
            page.goto(product_link)
            
            # # 로그인 팝업 끄기
            # try:
            #     page.wait_for_selector('.baxia-dialog-close', timeout=3000)
            #     page.click('.baxia-dialog-close')
            # except TimeoutError:
            #     # 셀렉터가 나타나지 않으면 아무 작업도 하지 않음
            #     pass
            
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
            product_description_json = response_product_description['data']
            
            actual_product_link = page.url
            product_id = get_product_id(actual_product_link)
            product_name = product_info_json['item']['title']
            thumbnail_urls = product_info_json['item']['images']
            product_option = parse_sku_data_to_options(product_info_json)
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

# get_product_info(["https://click.simba.taobao.com/cc_im?p=%C3%C0%C8%DD%C9%B3%C1%FA%D2%CE&s=1179920772&k=1549&e=MiHjIFDBKE6Dzf%2FvITO7sEZmLfqffUJeXjqNsSnrLV9lUd1Vq2tWy7oMOwWssTWQ07wOSSJWEfuKPnWyyGNr3x977EgpOixF09x%2BHZac%2BWA1mPkbBSlcKgR94erwJwidH1dovqwCAnLsPk33hZ7F1mN6FIQ9PZWnduUwk9AF0bcmof0KrXLpyqEt65sK%2FmY3TPnbPfS7k44sTBvquacd%2FsAd9yQ%2FZmMXFBZN6aRXE2kydiFfNuW%2BrCpxkFzvWX2sNZBrIQr16fUirfRmSc8XSna15O8ifaQHOpiYACmp7JeKIkl5WRNdM9LmJ1k8HY9YlTEjbJDiZ91%2Bdo5PIIjLxB7L5jThhRlV%2BqZUTaSfopvJqIbbjtP3ujJaBbP8Z0CzpM1TEmkg0FnVK0Pj9b0IfsCBhYqJZ%2BSxOQ1e3CmBWQWyacRRtnM52ziZqMLxrxPZwGJoh8jUfZAJaDYoVwABaTJlaJyTu%2FNnbTQJ5Jlx0Iwm9QCgFUfF6mJs%2B8NYZGSzo%2FJXgONmdylIF3Flw2CQpy%2BUH%2F%2FA5X4HVwGlKOVi0x2hHClDNzXoHKcpuO7g7IU0q1%2Fo%2FnaIIthiJ%2FfG%2B1fx2dzYVNcbY7YbKVZOC7mG74lmXmli3fCriT9z6PaimQdhXs9nITR5ti6lXr1XU4beOWEJprHuE5QfJdhSxNbJWMTS%2FAwFLht78wUrs5F1BwCRe4yRmHvnzW0uOsthIZB5ckkUP5Jnl%2F1G1JgEzoPUFo6Q38vsKo6L%2FKfX0uTrwJzcqOVOMq5ygu5%2BiVoL%2F7IaS2uIODJ%2BFXBxx5vklnSRWWx4jaLf1rfv4Bwf4YDRKXw7GrGhdNBKVHpDksBn8lrd%2Fvg4j5%2Bj8WdImQZrUXyLodne%2BWNHIPp4qyOjakjKOYuKQHi8vySCI6TmgeIkSchCHj1veAdbRD8VZtKlnfsn27Uci1tGLFCL6bHm1VRtHTpYQy1F6%2FtyeiyxalesylsFNAp0eTKV8BTDjApK2VAHPn39nYJhfDf8mCI6bXobhgECiD5bds0411lUlpcv7qUT5pb%2FNmBLlNfXNvIfRRaZzimELXVW6Hz6EIXsBxeQKJb%2F60C7SIZW5nUKFqGqLhhYf2nF1pqOXITDHjgySh6Imnr8j0yCLLCzcm0BYZbVFIbVfErnPmyrZC85DV7cKYFZBeW1a%2BV4ez7ZE2r%2Bw3V%2Ffcjd9RjMJ0vwHufELjGENhoR6pgHV1ABypxq31JyixvKY1BEwS0u4%2BfFDIUHp9IfU4nM9vQneUEaHxp0Itix2iiCDu8o5DEi7TpBM3SUiqqr9ak8ENdvElb81%2FcItDY8U8YDMXfBcYPJRfTfc9kh39L885DS%2BVCqOFI5DHyMtwmFb8mohtuO0%2Fe6HwmwOwtUIU1LpZGlJRHB1Qw392PkEhgJeaLV3h2YuB8JO%2BholEkEvzh9yZGW%2FKnc5DAF2EnaZYtXAaUo5WLTHdu3RZ0zFIoJTMI8hNv3ZhezPeAUvb7cLu1PyjTVj8XnkanyLQvAEzMUtxL46nh9htvH73IvQ%2BA9SyeUqQxxVys%3D#detail", "https://item.taobao.com/item.htm?id=576815286685&ns=1&abbucket=6#detail"])

test = {'seller': {'creditLevel': '6', 'creditLevelIcon': '//gw.alicdn.com/tfs/TB1GvjsiC_I8KJjy0FoXXaFnVXa-132-24.png', 'evaluates': [{'level': '1', 'levelText': '高', 'score': '5.0 ', 'title': '宝贝描述', 'type': 'desc'}, {'level': '1', 'levelText': '高', 'score': '5.0 ', 'title': '卖家服务', 'type': 'serv'}, {'level': '1', 'levelText': '高', 'score': '5.0 ', 'title': '物流服务', 'type': 'post'}], 'pcShopUrl': '//shop557267452.taobao.com', 'sellerId': '2216273476534', 'sellerNick': 'tb245135186', 'sellerType': 'C', 'shopIcon': 'https://img.alicdn.com/imgextra/i2/2216273476534/O1CN01jyRY221y8covUeTTg_!!2216273476534.jpg', 'shopId': '557267452', 'shopName': '安盛家具', 'userId': '2216273476534'}, 'item': {'images': ['https://img.alicdn.com/imgextra/i3/2216273476534/O1CN01plw9681y8cr9oiHdL_!!2216273476534.jpg', 'https://img.alicdn.com/imgextra/i2/2216273476534/O1CN01OKqho71y8cr1rSOd4_!!2216273476534.jpg', 'https://img.alicdn.com/imgextra/i3/2216273476534/O1CN01pkYA4M1y8cr94wuGJ_!!2216273476534.jpg', 'https://img.alicdn.com/imgextra/i2/2216273476534/O1CN01uR0bLx1y8cr9ue2c0_!!2216273476534.jpg', 'https://img.alicdn.com/imgextra/i2/2216273476534/O1CN01pSwqx81y8cr94vIQm_!!2216273476534.jpg'], 'itemId': '803321975230', 'pcADescUrl': '//market.m.taobao.com/app/detail-project/desc/index.html?id=803321975230&descVersion=7.0&type=1&f=icoss!0803321975230!12096298443&sellerType=C', 'qrCode': 'https://h5.m.taobao.com/awp/core/detail.htm?id=803321975230', 'spuId': '0', 'title': '足疗足浴电动沙发按摩床躺椅多功能泡修洗脚桑拿理疗休闲美甲K歌', 'titleIcon': '', 'useWirelessDesc': 'true', 'vagueSellCount': '0'}, 'feature': {'pcResistDetail': 'false', 'tmwOverseasScene': 'false'}, 'plusViewVO': {'headAtmosphereBeltVO': {'bizCode': '', 'valid': 'false'}}, 'skuCore': {'sku2info': {'0': {'logisticsTime': '付款后15天内发货', 'moreQuantity': 'true', 'price': {'priceActionText': '', 'priceActionType': 'buy_in_mobile', 'priceMoney': '167765', 'priceText': '1677.65-2492'}, 'quantity': '200', 'quantityText': '有货'}, '5640093415066': {'cartParam': {'addCartCheck': 'true'}, 'logisticsTime': '付款后15天内发货', 'moreQuantity': 'false', 'price': {'priceActionText': '', 'priceActionType': 'buy_in_mobile', 'priceMoney': '220720', 'priceText': '2207.2'}, 'quantity': '200', 'quantityText': '有货'}, '5640093415067': {'cartParam': {'addCartCheck': 'true'}, 'logisticsTime': '付款后15天内发货', 'moreQuantity': 'false', 'price': {'priceActionText': '', 'priceActionType': 'buy_in_mobile', 'priceMoney': '249200', 'priceText': '2492'}, 'quantity': '200', 'quantityText': '有货'}, '5640093415070': {'cartParam': {'addCartCheck': 'true'}, 'logisticsTime': '付款后15天内发货', 'moreQuantity': 'false', 'price': {'priceActionText': '', 'priceActionType': 'buy_in_mobile', 'priceMoney': '220720', 'priceText': '2207.2'}, 'quantity': '200', 'quantityText': '有货'}, '5640093415071': {'cartParam': {'addCartCheck': 'true'}, 'logisticsTime': '付款后15天内发货', 'moreQuantity': 'false', 'price': {'priceActionText': '', 'priceActionType': 'buy_in_mobile', 'priceMoney': '167765', 'priceText': '1677.65'}, 'quantity': '200', 'quantityText': '有货'}, '5640093415068': {'cartParam': {'addCartCheck': 'true'}, 'logisticsTime': '付款后15天内发货', 'moreQuantity': 'false', 'price': {'priceActionText': '', 'priceActionType': 'buy_in_mobile', 'priceMoney': '220720', 'priceText': '2207.2'}, 'quantity': '200', 'quantityText': '有货'}, '5640093415069': {'cartParam': {'addCartCheck': 'true'}, 'logisticsTime': '付 款后15天内发货', 'moreQuantity': 'false', 'price': {'priceActionText': '', 'priceActionType': 'buy_in_mobile', 'priceMoney': '239232', 'priceText': '2392.32'}, 'quantity': '11', 'quantityText': '有货'}}, 'skuItem': {'itemStatus': '0', 'renderSku': 'true', 'unitBuy': '1'}}, 'services': None, 'params': {'aplusParams': '[]', 'trackParams': {'detailabtestdetail': ''}}, 'skuBase': {'components': [], 'props': [{'hasImage': 'true', 'name': '颜色分类', 'nameDesc': '（6）', 'pid': '1627207', 'values': [{'image': 'https://gw.alicdn.com/bao/uploaded/i4/2216273476534/O1CN01t5EOuB1y8crB527MN_!!2216273476534.jpg', 'name': 'MZ-051B', 'sortOrder': '0', 'vid': '2646054843'}, {'image': 'https://gw.alicdn.com/bao/uploaded/i1/2216273476534/O1CN010eTIfX1y8cr7FGr9R_!!2216273476534.jpg', 'name': 'MZ-051D', 'sortOrder': '1', 'vid': '1145207700'}, {'image': 'https://gw.alicdn.com/bao/uploaded/i3/2216273476534/O1CN01xtjB881y8crDX8m0N_!!2216273476534.jpg', 'name': 'MZ-051A蓝灰色', 'sortOrder': '2', 'vid': '8609251248'}, {'image': 'https://gw.alicdn.com/bao/uploaded/i4/2216273476534/O1CN01JsE0lc1y8crB50i5y_!!2216273476534.jpg', 'name': 'MZ-051D连体沙发（特价款）', 'sortOrder': '3', 'vid': '20193652827'}, {'image': 'https://gw.alicdn.com/bao/uploaded/i4/2216273476534/O1CN01gRaTFs1y8crCwIahr_!!2216273476534.jpg', 'name': 'MZ-051A灰色', 'sortOrder': '4', 'vid': '8531410497'}, {'image': 'https://gw.alicdn.com/bao/uploaded/i3/2216273476534/O1CN01eGewfR1y8crCwI7aT_!!2216273476534.jpg', 'name': '面料颜色尺寸定制请联系客服', 'sortOrder': '5', 'vid': '1808751948'}]}], 'skus': [{'propPath': '1627207:2646054843', 'skuId': '5640093415066'}, {'propPath': '1627207:1145207700', 'skuId': '5640093415067'}, {'propPath': '1627207:8609251248', 'skuId': '5640093415068'}, {'propPath': '1627207:20193652827', 'skuId': '5640093415069'}, {'propPath': '1627207:8531410497', 'skuId': '5640093415070'}, {'propPath': '1627207:1808751948', 'skuId': '5640093415071'}]}, 'pcTrade': {'buyNowUrl': '//buy.taobao.com/auction/buy_now.jhtml', 'pcBuyParams': {'virtual': 'false', 'buy_now': '1885.00', 'auction_type': 'b', 'x-uid': '', 'title': '足疗足浴电动沙发按摩床躺椅多功能泡修洗脚桑拿理疗休闲美甲K歌', 'buyer_from': 'ecity', 'page_from_type': 'main_site_pc', 'detailIsLimit': 'false', 'who_pay_ship': '卖家承担运费', 'rootCatId': '50020611', 'auto_post1': None, 'auto_post': 'false', 'seller_nickname': '安盛家具', 'photo_url': 'i3/2216273476534/O1CN01plw9681y8cr9oiHdL_!!2216273476534.jpg', 'current_price': '1885.00', 'region': '广东佛山', 'seller_id': 'a089159814384a9462d29395b466d69e', 'etm': ''}, 'pcCartParam': {'areaId': '1'}, 'tradeType': '1'}, 'componentsVO': {'deliveryVO': {'agingDesc': '付款后15天内发货', 'areaId': '1', 'deliverToCity': '', 'deliveryFromAddr': '广东佛山', 'deliveryToAddr': '', 'deliveryToDistrict': ''}, 'headImageVO': {'images': ['https://img.alicdn.com/imgextra/i3/2216273476534/O1CN01plw9681y8cr9oiHdL_!!2216273476534.jpg', 'https://img.alicdn.com/imgextra/i2/2216273476534/O1CN01OKqho71y8cr1rSOd4_!!2216273476534.jpg', 'https://img.alicdn.com/imgextra/i3/2216273476534/O1CN01pkYA4M1y8cr94wuGJ_!!2216273476534.jpg', 'https://img.alicdn.com/imgextra/i2/2216273476534/O1CN01uR0bLx1y8cr9ue2c0_!!2216273476534.jpg', 'https://img.alicdn.com/imgextra/i2/2216273476534/O1CN01pSwqx81y8cr94vIQm_!!2216273476534.jpg'], 'videos': []}, 'headerVO': {'buttons': [{'background': {'alpha': '1.0', 'disabledAlpha': '1.0'}, 'disabled': 'false', 'events': [{'fields': {'url': '//s.taobao.com/search'}, 'type': 'onClick'}], 'subTitle': {}, 'title': {'text': '搜索'}, 'type': 'search_in_taobao'}, {'background': {'alpha': '1.0', 'disabledAlpha': '1.0'}, 'disabled': 'false', 'events': [{'fields': {'url': '//shop557267452.taobao.com/search.htm'}, 'type': 'onClick'}], 'subTitle': {}, 'title': {'text': '搜本店'}, 'type': 'search_in_store'}], 'logoJumpUrl': 'https://www.taobao.com', 'mallLogo': 'https://gw.alicdn.com/imgextra/i1/O1CN01z163bz1lHF5yQ50CC_!!6000000004793-2-tps-172-108.png', 'searchText': '搜索宝贝'}, 'storeCardVO': {'buttons': [{'disabled': 'false', 'image': {'gifAnimated': 'false', 'imageUrl': 'https://img.alicdn.com/imgextra/i1/O1CN016DNujx1yMMj6NMXVv_!!6000000006564-55-tps-24-24.svg'}, 'title': {'text': '联系客服'}, 'type': 'customer_service'}, {'disabled': 'false', 'events': [{'fields': {'url': '//shop557267452.taobao.com'}, 'type': 'openUrl'}], 'image': {'gifAnimated': 'false', 'imageUrl': 'https://img.alicdn.com/imgextra/i4/O1CN01jn67ow1ZhYeiTJlZn_!!6000000003226-55-tps-24-24.svg'}, 'title': {'text': '进入店铺'}, 'type': 'enter_shop'}], 'creditLevel': '6', 'creditLevelIcon': '//gw.alicdn.com/tfs/TB1GvjsiC_I8KJjy0FoXXaFnVXa-132-24.png', 'evaluates': [{'level': '1', 'levelText': '高', 'score': '5.0 ', 'title': '宝贝描述', 'type': 'desc'}, {'level': '1', 'levelText': '高', 'score': '5.0 ', 'title': '卖家服务', 'type': 'serv'}, {'level': '1', 'levelText': '高', 'score': '5.0 ', 'title': '物流服务', 'type': 'post'}], 'labelList': [{'contentDesc': '客服平均47秒回复'}, {'contentDesc': '服务体验良好'}], 'overallScore': '4.6', 'sellerType': 'C', 'shopIcon': 'https://img.alicdn.com/imgextra/i2/2216273476534/O1CN01jyRY221y8covUeTTg_!!2216273476534.jpg', 'shopName': '安盛家具', 'shopUrl': '//shop557267452.taobao.com'}, 'bottomBarVO': {'buyInMobile': 'false', 'leftButtons': [{'background': {'alpha': '1.0', 'disabledAlpha': '1.0', 'disabledColor': ['#ff7700', '#ff4900'], 'gradientColor': ['#ff7700', '#ff4900']}, 'disabled': 'false', 'title': {'alpha': '1.0', 'bold': 'true', 'color': '#ffffff', 'disabledAlpha': '0.2', 'disabledColor': '#80ffffff', 'fontSize': '16', 'text': '立即购买'}, 'type': 'buy_now'}, {'background': {'alpha': '1.0', 'disabledAlpha': '1.0', 'disabledColor': ['#ffcb00', '#ff9402'], 'gradientColor': ['#ffcb00', '#ff9402']}, 'disabled': 'false', 'title': {'alpha': '1.0', 'bold': 'true', 'color': '#ffffff', 'disabledAlpha': '0.2', 'disabledColor': '#33ffffff', 'fontSize': '16', 'text': '加入购物车'}, 'type': 'add_cart'}], 'rightButtons': [{'disabled': 'false', 'icon': {'alpha': '1.0', 'color': '#666666', 'disabledAlpha': '1.0', 'disabledColor': '#dddddd', 'iconFontName': '뀚', 'size': '14'}, 'title': {'alpha': '1.0', 'bold': 'false', 'color': '#666666', 'disabledAlpha': '1.0', 'disabledColor': '#666666', 'fontSize': '14', 'text': '收藏'}, 'type': 'collect'}]}, 'titleVO': {'salesDesc': '已售 0', 'subTitles': [], 'title': {'title': '足疗足浴电动沙发按摩床躺椅多功能泡修洗脚桑拿理疗休闲美甲K歌'}}, 'overseasLogisticsVO': {'data': {'deliveryList': [{'buyerAddressText': '', 'logisticsType': '2', 'sellerAddressText': '广东佛山'}], 'eventLogisticsType': '6', 'nonTwoStageLogisticsText': '非二段物流', 'ovsLogisticsPopUrl': 'https://world.taobao.com/wow/z/oversea/new_zebra_order/oversea-delivery-info?wh_biz=tm&wh_biz=tm&wh_weex=true&wh_weex=true&itemId=803321975230&areaId&site=KR&addressId&spm=a2141.7631564.overseaslogistics2.d1&version=logisticsVersion&baobaoText=&isOvsNewcomer=true&solutionType=0&ovsActivityType=0', 'ovsLogisticsTiming': '付款后15天内发货', 'ovsModule': 'false', 'showJiYunRecommend': 'false'}, 'events': {'exposureItem': [{'fields': {'page': 'Page_Detail', 'eventId': '2201', 'arg1': 'Page_Detail_Show-OverseasLogistics5', 'args': {'spm': 'a2141.7631564.overseaslogistics5.d1', 'itemId': '803321975230', 'sellerId': '2216273476534', 'trackPage': 'Page_Detail_Show_Detail_OverseasLogistics5', 'buyerAddrSite': None, 'logisticsAbtest': 'logistics_v4', 'showLogisticsTimingInfo': 'true', 'logisticsType': '6', 'effectiveSite': None}}, 'type': 'userTrack'}]}, 'ultronUIType': 'ovsNonTwoStageDeliveryStyle'}, 'extensionInfoVO': {'infos': [{'items': [{'text': ['Credit/Debit card', '支持韩元支付']}], 'title': '保障', 'type': 'GUARANTEE'}, {'items': [{'text': ['other/其他'], 'title': '品牌'}, {'text': ['TPDg5AoA'], 'title': '型号'}, {'text': ['广东省'], 'title': '产地'}, {'text': ['MZ-051B,MZ-051D,MZ-051A蓝灰色,MZ-051D连体沙发（特价款）,MZ-051A灰色,面料颜色尺寸定制请联系客服'], 'title': '颜色分类'}], 'title': '参数', 'type': 'BASE_PROPS'}]}, 'debugVO': {'host': 'taodetail033054102130.center.na620@33.54.102.130', 'traceId': '2100cfb417185669261677823e0bcf'}, 'rightBarVO': {'buyerButtons': [{'disabled': 'false', 'icon': '//gw.alicdn.com/imgextra/i3/O1CN01CEAqor1T5Bm2U3Ccm_!!6000000002330-2-tps-48-44.png', 'label': '联系客服', 'priority': '100', 'type': 'wangwang'}, {'disabled': 'false', 'icon': '//gw.alicdn.com/imgextra/i3/O1CN01Od2GJC1fxwVlcd1UA_!!6000000004074-2-tps-56-56.png', 'label': '购物车', 'priority': '99', 'type': 'cart'}, {'disabled': 'false', 'href': 'https://h5.m.taobao.com/awp/core/detail.htm?id=803321975230', 'icon': '//gw.alicdn.com/imgextra/i1/O1CN01D84lgZ1zRgxZVZYLE_!!6000000006711-55-tps-28-28.svg', 'label': '商品码', 'priority': '98', 'type': 'qrcode'}, {'disabled': 'false', 'icon': '//gw.alicdn.com/imgextra/i3/O1CN01qyqd6N271bIfKZwyt_!!6000000007737-2-tps-56-56.png', 'label': '反馈', 'priority': '97', 'type': 'feedback'}, {'disabled': 'false', 'href': '//jubao.taobao.com/index.htm?itemId=803321975230&spm=a1z6q.7847058', 'icon': '//gw.alicdn.com/imgextra/i4/O1CN015gkFg01D6X5DPZua9_!!6000000000167-2-tps-56-56.png', 'label': '举报', 'priority': '96', 'type': 'report'}, {'disabled': 'false', 'priority': '1', 'type': 'backTop'}], 'sellerButtons': []}, 'priceVO': {'price': {'hiddenPrice': 'false', 'priceActionText': '', 'priceActionType': 'buy_in_mobile', 'priceColor': '#FF4F00', 'priceDesc': '起', 'priceMoney': '220720', 'priceText': '2207.2', 'priceTitle': '卖家促销', 'priceTitleColor': '#FF4F00', 'priceUnit': '￥'}}}}

print(parse_sku_data_to_options(test))