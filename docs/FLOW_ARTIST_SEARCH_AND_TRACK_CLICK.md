# 아티스트 검색 → 곡 클릭 흐름 분석

## 전체 흐름 개요

```
1. 사용자 검색: "아이유" 검색
   ↓
2. 검색 API: GET /api/v1/search?q=아이유
   - iTunes Search API 호출
   - 아티스트가 DB에 없으면 생성
   - fetch_artist_image_task 호출 (비동기)
   - 검색 결과 반환 (artist_id 포함)
   ↓
3. 사용자 곡 클릭: 검색 결과에서 곡 선택
   ↓
4. 곡 상세 조회: GET /api/v1/tracks/{itunes_id}
   - DB에 곡이 없으면 iTunes Lookup API 호출
   - save_itunes_track_to_db_task 호출 (비동기)
   - Artist, Album, Music 생성
```

---

## 단계별 상세 분석

### 1단계: 검색 API (`GET /api/v1/search?q=아이유`)

**파일**: `music/views/search.py`

**동작 순서**:
1. iTunes Search API 호출
2. 검색 결과 파싱
3. 아티스트 이름 수집 및 중복 제거
4. **DB에 있는 아티스트 조회**
5. **DB에 없는 아티스트 생성**:
   ```python
   artist, artist_created = Artists.objects.get_or_create(
       artist_name=artist_name,
       defaults={
           'artist_image': '',  # 비동기로 수집
           'created_at': timezone.now(),
           'is_deleted': False,
       }
   )
   ```
6. **아티스트 이미지 태스크 호출** (새로 생성된 경우):
   ```python
   if artist_created or not artist.artist_image:
       fetch_artist_image_task.delay(artist.artist_id, artist_name)
   ```
7. 앨범도 동일하게 생성 및 이미지 태스크 호출
8. 검색 결과 반환 (artist_id, album_id 포함)

**✅ 정상 동작**: 아티스트 생성 + 이미지 태스크 호출

---

### 2단계: 곡 상세 조회 API (`GET /api/v1/tracks/{itunes_id}`)

**파일**: `music/views/music.py`

**동작 순서**:
1. DB에서 곡 조회 시도
2. **DB에 없으면**:
   - iTunes Lookup API 호출
   - 데이터 파싱
   - `save_itunes_track_to_db_task.delay(parsed_data)` 호출
   - 즉시 응답 반환 (202 Accepted)

**✅ 정상 동작**: 비동기 태스크 호출

---

### 3단계: 곡 저장 태스크 (`save_itunes_track_to_db_task`)

**파일**: `music/tasks.py`

**동작 순서**:
1. 중복 확인 (이미 DB에 있으면 스킵)
2. **아티스트 생성 또는 조회**:
   ```python
   artist, created = Artists.objects.get_or_create(
       artist_name=artist_name,
       defaults={
           'artist_image': itunes_data.get('artist_image', ''),  # ⚠️ 문제점!
           'created_at': now,
           'is_deleted': False,
       }
   )
   ```
3. **앨범 생성 또는 조회**:
   ```python
   album, created = Albums.objects.get_or_create(
       album_name=album_name,
       artist=artist,
       defaults={
           'album_image': '',  # ⚠️ 문제점!
           'created_at': now,
           'is_deleted': False,
       }
   )
   ```
4. Music 생성

**✅ 수정 완료**:
1. 아티스트 생성 시 `artist_image`를 빈 값으로 저장하고, **이미지 태스크 호출 추가됨**
2. 앨범 생성 시 `album_image`를 빈 값으로 저장하고, **이미지 태스크 호출됨** (이미 구현되어 있음)
3. 검색과 곡 클릭 모두 동일하게 이미지 태스크 호출

---

## ✅ 수정 완료 사항

### 수정 1: 아티스트 이미지 태스크 호출 추가
- **위치**: `save_itunes_track_to_db_task`
- **수정**: 아티스트 생성 시 `fetch_artist_image_task` 호출 추가
- **결과**: S3 업로드 및 리사이징 자동 처리

### 수정 2: 앨범 이미지 태스크 호출 확인
- **위치**: `save_itunes_track_to_db_task`
- **상태**: 이미 구현되어 있음
- **결과**: 앨범 이미지도 S3 업로드 및 리사이징 자동 처리

### 수정 3: 아티스트 이미지 URL 일관성 확보
- **검색 시**: 빈 값으로 저장 → 이미지 태스크 → S3 URL 저장
- **곡 클릭 시**: 빈 값으로 저장 → 이미지 태스크 → S3 URL 저장
- **결과**: 동일한 방식으로 처리되어 일관성 유지

---

## ✅ 최종 흐름 (수정 완료)

```
1. 검색: GET /api/v1/search?q=아이유
   ├─ iTunes Search API 호출
   ├─ 아티스트 생성 (artist_image: '')
   ├─ fetch_artist_image_task.delay() 호출
   │  └─ Wikidata/Deezer에서 이미지 조회
   │  └─ S3 업로드 (media/images/artists/original/)
   │  └─ Lambda 자동 리사이징 (원형 228x228, 208x208 / 사각형 220x220)
   │  └─ DB 업데이트 (원본 + 리사이징 URL)
   ├─ 앨범 생성 (album_image: '')
   ├─ fetch_album_image_task.delay() 호출
   │  └─ S3 업로드 (media/images/albums/original/)
   │  └─ Lambda 자동 리사이징 (사각형 220x220)
   │  └─ DB 업데이트 (원본 + 리사이징 URL)
   └─ 검색 결과 반환 (artist_id, album_id 포함)

2. 곡 클릭: GET /api/v1/tracks/{itunes_id}
   ├─ DB에서 곡 조회 시도
   ├─ DB에 없으면:
   │  ├─ iTunes Lookup API 호출
   │  ├─ save_itunes_track_to_db_task.delay() 호출
   │  │  ├─ 아티스트 조회/생성
   │  │  │  └─ 없으면 생성 (artist_image: '')
   │  │  │  └─ fetch_artist_image_task.delay() 호출
   │  │  ├─ 앨범 조회/생성
   │  │  │  └─ 없으면 생성 (album_image: '')
   │  │  │  └─ fetch_album_image_task.delay() 호출
   │  │  └─ Music 생성
   │  └─ 즉시 응답 반환 (202 Accepted)
   └─ DB에 있으면: 바로 반환 (200 OK)
```

## ✅ 검증 포인트

### 1. 아티스트 이미지 일관성
- ✅ 검색 시: 빈 값 → 이미지 태스크 → S3 URL
- ✅ 곡 클릭 시: 빈 값 → 이미지 태스크 → S3 URL
- ✅ 동일한 방식으로 처리되어 일관성 유지

### 2. 앨범 이미지 처리
- ✅ 검색 시: 빈 값 → 이미지 태스크 → S3 URL
- ✅ 곡 클릭 시: 빈 값 → 이미지 태스크 → S3 URL
- ✅ 동일한 방식으로 처리되어 일관성 유지

### 3. 비동기 처리
- ✅ 모든 이미지 수집은 비동기로 처리
- ✅ API 응답 시간 최적화
- ✅ Lambda가 자동으로 리사이징 처리

## 📝 API 호출 순서 요약

1. **검색 API**:
   - iTunes Search API
   - fetch_artist_image_task (비동기)
   - fetch_album_image_task (비동기)

2. **곡 상세 조회 API**:
   - iTunes Lookup API
   - save_itunes_track_to_db_task (비동기)
     - fetch_artist_image_task (비동기, 필요시)
     - fetch_album_image_task (비동기, 필요시)

모든 이미지 처리는 비동기로 진행되므로 API 응답은 빠르게 반환됩니다.

---

## 🧪 실제 테스트 결과 (2026-01-17)

### 테스트 시나리오: DB에 없는 아티스트 "boy pablo" 검색

#### 1단계: 검색 (`GET /api/v1/search?q=boy pablo`)
- ✅ iTunes Search API 호출 성공
- ✅ 아티스트 생성 (artist_id: 3729)
- ✅ 앨범 생성 (album_id: 6528, 6529, 6530, ...)
- ✅ `fetch_artist_image_task` 호출 (비동기)
- ✅ `fetch_album_image_task` 호출 (비동기)

#### 2단계: 아티스트 이미지 수집 (비동기)
- ✅ Wikidata에서 이미지 URL 조회
- ✅ S3 업로드 (User-Agent 헤더 추가로 403 에러 해결)
- ✅ DB 저장:
  - `artist_image`: S3 원본 URL
  - `image_large_circle`: S3 228x228 URL
  - `image_small_circle`: S3 208x208 URL
  - `image_square`: S3 220x220 URL

#### 3단계: 곡 클릭 (`GET /api/v1/tracks/1234864149`)
- ✅ iTunes Lookup API 호출 성공
- ✅ `save_itunes_track_to_db_task` 호출 (비동기)
- ✅ Music 생성 (music_id: 8583)
- ✅ 기존 아티스트 재사용 (artist_id: 3729)
- ✅ 기존 앨범 재사용 (album_id: 6528)

### 발견된 문제 및 해결
1. **Wikipedia 403 Forbidden 에러**
   - **원인**: User-Agent 헤더 없이 Wikipedia 이미지 다운로드 시도
   - **해결**: `music/utils/s3_upload.py`에 User-Agent 헤더 추가

### 최종 DB 상태
```
Artist: boy pablo (ID: 3729)
  - artist_image: S3 URL ✅
  - image_large_circle: S3 URL ✅
  - image_small_circle: S3 URL ✅
  - image_square: S3 URL ✅

Album: Roy Pablo - EP (ID: 6528)
  - album_image: S3 URL ✅
  - image_square: S3 URL ✅

Music: Everytime (ID: 8583)
  - itunes_id: 1234864149 ✅
  - artist: boy pablo ✅
  - album: Roy Pablo - EP ✅
```