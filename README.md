## BACKEND 레포지스토리 입니다

### 🔍 AWS OpenSearch 검색 기능

프로젝트에 AWS OpenSearch 기반 음악 검색 기능이 추가되었습니다!

#### 환경 변수 설정

`.env` 파일에 다음 환경 변수를 추가하세요:

```bash
# AWS OpenSearch 설정
OPENSEARCH_HOST=your-opensearch-domain.region.es.amazonaws.com
OPENSEARCH_PORT=443
OPENSEARCH_USERNAME=admin
OPENSEARCH_PASSWORD=your-opensearch-password
OPENSEARCH_USE_SSL=True
OPENSEARCH_VERIFY_CERTS=True
OPENSEARCH_INDEX_PREFIX=music
```

#### 패키지 설치

```bash
pip install -r requirements.txt
```

#### 인덱스 생성 및 데이터 동기화

```bash
# 인덱스 리셋 (삭제 → 생성 → 동기화)
python manage.py opensearch_setup --reset

# 또는 개별 실행
python manage.py opensearch_setup --create  # 인덱스 생성
python manage.py opensearch_setup --sync    # 데이터 동기화
python manage.py opensearch_setup --delete  # 인덱스 삭제
```

#### API 사용

```bash
# OpenSearch 검색
curl "http://localhost:8000/api/v1/search/opensearch?q=아이유&sort_by=popularity"

# 인덱스 생성
curl -X POST http://localhost:8000/api/v1/search/opensearch/index

# 데이터 동기화
curl -X POST http://localhost:8000/api/v1/search/opensearch/sync
```

자세한 내용은 [OpenSearch 가이드](./docs/opensearch.md)를 참조하세요.
