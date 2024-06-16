import http.client

def create_product_payload(product):
    return {
        "originProduct" : {
            "statusType" : "SALE",
            "leafCategoryId" : product["leafCategoryId"],
            "name" : product["name"],
            "detailContent" : product["detailContent"],
        }
    }

def register_product(BEARER_TOKEN, payload):
    conn = http.client.HTTPSConnection("api.commerce.naver.com")
    
    headers = {
    'Authorization': "Bearer " + BEARER_TOKEN,
    'content-type': "application/json"
    }

    conn.request("POST", "/external/v2/products", payload, headers)

    res = conn.getresponse()
    data = res.read()

    print(data.decode("utf-8"))