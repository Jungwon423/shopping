from dotenv import load_dotenv
from openai import OpenAI
import os
import re
import json

# .env 파일을 로드합니다.
load_dotenv(override=True)

# OpenAI API 키 설정
openai_api_key = os.getenv('OPENAI_API_KEY')

def create_seller_tag(product_name):
    client = OpenAI(api_key=openai_api_key)
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system", 
                "content": "You run an overseas fulfillment business that sources products from overseas e-commerce sites like Taobao and sells them back to Korean e-commerce sites. Your task is to take a given product name and think of 20 keywords that people in Korea might be searching for. Given the product name you need to generate keywords for, give me the keywords in the following JSON format. {{\"keywords\": \"List of keywords\"}}"
            },
            {
                "role": "user", 
                "content": product_name
            }
        ]
    )
    
    # 응답에서 JSON 형식의 문자열 추출
    response_text = re.search(r'\{.*?\}', response.choices[0].message.content, re.DOTALL).group(0)
    print(f'번역 결과 (JSON): {response_text}')
    
    # JSON 형식의 문자열을 파싱
    response_json = json.loads(response_text)
    
    generated_keywords = response_json["keywords"]
    print(f'생성된 키워드: {generated_keywords}')
    
    return [{"text": text} for text in generated_keywords][:10]