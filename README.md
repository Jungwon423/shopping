# 가상환경 생성
python3.10 -m venv venv

# 가상환경 실행방법
venv\Scripts\activate (Windows)
source venv/bin/activate (macOS)

(파이썬 버전 3.10.10)
--> chromaDB 쓰려면 3.10 이하 버전 써야 함

# 라이브러리 텍스트에 저장

pip freeze > requirements.txt

# 라이브러리 설치

pip install -r requirements.txt

# shopping

프로젝트 구조

shopping/
├── app.py
├── requirements.txt
├── venv/
└── api/
├── stt.py
├── gmail_module.py
├── calendar_module.py
└── llm_controller.py

# Application Workflow

1. 상품 소싱

- 타오바오 (✅)
- 티몰 ()
- 1688 ()
- 알리 ()
- 라쿠텐 ()
- 테무 ()
- VVIC ()
- 아마존 일본 ()
- 아마존 독일 ()
- 아마존 미국 ()
- 아마존 영국 ()
- 아마존 프랑스 ()
- 아마존 스페인 ()
- 아마존 이탈리아 ()
- 아마존 캐나다 ()
- 아마존 멕시코 ()
- 아마존 인도 ()

==> 상품 URL의 List 반환 ✅

2. (상품 URL이 주어졌을 때)

1) URL에 접속하여 상품 정보 Crawling

- 상품 정보 (상품명) ✅
- 상품 이미지 및 동영상
- 옵션 ✅
- 판매가 ✅
- 상품 속성 ✅
- 상세페이지의 이미지 저장 ✅

2. Crawling한 상품 정보 처리

- 상품 정보 (상품명 -> 상품 카테고리 & 상품 태그) ✅
- 상품 이미지 및 동영상 (원본 -> 마켓별 권장 크기로 리사이징) ✅
- 옵션 (원본 -> 마켓 지침에 맞게 수정) ✅
- 판매가 (원본 -> 환율 계산하여 계산) ✅
- 상품 속성 (원본 -> 마켓 지침에 맞게 수정) ✅
- 상세페이지 (외국어 번역)

3. 상품 업로드

- 스마트스토어 (✅)
- 쿠팡 (✅)
- 11번가 글로벌 ()
- 11번가 국내 ()
- ESM 2.0 (옥션, 지마켓) ()
- 옥션 1.0 (❌)
- 롯데온 ()
- 인터파크 ()
- 위메프 ()
