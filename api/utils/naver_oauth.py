from time import time
import bcrypt
import pybase64
import json
import requests

def make_signature(clientId, clientSecret):
    
    timestamp = int(time() * 1000)
    
    password = clientId + "_" + str(timestamp)
    hashed = bcrypt.hashpw(password.encode("utf-8"), clientSecret.encode("utf-8"))
    return pybase64.standard_b64encode(hashed).decode("utf-8")

def get_access_token(clientId, clientSecret):
    
    timestamp = int(time() * 1000)
    
    url = "https://api.commerce.naver.com/external/v1/oauth2/token"
    data = {
        "client_id": clientId,
        "timestamp": timestamp,
        "grant_type": "client_credentials",
        "client_secret_sign": make_signature(clientId, clientSecret),
        "type": "SELF",
    }

    print(json.dumps(data, indent=4))

    response = requests.post(url, data=data)
    return response.json()["access_token"]