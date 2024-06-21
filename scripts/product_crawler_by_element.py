from dotenv import load_dotenv
import os
import json
from playwright.sync_api import sync_playwright
import time
from urllib.parse import urlparse, parse_qs

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

def scroll_to_bottom(page):
    """
    주어진 Playwright 페이지 인스턴스를 천천히 아래로 스크롤합니다.

    Parameters:
    page (Page): Playwright 페이지 인스턴스
    """
    scroll_script = """
        async (step, delay) => {
            let totalHeight = 0;
            let distance = window.innerHeight / step;
            while (totalHeight < document.body.scrollHeight) {
                window.scrollBy(0, distance);
                totalHeight += distance;
                await new Promise(resolve => setTimeout(resolve, delay));
            }
        }
    """
    
    print("Scrolling to bottom...")
    # 아래와 같이 사용하여 스크립트와 인자를 따로 전달합니다.
    page.evaluate(f"({scroll_script})(50, 5)")
    # 스크롤이 완료될 시간을 기다림
    page.wait_for_timeout(1000)

def scroll_to_top(page):
    """
    주어진 Playwright 페이지 인스턴스를 천천히 위로 스크롤합니다.

    Parameters:
    page (Page): Playwright 페이지 인스턴스
    """
    scroll_script = """
        async (step, delay) => {
            while (window.scrollY > 0) {
                let scrollStep = Math.ceil(window.scrollY / step);
                window.scrollBy(0, -scrollStep);
                await new Promise(resolve => setTimeout(resolve, delay));
            }
        }
    """
    
    print("Scrolling to top...")
    # 스크립트와 인자를 따로 전달합니다.
    page.evaluate(f"({scroll_script})(50, 5)")
    # 스크롤이 완료될 시간을 기다림
    page.wait_for_timeout(1000)

def save_to_json(data, filename):
    """
    데이터를 JSON 파일로 저장합니다.

    Parameters:
    data (dict or list): JSON으로 저장할 데이터
    filename (str): 저장할 파일의 경로
    """
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def download_image(image_url, save_path, page):
    """
    주어진 URL에서 이미지를 다운로드하여 지정된 경로에 저장합니다.

    Parameters:
    url (str): 이미지 URL
    save_path (str): 이미지 저장 경로
    page (Page): Playwright 페이지 인스턴스
    """
    response = page.request.get(image_url)
    if response.status == 200:
        with open(save_path, 'wb') as file:
            file.write(response.body())
        print(f"Image downloaded successfully: {save_path}")
    else:
        print(f"Failed to download image: {image_url}. Status: {response.status}, Reason: {response.status_text}")


########################################

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
        
        # 제품 링크 열기
        page.goto(product_link)
        
        # 로그인 팝업 끄기
        try:
            page.wait_for_selector('.baxia-dialog-close', timeout=3000)
            page.click('.baxia-dialog-close')
        except TimeoutError:
            # 셀렉터가 나타나지 않으면 아무 작업도 하지 않음
            pass
        
        # 페이지를 맨 아래/위로 스크롤
        scroll_to_bottom(page)
        scroll_to_top(page)
        
        time.sleep(1)
        
        actual_product_link = page.url
        product_id = get_product_id(actual_product_link)
        product_name = get_product_name(page)
        thumbnail_urls = get_product_thumbnails(page, product_id)
        product_option = get_product_option(page)
        product_properties = get_product_properties(page)
        detail_image_urls = get_product_details(page, product_id)
        
        # 제품 정보를 JSON 파일로 저장
        product_info = {
            "product_id": product_id,
            "product_name": product_name,
            "product_options": product_option,
            "product_properties": product_properties,
            "thumbnail_urls": thumbnail_urls,
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

def get_product_name(page):
    """
    주어진 Playwright 페이지 인스턴스에서 제품 이름을 추출합니다.

    Parameters:
    page (Page): Playwright 페이지 인스턴스

    Returns:
    str: 추출된 제품 이름
    """
    # 제품 이름이 포함된 요소 선택
    page.wait_for_selector('h1.ItemHeader--mainTitle--1rJcXZz')
    product_name_element = page.query_selector('h1.ItemHeader--mainTitle--1rJcXZz')
    
    # 요소에서 텍스트 추출
    product_name = product_name_element.inner_text()
    
    print(f"Product name: {product_name}")
    
    return product_name

def get_product_thumbnails(page, product_id, user_id='test'):
    """
    주어진 Playwright 페이지 인스턴스에서 제품 썸네일 이미지를 추출하여 저장합니다.

    Parameters:
    page (Page): Playwright 페이지 인스턴스
    user_id (str): 사용자 ID
    product_id (str): 제품 ID

    Returns:
    bool: 이미지 추출 및 저장 성공 여부
    """
    # 썸네일 이미지 요소 선택자
    thumbnail_elements = page.query_selector_all('ul.PicGallery--thumbnails--3EG14Q2 img')

    # 로컬 저장 경로 설정
    thumbnail_dir = os.path.join("images", user_id, product_id, "thumbnails")
    os.makedirs(thumbnail_dir, exist_ok=True)

    # 썸네일 이미지 URL 리스트
    image_urls = []
    
    # 썸네일 이미지 저장
    for index, img_element in enumerate(thumbnail_elements):
        image_url = img_element.get_attribute('src')
        if image_url.startswith('//'):
            image_url = 'https:' + image_url
        
        # 이미지 URL 리스트에 추가
        image_urls.append(image_url)
        
        # 이미지 파일 이름 생성
        image_name = f'thumb_image_{index + 1}.jpg'
        save_path = os.path.join(thumbnail_dir, image_name)
        
        # 이미지 다운로드
        download_image(image_url, save_path, page)
        print(f"Thumbnail image saved to: {save_path}")

    return image_urls

def get_product_option(page):
    """
    주어진 Playwright 페이지 인스턴스에서 제품 옵션을 추출합니다.

    Parameters:
    page (Page): Playwright 페이지 인스턴스

    Returns:
    list: 추출된 제품 옵션 리스트
    """
    # 옵션 분류명
    # TODO: 옵션 분류가 여러 개일 경우 처리
    page.wait_for_selector('.ItemLabel--label--3_r0ZNT .ItemLabel--labelText--3QV48AM')
    option_name = page.query_selector('.ItemLabel--label--3_r0ZNT .ItemLabel--labelText--3QV48AM').inner_text()
    
    print(f"Option name: {option_name}")
    
    # 각 옵션의 셀렉터를 가져옵니다.
    option_selectors = page.query_selector_all('.SkuContent--valueItem--1Q1b8S3')
    
    results = []

    for option in option_selectors:
        # 옵션 클릭
        option.click()
        
        # 가격 정보가 업데이트되기를 기다립니다.
        page.wait_for_selector('.Price--priceText--1oEHppn')
        
        # 옵션 이미지, 이름, 가격을 가져옵니다.
        image = option.query_selector('img')
        try:
            image_src = image.get_attribute('src')
            if not image_src:
                image_src = None
        except Exception as e:
            image_src = None

        print('image_src:', image_src)

        name = option.query_selector('.SkuContent--valueItemText--21q8M9E').inner_text()
        price = page.query_selector('.Price--priceText--1oEHppn').inner_text()

        results.append({
            'image': image_src,
            'name': name,
            'price': price
        })

    return results

def get_product_properties(page):
    """
    주어진 Playwright 페이지 인스턴스에서 제품 속성을 추출합니다.

    Parameters:
    page (Page): Playwright 페이지 인스턴스

    Returns:
    dict: 추출된 제품 속성 딕셔너리
    """
    # 정보를 저장할 딕셔너리 초기화
    parameters = {}

    # 각 정보 항목을 선택합니다.
    info_items = page.query_selector_all('.InfoItem--infoItem--zCvv3MH')

    for item in info_items:
        # 키와 값을 추출합니다.
        key = item.query_selector('.InfoItem--infoItemTitle--RNDVIHj').get_attribute('title')
        value = item.query_selector('.InfoItem--infoItemContent--3ia0hBf').get_attribute('title')
        
        # 딕셔너리에 저장합니다.
        parameters[key] = value

    return parameters

def get_product_details(page, product_id, user_id='test'):
    """
    주어진 Playwright 페이지 인스턴스에서 제품 상세 이미지를 추출하여 저장합니다.

    Parameters:
    page (Page): Playwright 페이지 인스턴스
    user_id (str): 사용자 ID
    product_id (str): 제품 ID

    Returns:
    bool: 이미지 추출 및 저장 성공 여부
    """
    
    # 상세 이미지 요소 선택자
    detail_elements = page.query_selector_all('.descV8-container img')


    # 로컬 저장 경로 설정
    detail_dir = os.path.join("images", user_id, product_id, "details")
    os.makedirs(detail_dir, exist_ok=True)
    
    # 상세 이미지 URL 리스트
    image_urls = []
    
    # 상세 이미지 저장
    for index, img_element in enumerate(detail_elements):
        image_url = img_element.get_attribute('src') or img_element.get_attribute('data-src')
        if image_url.startswith('//'):
            image_url = 'https:' + image_url
            
        # 이미지 URL 리스트에 추가
        image_urls.append(image_url)
        
        # 이미지 파일 이름 생성
        image_name = f'detail_image_{index + 1}.jpg'
        save_path = os.path.join(detail_dir, image_name)
        
        # 이미지 다운로드
        download_image(image_url, save_path, page)
        print(f"Detail image saved to: {save_path}")

    return image_urls

get_product_info("https://item.taobao.com/item.htm?priceTId=2100c80717182171949451856e0c31&id=576815286685&ns=1&abbucket=6#detail")