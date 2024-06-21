from api.utils.ensure_https import ensure_https

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

def extract_image_links(dict):
    if 'desc_richtext_pc' in dict:
        return extract_image_links_from_html(dict['desc_richtext_pc']['model']['text'])
    else:
        image_links = []
        for key in dict:
            if key.startswith('detail_pic'):
                image_links.append(ensure_https(dict[key]['model']['picUrl']))
        return image_links

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