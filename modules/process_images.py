def create_image_payload(image_urls):
    """
    대표 이미지와 선택 이미지를 분리하여 이미지 페이로드를 생성합니다.

    Args:
        image_urls (list): 이미지 URL 리스트.

    Returns:
        dict: 대표 이미지와 선택 이미지를 포함하는 딕셔너리.
    """
    return {
        "representativeImage": image_urls[0],
        "optionalImages": image_urls[1:]
    }

def create_detail_content_payload(detail_image_urls):
    """
    이미지 URL 리스트를 사용하여 상세 콘텐츠를 위한 HTML 페이로드를 생성합니다.

    Args:
        detail_image_urls (list): 제품 상세 정보를 위한 이미지 URL 리스트.

    Returns:
        str: 생성된 HTML 코드.
    """
    # HTML 템플릿 시작 부분
    html = """
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>제품 상세 이미지</title>
        <style>
            .image-container {
                text-align: center;
                margin: 20px 0;
            }
            .image-container img {
                max-width: 750px;
                width: 100%;
                height: auto;
            }
        </style>
    </head>
    <body>
    """

    # 각 이미지 URL에 대해 HTML 생성
    for url in detail_image_urls:
        html += f"""
        <div class="image-container">
            <img src="{url}" alt="Product Image">
        </div>
        """

    # HTML 템플릿 종료 부분
    html += """
    </body>
    </html>
    """

    # 페이로드로 반환
    return html