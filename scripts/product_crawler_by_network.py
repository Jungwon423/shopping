from playwright.sync_api import Playwright, sync_playwright, expect
import json
import random
from pymongo import MongoClient

# MongoDB 클라이언트 설정
client = MongoClient("mongodb://localhost:27017/")
db = client["SmartStore"]
product_collection = db["products"]

URLLIST = {}
PRODUCT_INFO = {}
PRODUCT_DETAIL = {}

# results.json 파일을 읽어옴
with open("results.json", "r", encoding="utf-8") as f:
    data = json.load(f)
    for key in data:
        currentKeyLinks = sorted(data[key], key=lambda x: -x["sales"])[:5]
        currentKeyLinks = [x["href"] for x in data[key]]
        URLLIST.update({key: currentKeyLinks})

def jsonp_to_json(jsonp_str):
    """
    JSONP 문자열을 JSON 객체로 변환합니다.

    Args:
        jsonp_str (str): 변환할 JSONP 문자열.

    Returns:
        dict: 변환된 JSON 객체.
    """
    try:
        return json.loads(jsonp_str)
    except:
        json_str = jsonp_str.split("(", 1)[1].rsplit(")", 1)[0]
        return json.loads(json_str)

def load_storage(context, cookies_path):
    """
    파일에서 쿠키를 로드하고 브라우저 컨텍스트에 설정합니다.

    Args:
        context: Playwright 브라우저 컨텍스트.
        cookies_path (str): 쿠키 파일 경로.
    """
    with open(cookies_path, "r") as f:
        cookies = json.load(f)
    context.add_cookies(cookies)

def run(URLLIST) -> None:
    """
    Playwright를 사용하여 웹 스크래핑을 수행하고 데이터를 MongoDB에 저장하는 메인 함수입니다.

    Args:
        URLLIST (dict): 키워드와 해당 URL을 포함한 딕셔너리.
    """
    with sync_playwright() as playwright:
        global PRODUCT_INFO
        global PRODUCT_DETAIL

        browser = playwright.chromium.launch(headless=False)
        context = browser.new_context()

        load_storage(context, "cookies.json")

        page = context.new_page()
        page.set_viewport_size({"width": 1920, "height": 1080})

        def handle_response(response):
            """
            HTTP 응답을 처리하여 제품 정보와 세부 정보를 추출합니다.

            Args:
                response: Playwright 응답 객체.
            """
            global PRODUCT_INFO
            global PRODUCT_DETAIL
            if response.status == 200 and "mtop.taobao.pcdetail.data.get" in response.url:
                try:
                    jsonp_str = response.text()
                    temp = jsonp_to_json(jsonp_str)
                    if temp.get("data", {}).get("seller", {}):
                        PRODUCT_INFO = temp
                except Exception as e:
                    pass
            elif response.status == 200 and "mtop.taobao.detail.getdesc" in response.url:
                try:
                    jsonp_str = response.text()
                    temp = jsonp_to_json(jsonp_str)
                    if temp.get("api", None):
                        PRODUCT_DETAIL = temp
                except Exception as e:
                    pass

        page.on("response", handle_response)
        cnt = 0
        errorCnt = 0

        for key in URLLIST:
            for url in URLLIST[key]:
                cnt += 1
                PRODUCT_INFO = None
                PRODUCT_DETAIL = None
                page.goto(url)
                page.wait_for_timeout((5000 + 4000 * random.random()) * 6)

                if PRODUCT_INFO is None or PRODUCT_DETAIL is None:
                    errorCnt += 1
                print(f"Crawling {cnt}/480 ({errorCnt} errors)")

                # MongoDB에 저장
                product_collection.insert_one({
                    "product_info": PRODUCT_INFO,
                    "product_detail": PRODUCT_DETAIL,
                    "url": page.url,
                    "keyword": key, 
                })

        # 브라우저 컨텍스트와 브라우저 닫기
        context.close()
        browser.close()

run(URLLIST)
