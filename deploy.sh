#!/bin/bash

# 이 스크립트는 EC2 인스턴스와 같은 리눅스 환경에서 실행된다고 가정합니다.

# 프로젝트 디렉토리로 이동합니다.
cd /path/to/your/project

# 가상 환경이 이미 존재하는지 확인하고, 없다면 생성합니다.
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

# 가상 환경을 활성화합니다.
source venv/bin/activate

# 필요한 패키지를 설치합니다.
pip install -r requirements.txt

# Gunicorn을 사용하여 애플리케이션을 실행합니다.
# 이미 실행 중인 Gunicorn 프로세스가 있는 경우, 해당 프로세스를 종료합니다.
if pgrep gunicorn; then
    pkill gunicorn
fi

# Gunicorn을 백그라운드에서 실행합니다.
gunicorn --bind 0.0.0.0:5000 app:app --daemon

echo "Deployment completed successfully!"
