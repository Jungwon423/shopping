import requests

def download_image(image_url: str) -> bytes:
    """
    이미지 URL에서 이미지를 다운로드하여 바이트 데이터로 반환합니다.

    Args:
        image_url (str): 이미지 URL

    Returns:
        bytes: 이미지 바이트 데이터 또는 None (실패 시)
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        # 이미지 URL에서 GET 요청을 통해 이미지를 다운로드
        response = requests.get(image_url, headers=headers, timeout=10)
        # 응답 상태 코드가 200(성공)이 아닌 경우 예외 발생
        response.raise_for_status()
        # 성공적으로 다운로드된 이미지의 바이트 데이터를 반환
        return response.content
    except requests.RequestException as e:
        # 다운로드 중 오류가 발생하면 오류 메시지를 출력하고 None을 반환
        print(f'Error downloading image: {e}')
        return None
