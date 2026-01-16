# 공식 Python 슬림 이미지를 기반으로 사용
FROM python:3.11-slim-bookworm

# 작업 디렉토리 설정
WORKDIR /usr/src/app

# 환경 변수 설정
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# PostgreSQL 클라이언트 설치 (psql)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    postgresql-client && \
    rm -rf /var/lib/apt/lists/*

# 의존성 설치
RUN pip install --upgrade pip
COPY ./requirements.txt .
RUN pip install -r requirements.txt

# 프로젝트 파일 복사
COPY . .