# 📋 플레이리스트 관리 가이드

사용자 플레이리스트 생성, 관리 및 공유 기능을 설명합니다.

## 📋 개요

플레이리스트 시스템은 다음과 같은 특징을 가집니다:

- **사용자별 관리**: 각 사용자의 개인 플레이리스트
- **공개/비공개 설정**: 다른 사용자와 공유 가능
- **곡 순서 관리**: 플레이리스트 내 곡 순서 조정
- **좋아요 기능**: 다른 사용자의 플레이리스트에 좋아요 표시

## 🔗 API 엔드포인트

### 1. 플레이리스트 목록 조회 및 생성

#### 목록 조회
**`GET /api/v1/playlists`**

플레이리스트 목록을 조회합니다. (자신의 플레이리스트 + 공개 플레이리스트)

##### 쿼리 파라미터

| 파라미터 | 타입 | 필수 | 설명 |
|----------|------|------|------|
| `visibility` | string | ❌ | `public`/`private` 필터링 |
| `user_id` | integer | ❌ | 특정 사용자의 플레이리스트만 조회 |

##### 응답 예시
```json
[
  {
    "playlist_id": 1,
    "title": "출근길 플레이리스트",
    "user_id": 123,
    "visibility": "public",
    "created_at": "2024-01-15T09:00:00Z",
    "music_count": 15,
    "like_count": 5
  }
]
```

#### 플레이리스트 생성
**`POST /api/v1/playlists`**

새로운 플레이리스트를 생성합니다.

##### 요청 본문
```json
{
  "title": "출근길 플레이리스트",
  "visibility": "public"
}
```

##### 응답 예시
```json
{
  "playlist_id": 1,
  "title": "출근길 플레이리스트",
  "user_id": 123,
  "visibility": "public",
  "created_at": "2024-01-15T09:00:00Z",
  "updated_at": "2024-01-15T09:00:00Z",
  "music_count": 0,
  "like_count": 0,
  "musics": []
}
```

### 2. 플레이리스트 상세 관리

#### 상세 조회
**`GET /api/v1/playlists/{playlistId}`**

플레이리스트 상세 정보와 포함된 곡 목록을 조회합니다.

##### 응답 예시
```json
{
  "playlist_id": 1,
  "title": "출근길 플레이리스트",
  "user_id": 123,
  "visibility": "public",
  "created_at": "2024-01-15T09:00:00Z",
  "updated_at": "2024-01-15T09:00:00Z",
  "music_count": 2,
  "like_count": 5,
  "musics": [
    {
      "item_id": 10,
      "music_id": 456,
      "music_name": "분홍신",
      "artist_name": "아이유",
      "album_image": "https://...",
      "order": 1,
      "added_at": "2024-01-15T09:05:00Z"
    },
    {
      "item_id": 11,
      "music_id": 789,
      "music_name": "좋은날",
      "artist_name": "아이유",
      "album_image": "https://...",
      "order": 2,
      "added_at": "2024-01-15T09:10:00Z"
    }
  ]
}
```

#### 정보 수정
**`PATCH /api/v1/playlists/{playlistId}`**

플레이리스트 제목과 공개 설정을 수정합니다.

##### 요청 본문
```json
{
  "title": "새로운 플레이리스트 제목",
  "visibility": "private"
}
```

#### 삭제
**`DELETE /api/v1/playlists/{playlistId}`**

플레이리스트를 삭제합니다. (소프트 삭제)

### 3. 곡 관리

#### 곡 추가
**`POST /api/v1/playlists/{playlistId}/items`**

플레이리스트에 곡을 추가합니다.

##### 요청 본문
```json
{
  "music_id": 456,
  "order": 1
}
```

##### 파라미터 설명
- `music_id`: 추가할 음악의 ID
- `order`: 곡 순서 (생략 시 마지막 순서로 추가)

#### 곡 삭제
**`DELETE /api/v1/playlists/items/{itemId}`**

플레이리스트에서 특정 곡을 제거합니다.

### 4. 좋아요 기능

#### 좋아요 등록
**`POST /api/v1/playlists/{playlistId}/likes`**

다른 사용자의 플레이리스트에 좋아요를 표시합니다.

#### 좋아요 취소
**`DELETE /api/v1/playlists/{playlistId}/likes`**

플레이리스트 좋아요를 취소합니다.

## 🔐 권한 및 접근 제어

### 플레이리스트 조회 권한
- **공개 플레이리스트**: 모든 사용자 접근 가능
- **비공개 플레이리스트**: 소유자만 접근 가능

### 수정/삭제 권한
- 플레이리스트 소유자만 수정/삭제 가능

### 좋아요 권한
- 자신의 플레이리스트에는 좋아요 불가능
- 다른 사용자의 공개 플레이리스트에만 좋아요 가능

## 📊 데이터 구조

### Playlist 모델
```json
{
  "playlist_id": "integer (PK)",
  "user_id": "integer (FK)",
  "title": "string (필수)",
  "visibility": "public|private",
  "created_at": "datetime",
  "updated_at": "datetime",
  "is_deleted": "boolean"
}
```

### PlaylistItem 모델 (곡 연결)
```json
{
  "item_id": "integer (PK)",
  "playlist_id": "integer (FK)",
  "music_id": "integer (FK)",
  "order": "integer (순서)",
  "created_at": "datetime",
  "updated_at": "datetime",
  "is_deleted": "boolean"
}
```

### PlaylistLike 모델 (좋아요)
```json
{
  "like_id": "integer (PK)",
  "user_id": "integer (FK)",
  "playlist_id": "integer (FK)",
  "created_at": "datetime"
}
```

## 📝 사용 예시

### 플레이리스트 생성 및 곡 추가

```python
import requests

# 헤더 설정 (JWT 토큰 필요)
headers = {
    'Authorization': 'Bearer your_jwt_token',
    'Content-Type': 'application/json'
}

# 1. 플레이리스트 생성
playlist_data = {
    'title': '출근길 플레이리스트',
    'visibility': 'public'
}

response = requests.post(
    'https://api.example.com/api/v1/playlists',
    json=playlist_data,
    headers=headers
)

playlist = response.json()
playlist_id = playlist['playlist_id']

# 2. 곡 추가
music_data = {
    'music_id': 456,
    'order': 1
}

response = requests.post(
    f'https://api.example.com/api/v1/playlists/{playlist_id}/items',
    json=music_data,
    headers=headers
)
```

### JavaScript 예시

```javascript
// 플레이리스트 생성
const createPlaylist = async (title, visibility) => {
    const response = await fetch('/api/v1/playlists', {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ title, visibility })
    });

    return await response.json();
};

// 곡 추가
const addMusicToPlaylist = async (playlistId, musicId, order) => {
    const response = await fetch(`/api/v1/playlists/${playlistId}/items`, {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ music_id: musicId, order })
    });

    return await response.json();
};

// 사용 예시
const playlist = await createPlaylist('나의 플레이리스트', 'public');
await addMusicToPlaylist(playlist.playlist_id, 123, 1);
```

## ⚠️ 주의사항

### 곡 순서 관리
- `order` 필드는 1부터 시작하는 순차적인 값
- 중간에 곡을 추가할 때는 기존 순서를 고려해야 함
- 순서 재정렬이 필요한 경우 전체 곡의 순서를 다시 설정

### 성능 고려사항
- 플레이리스트에 포함된 곡이 많을 경우 페이지네이션 고려
- 빈번한 순서 변경은 DB 부하를 줄 수 있음

### 데이터 정합성
- 삭제된 음악은 플레이리스트에서 자동으로 제거되지 않음
- 클라이언트에서 음악 존재 여부 확인 필요

## 🔍 관련 파일

- `music/views/playlist.py` - 플레이리스트 API 구현
- `music/models.py` - Playlist, PlaylistItem, PlaylistLike 모델
- `music/serializers/playlist.py` - 플레이리스트 시리얼라이저