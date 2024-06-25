from time import time
import bcrypt
import pybase64
import json
import requests

def make_signature(clientId, clientSecret):
    """
    클라이언트 ID와 클라이언트 시크릿을 기반으로 서명을 생성합니다.

    Args:
        clientId (str): 클라이언트 ID
        clientSecret (str): 클라이언트 시크릿

    Returns:
        str: 생성된 서명 (Base64 인코딩)
    """
    timestamp = int(time() * 1000)
    
    # 클라이언트 ID와 타임스탬프를 결합하여 비밀번호 생성
    password = clientId + "_" + str(timestamp)
    # bcrypt 해싱을 사용하여 비밀번호 해싱
    hashed = bcrypt.hashpw(password.encode("utf-8"), clientSecret.encode("utf-8"))
    # Base64로 인코딩하여 서명 반환
    return pybase64.standard_b64encode(hashed).decode("utf-8")

def get_access_token(clientId, clientSecret):
    """
    네이버 API에 접근하기 위한 액세스 토큰을 가져옵니다.

    Args:
        clientId (str): 클라이언트 ID
        clientSecret (str): 클라이언트 시크릿

    Returns:
        str: 액세스 토큰
    """
    timestamp = int(time() * 1000)
    
    url = "https://api.commerce.naver.com/external/v1/oauth2/token"
    data = {
        "client_id": clientId,
        "timestamp": timestamp,
        "grant_type": "client_credentials",
        "client_secret_sign": make_signature(clientId, clientSecret),
        "type": "SELF",
    }

    # print(json.dumps(data, indent=4))

    # POST 요청을 통해 액세스 토큰 요청
    response = requests.post(url, data=data)
    # 응답에서 액세스 토큰 추출 및 반환
    return response.json()["access_token"]
