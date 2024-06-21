from openai import OpenAI
from dotenv import load_dotenv
import os
import json
import chromadb
import chromadb.utils.embedding_functions as embedding_functions
import re

# .env 파일을 로드합니다.
load_dotenv(override=True)

# OpenAI API 키 설정
openai_api_key = os.getenv('OPENAI_API_KEY')

def translate_with_gpt3(text):
    """
    주어진 중국어 텍스트를 GPT-3를 사용하여 한국어로 번역합니다.
    
    Args:
        text (str): 번역할 중국어 텍스트.
        
    Returns:
        str: 번역된 한국어 텍스트.
    """
    client = OpenAI(api_key=openai_api_key)
    
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are in charge of translating Chinese to Korean for a company that sources products from Taobao and sells them on a Korean e-commerce platform. Given the Chinese keywords you need to translate, translate them into Korean in the following JSON format. {“translated_text”: “Your translation into Korean}"},
            {"role": "user", "content": text}
        ],
        temperature=0
    )
    
    # 응답에서 JSON 형식의 문자열 추출
    response_text = re.search(r'\{.*?\}', response.choices[0].message.content, re.DOTALL).group(0)
    
    # JSON 형식의 문자열을 파싱
    response_json = json.loads(response_text)
    
    translated_text = response_json["translated_text"]
    print(f'번역 결과: {translated_text}')
    
    return translated_text

def refine_product_name(product_name):
    """
    주어진 한국어 상품명을 정제하여 본질적인 이름으로 변환합니다.
    
    Args:
        product_name (str): 정제할 한국어 상품명.
        
    Returns:
        str: 정제된 한국어 상품명.
    """
    client = OpenAI(api_key=openai_api_key)
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": '''You're in charge of finding categories for products in an e-commerce company, but the product names you've been given have modifiers that don't really describe the product, making it difficult to determine what the product is. You need to remove the modifiers from the product names and refine them into names that describe the essence of the product.
            Given the Korean name of the product, refine the name in the following JSON format. {“refined_product_name”: “product name that you've refined in korean”}
            Following is an example.
            Product name: Baseus 2024 스포츠를 위한 새로운 진정한 무선 블루투스 이어폰, 고품질 외관, 소음 감소, 게임, e-스포츠
            Refined product name: 무선 블루투스 이어폰
            
            '''},
            {"role": "user", "content": product_name}
        ]
    )
    
    # 응답에서 JSON 형식의 문자열 추출
    response_text = re.search(r'\{.*?\}', response.choices[0].message.content, re.DOTALL).group(0)
    print(f'상품명 정제 결과 (JSON): {response_text}')
    
    # JSON 형식의 문자열을 파싱
    response_json = json.loads(response_text)
    
    refined_text = response_json["refined_product_name"]
    print(f'정제 결과: {refined_text}')
    
    return refined_text

def find_nearest_categories(product_name, collection):
    """
    주어진 상품명과 가장 가까운 15개의 카테고리를 검색합니다.
    
    Args:
        product_name (str): 검색할 상품명.
        collection (chromadb.Collection): 검색할 카테고리 컬렉션.
        
    Returns:
        list: 가장 가까운 15개의 카테고리 문서.
    """
    results = collection.query(
        query_texts=product_name,
        n_results=5000
    )
    
    find_str = "안마의자"
    find_idx = -1
    
    # 하나씩 출력
    print(f"The nearest categories for '{product_name}' are:")
    for idx, category in enumerate(results['metadatas'][0][:]):
        if idx < 10:
            print(f"- {category['name']}")
        if find_str in category['name']:
            find_idx = idx
            break
        
    print(f"find_idx: {find_idx}")
    
    # 가장 가까운 15개의 문서를 반환
    return results['metadatas'][0][:15] if results['metadatas'] else []

def select_category_with_gpt4o(product_name, nearest_categories):
    """
    주어진 상품명과 후보 카테고리를 이용하여 GPT-4o로 가장 적합한 카테고리를 선택합니다.
    
    Args:
        product_name (str): 상품명.
        nearest_categories (list): 후보 카테고리 목록.
        
    Returns:
        dict: 선택된 카테고리와 그 ID를 포함한 딕셔너리.
    """
    
    guide = "You're an ecommerce business whose job is to determine which product category a product belongs to when given a product name. Given a product name and a set of candidate category names, you need to find the most accurate category that product name belongs to."
    prompt = "Given the product name and the following candidate categories, determine which category the product belongs to.\n\nProduct name: " + product_name + "\n\nCandidate categories:\n" + "\n".join([category["name"] for category in nearest_categories]) + "\n\nWhich category does the product belong to? Respond in the following JSON format:\n\n{\n  \"category\": \"Category name\"\n}\n"
    
    client = OpenAI(api_key=openai_api_key)
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": guide},
            {"role": "user", "content": prompt},
        ]
    )
    
    print(response.choices[0].message.content)
    response_text = response.choices[0].message.content
    start_idx = response_text.find("{")
    response_text = response_text[start_idx:]
    end_idx = response_text.find("}")
    response_text = response_text[:end_idx+1]
    
    print(f"response_text: {response_text}")
    # JSON 형식의 문자열 파싱
    response_json = json.loads(response_text)
    
    category_text = response_json["category"]
    print(f'카테고리: {category_text}')
    
    category_id = None
    for category in nearest_categories:
        if category["name"] == category_text:
            category_id = category["category_id"]
    
    return {
        "category_text" : category_text,
        "category_id" : category_id
    }

def create_leaf_category(name):
    """
    주어진 상품명을 이용하여 최종 카테고리를 생성합니다.
    
    1. 중국어 상품명을 한국어로 번역합니다.
    2. 한국어 상품명을 정제합니다.
    3. 정제된 상품명을 이용하여 가장 가까운 카테고리들을 검색합니다.
    4. GPT-4o를 이용하여 최종 카테고리를 선택합니다.
    
    Args:
        name (str): 상품명.
        
    Returns:
        dict: 번역된 상품명, 정제된 상품명, 선택된 카테고리 정보를 포함한 딕셔너리.
    """
    # 중국어 name -> 한국어 name
    translated_name = translate_with_gpt3(name)
    
    # 한국어 name을 정제
    refined_name = refine_product_name(translated_name)
    
    # 한국어 name으로 embedding해서 검색
    openai_ef = embedding_functions.OpenAIEmbeddingFunction(
                api_key=openai_api_key,
            )

    client = chromadb.PersistentClient(path='chromadb_last_two_words')
    collection_name = 'categories'

    collection = client.get_or_create_collection(name=collection_name, embedding_function=openai_ef)
    
    nearest_categories = find_nearest_categories(refined_name, collection)
    
    # GPT-4o가 카테고리 선택
    selected_category = select_category_with_gpt4o(translated_name, nearest_categories) 
    
    return {
        "name": translated_name,
        "refined_name": refined_name,
        "leaf_category": selected_category["category_id"],
        "leaf_category_text" : selected_category["category_text"],
    }
