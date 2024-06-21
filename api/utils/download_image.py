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
        response = requests.get(image_url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.content
    except requests.RequestException as e:
        print(f'Error downloading image: {e}')
        return None