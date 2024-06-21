def ensure_https(url):
    """
    주어진 URL이 https://로 시작하지 않으면 https://로 시작하도록 변환합니다.

    Args:
        url (str): 변환할 URL

    Returns:
        str: 변환된 URL
    """
    # URL이 https://로 시작하지 않는 경우 처리
    if not url.startswith("https://"):
        # URL이 //로 시작하는 경우 https:를 추가
        if url.startswith("//"):
            return "https:" + url
        # URL이 http://로 시작하거나 다른 형식인 경우 https://를 추가
        else:
            return "https://" + url
    # URL이 이미 https://로 시작하는 경우 그대로 반환
    return url
