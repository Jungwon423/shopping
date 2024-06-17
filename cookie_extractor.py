from playwright.sync_api import sync_playwright
import json

# "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=8888


def get_existing_browser_storage(remote_debugging_url):
    with sync_playwright() as p:
        # 브라우저에 CDP를 통해 연결
        browser = p.chromium.connect_over_cdp(remote_debugging_url)
        default_context = browser.contexts[0]
        page = default_context.pages[0]

        # 쿠키와 로컬 스토리지 가져오기
        cookies = page.context.cookies()

        # Playwright를 위한 저장소 파일 생성
        with open("cookies.json", "w") as f:
            json.dump(cookies, f, indent=2)

        print("Cookies and Local Storage have been saved.")

        # Playwright 페이지 닫기
        page.close()
        browser.close()


if __name__ == "__main__":
    get_existing_browser_storage("http://localhost:8888")
