# 🔍 음악 검색 시스템 가이드

iTunes API를 활용한 음악 검색 기능을 설명합니다.

## 📋 개요

음악 검색 시스템은 다음과 같은 특징을 가집니다:

- **외부 API 연동**: iTunes Search API 활용
- **고급 검색 문법**: 일반 검색어 + 태그 조합 지원
- **자동 DB 저장**: 검색 결과 자동 저장 및 이미지 수집
- **비동기 처리**: 이미지 수집을 백그라운드에서 처리

## 🔗 API 엔드포인트

### 음악 검색
**`GET /api/v1/search`**

iTunes API를 사용한 음악 검색

#### 쿼리 파라미터

| 파라미터 | 타입 | 필수 | 설명 |
|----------|------|------|------|
| `q` | string | ✅ | 검색어 (태그는 `# ` 형식으로 구분) |
| `exclude_ai` | boolean | ❌ | AI 생성곡 제외 (기본값: false) |
| `page` | integer | ❌ | 페이지 번호 (기본값: 1) |
| `page_size` | integer | ❌ | 페이지 크기 (기본값: 20, 최대: 100) |

#### 검색 문법

##### 일반 검색
```
GET /api/v1/search?q=아이유
```

##### 태그 검색
```
GET /api/v1/search?q=# christmas
```
- `#` 뒤에 **공백 필수**
- DB에 저장된 태그로만 검색 가능

##### 복합 검색 (AND 조건)
```
GET /api/v1/search?q=아이유 # christmas
```
- 검색어 + 태그 조합
- iTunes 결과 중 태그 매칭된 곡만 반환

##### 특수 케이스
```
GET /api/v1/search?q=C#
```
- 공백이 없으면 일반 텍스트로 처리
- `#`이 포함된 아티스트/곡명 검색 가능

#### 응답 형식

```json
{
  "count": 20,
  "next": "https://api.example.com/api/v1/search?q=아이유&page=2",
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
      "audio_url": "https://audio-ssl.itunes.apple.com/...",
      "album_image": "https://is3-ssl.mzstatic.com/...",
      "is_ai": false,
      "in_db": true,
      "has_matching_tags": false
    }
  ]
}
```

#### 응답 필드 설명

| 필드 | 타입 | 설명 |
|------|------|------|
| `itunes_id` | integer | iTunes 곡 고유 ID |
| `music_name` | string | 곡명 |
| `artist_name` | string | 아티스트명 |
| `artist_id` | integer | DB 아티스트 ID (없으면 null) |
| `album_name` | string | 앨범명 |
| `album_id` | integer | DB 앨범 ID (없으면 null) |
| `genre` | string | 장르 |
| `duration` | integer | 재생 시간 (밀리초) |
| `audio_url` | string | 30초 미리듣기 URL |
| `album_image` | string | 앨범 커버 이미지 URL |
| `is_ai` | boolean | AI 생성곡 여부 |
| `in_db` | boolean | DB에 저장된 곡인지 여부 |
| `has_matching_tags` | boolean | 태그 검색 시 매칭 여부 |

## 🔄 동작 플로우

### 1. 검색어 파싱
- 일반 검색어와 태그(`# `) 분리
- `# christmas` → 태그: "christmas"
- `아이유 # christmas` → 검색어: "아이유", 태그: "christmas"

### 2. iTunes API 호출
- 일반 검색어가 있으면 iTunes Search API 호출
- 최대 50개 결과까지 검색

### 3. DB 연동
- 아티스트/앨범 자동 생성 또는 조회
- **비동기로 이미지 수집** (Celery 태스크)

### 4. 태그 필터링
- 태그가 있으면 DB에서 해당 태그를 가진 곡과 매칭
- AND 조건으로 필터링

### 5. AI 필터링
- `exclude_ai=true` 시 AI 생성곡 제외

## 🖼️ 이미지 자동 수집

검색 시 다음과 같은 이미지 수집이 자동으로 진행됩니다:

### 아티스트 이미지
- Wikidata → Deezer API 순으로 조회
- S3 업로드 및 리사이징 (원형/사각형)
- 비동기 처리로 검색 응답 지연 없음

### 앨범 이미지
- iTunes에서 제공하는 앨범 커버 사용
- S3 업로드 및 리사이징 (사각형)
- 비동기 처리

## 📝 사용 예시

### Python
```python
import requests

# 일반 검색
response = requests.get('https://api.example.com/api/v1/search', params={
    'q': '아이유',
    'page': 1,
    'page_size': 20
})

# 태그 검색
response = requests.get('https://api.example.com/api/v1/search', params={
    'q': '# christmas'
})

# 복합 검색 + AI 제외
response = requests.get('https://api.example.com/api/v1/search', params={
    'q': '아이유 # christmas',
    'exclude_ai': True
})
```

### JavaScript
```javascript
// 일반 검색
const response = await fetch('/api/v1/search?q=아이유&page=1&page_size=20');
const data = await response.json();

// 태그 검색
const response = await fetch('/api/v1/search?q=# christmas');
const data = await response.json();

// 복합 검색 + AI 제외
const response = await fetch('/api/v1/search?q=아이유 # christmas&exclude_ai=true');
const data = await response.json();
```

## ⚠️ 주의사항

### 검색 문법
- 태그는 반드시 `#` + **공백** 형식 사용
- `#christmas` (공백 없음) → 일반 텍스트로 처리
- `C#`, `I'm #1` → 일반 텍스트로 처리

### 성능 고려사항
- 대량 검색 시 페이지네이션 적극 활용
- AI 필터링은 클라이언트 사이드에서도 가능 (`is_ai` 필드 활용)

### 캐싱 전략
- 동일 검색어에 대한 반복 호출 최소화
- 클라이언트 측 캐싱 고려

## 🔍 관련 문서

- [아티스트 검색 → 곡 클릭 흐름 분석](./FLOW_ARTIST_SEARCH_AND_TRACK_CLICK.md) - 상세한 기술적 분석
- `music/views/search.py` - 검색 API 구현
- `music/services/itunes.py` - iTunes API 서비스