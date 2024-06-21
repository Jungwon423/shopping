from typing import List
import requests

from api.utils.naver_oauth import get_access_token
from api.utils.download_image import download_image

def upload_image_to_naver(image_urls: List[str], client_id="3CCF8wa60QZFqM40L9KTme", client_secret="$2a$04$t58Bu4kYetpNCt7Cf7fQHO") -> List[str]:
    """
    이미지 URL 리스트를 받아 Naver API를 통해 이미지를 업로드하고 결과를 반환합니다.
    이미지 URL은 10개 단위로 처리됩니다.

    Args:
        image_urls (List[str]): 업로드할 이미지 URL 리스트
        client_id (str): Naver API 클라이언트 ID
        client_secret (str): Naver API 클라이언트 시크릿

    Returns:
        List[str]: 업로드된 이미지 URL 리스트
    """
    # Naver API 액세스 토큰 가져오기
    access_token = get_access_token(client_id, client_secret)
    print(f"Access Token: {access_token[:10]}...")  # 토큰의 처음 10자만 출력
    
    url = "https://api.commerce.naver.com/external/v1/product-images/upload"
    headers = {
        'Authorization': f"Bearer {access_token}",
    }

    all_uploaded_images = []
    batch_size = 10

    # 이미지 URL을 10개씩 묶어 처리
    for i in range(0, len(image_urls), batch_size):
        batch = image_urls[i:i+batch_size]
        files = []
        
        # 각 이미지 URL을 다운로드하여 파일로 준비
        for idx, image_url in enumerate(batch):
            image_data = download_image(image_url)
            if image_data:
                files.append(('imageFiles', (f'image_{idx}.jpg', image_data, 'image/jpeg')))
        
        # 준비된 파일이 있는 경우 업로드
        if files:
            print(f"Uploading batch {i//batch_size + 1} with {len(files)} images")
            response = requests.post(url, headers=headers, files=files)
            print(f"Response for batch {i//batch_size + 1}: {response.status_code}")
            print(response.text[:500] + "...")  # 응답의 처음 500자만 출력
            
            # 응답이 성공적인 경우 업로드된 이미지 URL 추출
            if response.status_code == 200:
                uploaded_images = response.json().get("images", [])
                all_uploaded_images.extend([img.get("url") for img in uploaded_images if img.get("url")])
            else:
                print(f"Error in batch {i//batch_size + 1}: {response.status_code} - {response.text}")

    return all_uploaded_images
