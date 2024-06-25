from flask import request
from flask_restx import Namespace, Resource, fields
from bson import ObjectId
from datetime import datetime
from api.services.product.get_producit_info import format_product_data
from api.services.product.upload import (
    extract_product_info,
    process_product_info,
    create_product_payload,
    save_payload_to_db,
    send_product_info_request
)

# MongoDB 연결 (실제 구현에서는 별도의 모듈로 분리하는 것이 좋습니다)
from pymongo import MongoClient
client = MongoClient('mongodb://localhost:27017/')
db = client['SmartStore']
raw_product_collection = db['products_raw_data']
processed_product_collection = db['products_processed_data']

# Namespace 생성
product_ns = Namespace('products', description='상품 관련 작업')

# API 모델 정의
product_model = product_ns.model('Product', {
    'product_info': fields.Raw(required=True, description='상품 정보'),
    'product_detail': fields.Raw(required=True, description='상품 상세페이지'),
    'url': fields.String(required=True, description='상품 URL'),
    'keyword': fields.String(description='검색 키워드'),
})

@product_ns.route('/process')
class ProcessProduct(Resource):
    @product_ns.expect(product_model)
    @product_ns.doc(description='상품 처리 요청')
    def post(self):
        data = request.json
        product = {
            'product_info': data['product_info'],
            'product_detail': data['product_detail'],
            'url': data['url'],
            'keyword': data.get('keyword'),
            # 추가 필드
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        }
        result = raw_product_collection.insert_one(product)
        # 여기에 비동기 처리 로직 추가 (예: Celery 태스크 호출)
        product_info = extract_product_info(id=str(result.inserted_id))
        processed_product_info = process_product_info(product_info)
        product_payload = create_product_payload(processed_product_info)
        # 페이로드를 MongoDB에 저장
        save_payload_to_db(product_payload)
        
        return {'message': '처리가 시작되었습니다', 'product_id': str(result.inserted_id)}, 202

@product_ns.route('/<string:product_id>')
class Product(Resource):
    @product_ns.doc(description='상품 정보 조회')
    def get(self, product_id):
        product = processed_product_collection.find_one({'_id': ObjectId(product_id)}, {'_id': 0})
        if product:
            formatted_product = format_product_data([product])[0]
            return {'product': formatted_product}, 200
        return {'message': '상품을 찾을 수 없습니다'}, 404

@product_ns.route('/update/<string:product_id>')
class UpdateProduct(Resource):
    @product_ns.expect(product_model)
    @product_ns.doc(description='처리된 상품 정보 업데이트')
    def put(self, product_id):
        data = request.json
        result = raw_product_collection.update_one(
            {'_id': ObjectId(product_id)},
            {'$set': {
                'data': data['data'],
                'updated_at': datetime.utcnow()
            }}
        )
        if result.modified_count:
            return {'message': '상품이 성공적으로 업데이트되었습니다'}, 200
        return {'message': '상품을 찾을 수 없습니다'}, 404

@product_ns.route('/upload/<string:product_id>')
class UploadProduct(Resource):
    @product_ns.doc(description='상품 업로드 요청')
    def post(self, product_id):
        result = raw_product_collection.update_one(
            {'_id': ObjectId(product_id)},
            {'$set': {
                'status': 'uploading',
                'updated_at': datetime.utcnow()
            }}
        )
        if result.modified_count:
            # 여기에 실제 업로드 로직 추가 (예: Celery 태스크 호출)
            return {'message': '업로드 프로세스가 시작되었습니다'}, 202
        return {'message': '상품을 찾을 수 없습니다'}, 404

@product_ns.route('/processed')
class ProcessedProducts(Resource):
    @product_ns.doc(description='처리된 상품 목록 조회')
    def get(self):
        # 페이지네이션 파라미터
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))
        
        skip = (page - 1) * per_page
        products = list(processed_product_collection.find(
            # {'status': 'processed'},
            # {'_id': 0}  # _id 필드 제외
        ).skip(skip).limit(per_page))
        
        formatted_products = format_product_data(products)
        
        return {'products': formatted_products, 'page': page, 'per_page': per_page}, 200

@product_ns.route('/uploaded')
class UploadedProducts(Resource):
    @product_ns.doc(description='업로드된 상품 목록 조회')
    def get(self):
        # 페이지네이션 파라미터
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))
        
        skip = (page - 1) * per_page
        products = list(processed_product_collection.find(
            {'status': 'uploaded'},
            {'_id': 0}  # _id 필드 제외
        ).skip(skip).limit(per_page))
        
        return {'products': products, 'page': page, 'per_page': per_page}, 200