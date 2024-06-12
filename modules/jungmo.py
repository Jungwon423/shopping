from playwright.sync_api import Playwright, sync_playwright, expect
import json
import random
from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017/")
db = client["SmartStore"]
category_collection = db["category"]
keyword_collection = db["keyword"]

KEYWORDLIST = []

categories = category_collection.find()
search_categories = []
cnt = 0
for category in categories:
    for rank in category["ranks"]:
        cnt += 1
        if cnt <= 288:
            continue
        search_categories.append(
            {
                "cid": category["cid"],
                "category": category["category"],
                "keyword": rank["keyword"],
                "rank": rank["rank"],
            }
        )


def run(playwright: Playwright) -> None:
    global KEYWORDLIST
    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()

    def handle_response(response):
        global KEYWORDLIST
        if response.status == 200:
            if "keywordstool" in response.url:
                try:
                    KEYWORDLIST = response.json()["keywordList"]
                except Exception as e:
                    print(f"Failed to process response: {e}")

            elif "managedKeyword" in response.url and KEYWORDLIST:
                try:
                    keywordInfos = response.json()
                    for keywordInfo in keywordInfos:
                        keywordName = keywordInfo["keyword"]

                        # KEYWORDLIST에 있는 키워드 정보에 추가: relKeyword 랑 일치
                        for keyword in KEYWORDLIST:
                            if keyword["relKeyword"] == keywordName:
                                keyword.update(keywordInfo)
                                break

                except Exception as e:
                    print(f"Failed to process response: {e}")

    # 네트워크 응답 가로채기
    page.on("response", handle_response)

    # 네이버 메인 페이지로 이동
    page.goto("https://www.naver.com/")

    # 네이버 로그인 페이지로 이동
    page.get_by_role("link", name="NAVER 로그인").click()

    # 아이디 입력
    page.get_by_placeholder("아이디").click()
    page.get_by_placeholder("아이디").fill("jungmo324")

    # 비밀번호 입력
    page.get_by_placeholder("비밀번호").click()
    page.get_by_placeholder("비밀번호").fill("mequer98!")

    # 로그인 버튼 클릭
    page.get_by_role("button", name="로그인").click()

    # 로그인 후 이동할 페이지로 대기
    page.wait_for_load_state("networkidle")

    # 키워드 플래너 페이지로 이동
    page.goto(
        "https://manage.searchad.naver.com/customers/3216027/tool/keyword-planner"
    )

    # 팝업 확인 버튼 클릭
    page.get_by_role("button", name="확인").click()

    for search_category in search_categories:

        KEYWORDLIST = []

        # 키워드 입력창 클릭 및 입력
        page.get_by_placeholder("한줄에 하나씩 입력하세요.\n(최대 5개까지)").click()
        page.get_by_placeholder("한줄에 하나씩 입력하세요.\n(최대 5개까지)").fill(
            search_category["keyword"]
        )

        # 조회하기 버튼 클릭
        page.get_by_role("button", name="조회하기").click()

        # 1. 특정 네트워크 응답을 기다림
        with page.expect_response(
            lambda response: "keywordstool" in response.url
        ) as response_info:
            response = response_info.value

        # 2. 응답을 받은 후 8~12초 대기
        page.wait_for_timeout(8000 + 4000 * random.random())

        # 키워드 정보 저장
        search_category["keywordList"] = KEYWORDLIST

        # 키워드 정보 저장
        keyword_collection.insert_one(search_category)

    # 브라우저 닫기 (주석 처리 해제)
    context.close()
    browser.close()


with sync_playwright() as playwright:
    run(playwright)
