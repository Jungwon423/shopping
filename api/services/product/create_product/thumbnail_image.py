def create_image_payload(image_urls):
    """
    대표 이미지와 선택 이미지를 분리하여 네이버 API 형식에 맞는 이미지 페이로드를 생성합니다.

    Args:
        image_urls (list): 이미지 URL 리스트.

    Returns:
        dict: 네이버 API 형식에 맞는 이미지 페이로드 딕셔너리.
    """
    payload = {
            "representativeImage": {
                "url": image_urls[0]
            },
            "optionalImages": [
                {"url": url} for url in image_urls[1:]
            ]
    }
    return payload