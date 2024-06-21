def ensure_https(url):
    """
    주어진 URL이 https://로 시작하지 않으면 https://로 시작하도록 변환합니다.

    Parameters:
    url (str): 변환할 URL

    Returns:
    str: 변환된 URL
    """
    if not url.startswith("https://"):
        if url.startswith("//"):
            return "https:" + url
        else:
            return "https://" + url
    return url