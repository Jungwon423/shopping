from flask import Flask
from flask_restx import Api
from flask_cors import CORS
from api.endpoints.products import product_ns  # product_ns를 직접 import

app = Flask(__name__)
CORS(app)  # 모든 도메인에서의 요청을 허용

api = Api(app, 
    title='Your API Title',
    version='1.0',
    description='A description of your API'
)

# product namespace를 api에 추가
api.add_namespace(product_ns, path='/products')

if __name__ == '__main__':
    app.run(debug=True)
