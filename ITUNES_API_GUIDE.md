# iTunes API 통합 가이드

## 개요

iTunes Search API를 활용한 음악 검색 시스템이 구현되었습니다.

## 주요 기능

### 1. 검색 우선순위
- **iTunes API 우선**: 검색 시 iTunes API를 먼저 호출
- **DB 캐싱**: 클릭한 곡은 자동으로 DB에 저장
- **중복 방지**: `itunes_id`로 중복 저장 방지

### 2. 고급 검색 문법

#### 일반 검색
```bash
GET /api/v1/search?q=아이유
```
- iTunes API에서 "아이유" 검색
- 결과: 아티스트명 또는 곡명에 "아이유" 포함된 곡

#### 태그만 검색
```bash
GET /api/v1/search?q=%23christmas
# 또는 URL 인코딩 없이: ?q=#christmas
```
- DB에서 "christmas" 태그를 가진 곡만 조회
- iTunes API 호출 안 함

#### 복합 검색 (검색어 + 태그)
```bash
GET /api/v1/search?q=아이유%23christmas
# 또는: ?q=아이유#christmas
```
- iTunes에서 "아이유" 검색
- 결과 중 DB에 "christmas" 태그가 있는 곡만 필터링

#### AI 필터
```bash
GET /api/v1/search?q=아이유&exclude_ai=true
```
- AI 생성곡 제외 (기성곡만 조회)

### 3. 상세 조회 (자동 저장)

```bash
GET /api/v1/tracks/{itunes_id}
```

**동작:**
1. DB에 있으면 → 200 OK (DB 데이터 반환)
2. DB에 없으면 → iTunes Lookup API 호출 → DB 저장 → 201 Created

**응답 예시:**
```json
{
  "music_id": 8574,
  "music_name": "Never Ending Story",
  "artist": {
    "artist_id": 3711,
    "artist_name": "IU"
  },
  "album": {
    "album_id": 6508,
    "album_name": "A flower bookmark, Pt. 3 - EP"
  },
  "itunes_id": 1815869481,
  "tags": [],
  "is_ai": false
}
```

## API 엔드포인트

### 새로운 엔드포인트

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/api/v1/search` | iTunes 기반 검색 |
| GET | `/api/v1/tracks/{itunes_id}` | iTunes ID로 상세 조회 |

### 기존 엔드포인트 (호환성 유지)

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/api/v1/db/tracks` | DB 직접 조회 (개발자용) |
| GET | `/api/v1/db/tracks/{music_id}` | DB music_id로 조회 |

## 검색 파라미터

### `/api/v1/search`

| 파라미터 | 타입 | 필수 | 설명 | 예시 |
|----------|------|------|------|------|
| `q` | string | ✅ | 검색어 (# 포함 가능) | `아이유`, `#christmas`, `아이유#christmas` |
| `exclude_ai` | boolean | ❌ | AI 생성곡 제외 | `true`, `false` (기본값) |
| `page` | integer | ❌ | 페이지 번호 | `1`, `2`, ... |
| `page_size` | integer | ❌ | 페이지 크기 | `20` (기본값) |

## 검색 문법 상세

### 검색어 파싱 규칙

```python
"아이유"           → term: "아이유",    tags: []
"#christmas"      → term: None,       tags: ["christmas"]
"아이유#christmas" → term: "아이유",    tags: ["christmas"]
"#신나는#밝은"     → term: None,       tags: ["신나는", "밝은"]
"IU#신나는#밝은"   → term: "IU",       tags: ["신나는", "밝은"]
```

### 검색 로직

1. **일반 검색어만 있을 때** (`아이유`)
   - iTunes API 호출
   - 모든 결과 반환

2. **태그만 있을 때** (`#christmas`)
   - iTunes API 호출 안 함
   - DB에서 태그 매칭된 곡만 조회

3. **검색어 + 태그** (`아이유#christmas`)
   - iTunes API 호출 (검색어로)
   - DB 태그와 교집합 (AND 로직)
   - 매칭된 곡만 반환

## 테스트

### 자동 테스트 실행
```bash
docker-compose exec web python test_itunes_api.py
```

### 수동 테스트 예시

#### 1. 일반 검색
```bash
curl "http://localhost:8000/api/v1/search?q=아이유"
```

#### 2. 태그 검색
```bash
curl "http://localhost:8000/api/v1/search?q=%23christmas"
```

#### 3. 복합 검색
```bash
curl "http://localhost:8000/api/v1/search?q=아이유%23christmas"
```

#### 4. 상세 조회 (자동 저장)
```bash
# 첫 조회 시 201 Created
curl "http://localhost:8000/api/v1/tracks/1815869481"

# 재조회 시 200 OK (DB 캐시)
curl "http://localhost:8000/api/v1/tracks/1815869481"
```

## Swagger UI

API 문서 및 테스트:
```
http://localhost:8000/api/docs/
```

## 주의사항

1. **iTunes API Rate Limit**
   - 분당 20회 권장
   - 타임아웃: 3초

2. **중복 방지**
   - `itunes_id` 기반 중복 체크
   - 이미 저장된 곡은 재저장 안 함

3. **태그 정보**
   - iTunes 곡은 처음 저장 시 태그 없음
   - 수동으로 태그 추가 필요

4. **Artist/Album 중복**
   - `get_or_create`로 중복 생성 방지
   - 이름 기준 매칭

## 파일 구조

```
Backend/
├── music/
│   ├── services.py          # iTunes API 서비스
│   ├── views.py             # MusicSearchView, MusicDetailView
│   ├── serializers.py       # iTunesSearchResultSerializer
│   └── urls.py              # URL 라우팅
├── test_itunes_api.py       # 통합 테스트 스크립트
└── ITUNES_API_GUIDE.md      # 이 문서
```

## 향후 개선 사항

- [ ] iTunes API 응답 캐싱 (Redis)
- [ ] 태그 자동 생성 (AI 기반)
- [ ] 검색 결과 정렬 옵션
- [ ] 인기도/조회수 기반 랭킹
- [ ] 가사 자동 수집 (LRCLIB API)
