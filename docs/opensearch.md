# 🔍 AWS OpenSearch 검색 엔진 가이드

AWS OpenSearch를 활용한 고성능 음악 검색 기능을 설명합니다.

## 📋 개요

OpenSearch 검색 시스템은 다음과 같은 특징을 가집니다:

- **전문 검색**: 빠르고 정확한 Full-text Search
- **한글 지원**: 한글 형태소 분석 및 ngram 기반 부분 일치
- **퍼지 매칭**: 오타 허용 검색
- **다양한 정렬**: 관련도, 인기도, 최신순 정렬 지원
- **고성능**: 대용량 데이터에서도 빠른 검색 응답

## 🚀 시작하기

### 1. OpenSearch 설정

`.env` 파일에 다음 환경 변수를 추가하세요:

```bash
# AWS OpenSearch 설정
OPENSEARCH_HOST=your-opensearch-domain.region.es.amazonaws.com
OPENSEARCH_PORT=443
OPENSEARCH_USERNAME=admin
OPENSEARCH_PASSWORD=your-password
OPENSEARCH_USE_SSL=True
OPENSEARCH_VERIFY_CERTS=True
OPENSEARCH_INDEX_PREFIX=music
```

### 2. 패키지 설치

```bash
pip install -r requirements.txt
```

### 3. 인덱스 생성 및 데이터 동기화

#### 방법 1: Django 관리 명령어 사용 (권장)

```bash
# 인덱스 리셋 (삭제 → 생성 → 동기화)
python manage.py opensearch_setup --reset

# 또는 개별 실행
python manage.py opensearch_setup --create  # 인덱스 생성
python manage.py opensearch_setup --sync    # 데이터 동기화
python manage.py opensearch_setup --delete  # 인덱스 삭제
```

#### 방법 2: API 엔드포인트 사용

```bash
# 인덱스 생성
curl -X POST http://localhost:8000/api/v1/search/opensearch/index

# 데이터 동기화
curl -X POST http://localhost:8000/api/v1/search/opensearch/sync

# 인덱스 삭제
curl -X DELETE http://localhost:8000/api/v1/search/opensearch/index
```

## 🔗 API 엔드포인트

### 음악 검색

**`GET /api/v1/search/opensearch`**

OpenSearch를 사용한 음악 검색

#### 쿼리 파라미터

| 파라미터 | 타입 | 필수 | 설명 |
|----------|------|------|------|
| `q` | string | ✅ | 검색어 |
| `sort_by` | string | ❌ | 정렬 기준 (relevance, popularity, recent) |
| `exclude_ai` | boolean | ❌ | AI 생성곡 제외 (기본값: false) |
| `genre` | string | ❌ | 장르 필터 |
| `page` | integer | ❌ | 페이지 번호 (기본값: 1) |
| `page_size` | integer | ❌ | 페이지 크기 (기본값: 20, 최대: 100) |

#### 응답 형식

```json
{
  "count": 100,
  "next": 2,
  "previous": null,
  "results": [
    {
      "itunes_id": 123456789,
      "music_name": "분홍신",
      "artist_name": "아이유",
      "artist_id": 123,
      "album_name": "Palette",
      "album_id": 456,
      "genre": "Pop",
      "duration": 217000,
      "audio_url": null,
      "album_image": null,
      "in_db": true,
      "has_matching_tags": false,
      "_score": 12.5,
      "_highlight": {
        "music_name": ["<em>분홍신</em>"],
        "artist_name": ["<em>아이유</em>"]
      }
    }
  ]
}
```

## 📝 사용 예시

### Python

```python
import requests

# 일반 검색
response = requests.get('http://localhost:8000/api/v1/search/opensearch', params={
    'q': '아이유',
    'page': 1,
    'page_size': 20
})

# 인기도순 정렬
response = requests.get('http://localhost:8000/api/v1/search/opensearch', params={
    'q': '아이유',
    'sort_by': 'popularity'
})

# 장르 필터 + AI 제외
response = requests.get('http://localhost:8000/api/v1/search/opensearch', params={
    'q': '사랑',
    'genre': 'Pop',
    'exclude_ai': True
})
```

### JavaScript

```javascript
// 일반 검색
const response = await fetch('/api/v1/search/opensearch?q=아이유&page=1&page_size=20');
const data = await response.json();

// 인기도순 정렬
const response = await fetch('/api/v1/search/opensearch?q=아이유&sort_by=popularity');
const data = await response.json();

// 장르 필터 + AI 제외
const response = await fetch('/api/v1/search/opensearch?q=사랑&genre=Pop&exclude_ai=true');
const data = await response.json();
```

## 🎯 검색 기능

### 1. 전문 검색 (Full-text Search)

OpenSearch는 다음 필드를 검색합니다:

- **아티스트명** (가중치: 5) - 가장 높은 우선순위 (아티스트 검색 최적화)
- **곡명** (가중치: 3) - 높은 우선순위
- **가사** (가중치: 2) - 중간 우선순위
- **앨범명** (가중치: 0.5) - 낮은 우선순위

### 2. 가사 검색 (Lyrics Search) 🎤

가사 내용으로도 노래를 찾을 수 있습니다:

**예시:**
```bash
# 가사에 "너를 만난 그날부터"가 포함된 곡 검색
GET /api/v1/search/opensearch?q=너를 만난 그날부터

# 가사에 "하늘을 나는"이 포함된 곡 검색
GET /api/v1/search/opensearch?q=하늘을 나는
```

**특징:**
- 가사의 일부분만 기억해도 검색 가능
- 하이라이트 기능으로 매칭된 가사 부분 강조

### 3. Ngram 기반 부분 일치

부분 문자열로도 검색 가능:

- "분홍" → "분홍신" 검색됨
- "아이" → "아이유" 검색됨
- "하늘" → "하늘을 나는 꿈" 가사 검색됨

### 4. 퍼지 매칭 (오타 허용)

1-2글자 오타도 허용:

- "아유" → "아이유" 검색됨
- "분홍시" → "분홍신" 검색됨
- "사랑해요" → "사랑행요" 검색됨

### 5. 정렬 옵션

#### `relevance` (기본값)
검색 관련도 순으로 정렬 (검색어와 가장 관련성 높은 결과 우선)

**가중치 계산:**
- 아티스트명 일치 (5점) > 곡명 일치 (3점) > 가사 일치 (2점) > 앨범명 일치 (0.5점)
- 아티스트 검색 시 더 정확한 결과 제공

#### `popularity`
인기도 순으로 정렬:
1. 재생 수 (내림차순)
2. 좋아요 수 (내림차순)
3. 검색 관련도

#### `recent`
최신순으로 정렬:
1. 생성일 (내림차순)
2. 검색 관련도

## 🔄 데이터 동기화

### 자동 동기화

음악 데이터가 추가/수정/삭제될 때 자동으로 OpenSearch와 동기화하려면 Django Signal을 사용하세요:

```python
# music/signals.py
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Music
from .services.opensearch import opensearch_service

@receiver(post_save, sender=Music)
def index_music_on_save(sender, instance, **kwargs):
    """음악 저장 시 OpenSearch 인덱싱"""
    music_data = {
        'music_id': instance.music_id,
        'itunes_id': instance.itunes_id,
        'music_name': instance.music_name or '',
        'artist_name': instance.artist.artist_name if instance.artist else '',
        'artist_id': instance.artist.artist_id if instance.artist else None,
        'album_name': instance.album.album_name if instance.album else '',
        'album_id': instance.album.album_id if instance.album else None,
        'genre': instance.genre or '',
        'duration': instance.duration or 0,
        'is_ai': getattr(instance, 'is_ai', False),
        'tags': [],  # 태그 추출 로직 추가
        'lyrics': instance.lyrics or '',  # 가사 추가
        'created_at': instance.created_at.isoformat() if instance.created_at else None,
        'play_count': 0,
        'like_count': 0,
    }
    opensearch_service.index_music(music_data)

@receiver(post_delete, sender=Music)
def delete_music_from_index(sender, instance, **kwargs):
    """음악 삭제 시 OpenSearch에서 제거"""
    opensearch_service.delete_music(instance.itunes_id)
```

### 수동 동기화

주기적으로 전체 데이터를 동기화하려면:

```bash
# Cron 작업으로 매일 새벽 4시에 실행
0 4 * * * cd /path/to/project && python manage.py opensearch_setup --sync
```

## 🛠️ 인덱스 구조

OpenSearch 인덱스는 다음과 같은 매핑을 사용합니다:

```json
{
  "settings": {
    "analysis": {
      "analyzer": {
        "korean_analyzer": {
          "type": "custom",
          "tokenizer": "standard",
          "filter": ["lowercase", "trim"]
        },
        "ngram_analyzer": {
          "type": "custom",
          "tokenizer": "standard",
          "filter": ["lowercase", "ngram_filter"]
        }
      },
      "filter": {
        "ngram_filter": {
          "type": "ngram",
          "min_gram": 2,
          "max_gram": 10
        }
      }
    }
  },
  "mappings": {
    "properties": {
      "music_id": {"type": "integer"},
      "itunes_id": {"type": "long"},
      "music_name": {
        "type": "text",
        "analyzer": "korean_analyzer",
        "fields": {
          "ngram": {"type": "text", "analyzer": "ngram_analyzer"},
          "keyword": {"type": "keyword"}
        }
      },
      "artist_name": {
        "type": "text",
        "analyzer": "korean_analyzer",
        "fields": {
          "ngram": {"type": "text", "analyzer": "ngram_analyzer"},
          "keyword": {"type": "keyword"}
        }
      },
      "album_name": {
        "type": "text",
        "analyzer": "korean_analyzer",
        "fields": {
          "ngram": {"type": "text", "analyzer": "ngram_analyzer"}
        }
      },
      "lyrics": {
        "type": "text",
        "analyzer": "korean_analyzer",
        "fields": {
          "ngram": {"type": "text", "analyzer": "ngram_analyzer"}
        }
      },
      "genre": {"type": "keyword"},
      "duration": {"type": "integer"},
      "is_ai": {"type": "boolean"},
      "tags": {"type": "keyword"},
      "created_at": {"type": "date"},
      "play_count": {"type": "integer"},
      "like_count": {"type": "integer"}
    }
  }
}
```

## ⚠️ 주의사항

### 성능 최적화

- **페이지네이션 적극 활용**: 한 번에 너무 많은 결과를 요청하지 마세요 (최대 100개)
- **필터 활용**: 불필요한 검색 범위를 줄이기 위해 `genre`, `exclude_ai` 등의 필터를 사용하세요
- **캐싱**: 동일한 검색어에 대한 결과를 클라이언트 측에서 캐싱하세요

### 보안

- **관리 엔드포인트 보호**: 인덱스 생성/삭제/동기화 API는 관리자만 접근하도록 권한 설정 필요
- **환경 변수 관리**: OpenSearch 인증 정보를 코드에 하드코딩하지 마세요

### 비용 관리

- **AWS OpenSearch 인스턴스 크기**: 데이터 양에 맞는 적절한 인스턴스 선택
- **불필요한 인덱스 삭제**: 테스트용 인덱스는 삭제하여 비용 절감

## 🔍 관련 문서

- [iTunes 검색 API](./search.md) - 기존 iTunes 기반 검색
- [AWS OpenSearch 공식 문서](https://docs.aws.amazon.com/opensearch-service/)
- `music/services/opensearch.py` - OpenSearch 서비스 구현
- `music/views/opensearch_search.py` - OpenSearch 검색 API 구현

## 🆚 iTunes 검색 vs OpenSearch 검색

| 기능 | iTunes 검색 | OpenSearch 검색 |
|------|------------|----------------|
| 데이터 소스 | iTunes API | 자체 DB |
| 검색 속도 | 느림 (외부 API 호출) | 매우 빠름 |
| 오타 허용 | ❌ | ✅ |
| 부분 일치 | 제한적 | ✅ |
| 정렬 옵션 | 제한적 | 다양함 |
| 한글 지원 | 제한적 | 최적화됨 |
| 가사 검색 | ❌ | ✅ |
| 태그 검색 | ✅ | ✅ (예정) |

## 📈 향후 개선 사항

- [x] 가사 검색 (Lyrics Search) ✅
- [ ] 유의어 검색 (아티스트 별명/본명 매칭)
- [ ] 자동완성 (Autocomplete) 기능 추가
- [ ] 태그 기반 검색 통합
- [ ] 검색 로그 분석 및 인기 검색어 추천
- [ ] 재생 수/좋아요 수 실시간 업데이트
- [ ] 검색 결과 개인화 (Personalization)