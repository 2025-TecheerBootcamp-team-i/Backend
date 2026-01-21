# 기본 플레이리스트 자동 생성 기능

## 개요
사용자가 회원가입을 완료하면 자동으로 "좋아요 표시한 음악" 플레이리스트가 생성됩니다.

## 구현 세부사항

### 1. Signal 기반 자동 생성
- **위치**: `music/signals.py`
- **Signal**: `post_save` on `Users` model
- **트리거**: 사용자 생성 시 (`created=True`)
- **트랜잭션 안전성**: `transaction.on_commit()` 사용하여 DB 커밋 후 실행

### 2. 플레이리스트 속성
```python
{
    "title": "좋아요 표시한 음악",
    "visibility": "private",
    "user": <회원가입한 사용자>,
    "created_at": <현재 시간>,
    "updated_at": <현재 시간>,
    "is_deleted": False
}
```

### 3. 구현 파일

#### music/signals.py
```python
@receiver(post_save, sender=Users)
def create_default_playlist(sender, instance, created, **kwargs):
    """
    사용자가 회원가입하면 자동으로 "좋아요 표시한 음악" 플레이리스트를 생성
    """
    if not created:
        return
    
    def create_playlist():
        try:
            user = Users.objects.get(user_id=instance.user_id)
            now = timezone.now()
            playlist = Playlists.objects.create(
                user=user,
                title="좋아요 표시한 음악",
                visibility="private",
                created_at=now,
                updated_at=now,
                is_deleted=False
            )
            logger.info(f"기본 플레이리스트 생성 완료: user_id={user.user_id}")
        except Exception as e:
            logger.error(f"기본 플레이리스트 생성 실패: {e}")
    
    transaction.on_commit(create_playlist)
```

#### music/apps.py
Signal이 자동으로 등록되도록 이미 설정되어 있습니다:
```python
def ready(self):
    """앱이 준비되면 signals를 등록"""
    import music.signals  # noqa
```

## 테스트

### 단위 테스트
```bash
python manage.py test music.tests.UserSignalTestCase
```

**테스트 케이스:**
1. `test_create_default_playlist_on_signup`: 회원가입 시 플레이리스트 자동 생성 확인
2. `test_no_playlist_on_user_update`: 사용자 정보 수정 시 플레이리스트 중복 생성 방지 확인
3. `test_multiple_users_get_own_playlists`: 여러 사용자가 각각 자신의 플레이리스트 보유 확인

### 통합 테스트 (API)
```bash
python manage.py test music.tests.RegisterAPITestCase
```

**테스트 케이스:**
1. `test_register_creates_default_playlist`: 회원가입 API 호출 시 플레이리스트 자동 생성 확인

### 수동 테스트

#### 1. 회원가입 API 호출
```bash
curl -X POST http://localhost:8000/api/v1/auth/users/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "Test1234!@",
    "password_confirm": "Test1234!@",
    "nickname": "테스트유저"
  }'
```

**예상 응답:**
```json
{
  "message": "회원가입 성공",
  "user_id": 1,
  "email": "test@example.com",
  "nickname": "테스트유저"
}
```

#### 2. 플레이리스트 확인
```bash
# 로그인하여 토큰 획득
curl -X POST http://localhost:8000/api/v1/auth/tokens/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "Test1234!@"
  }'

# 플레이리스트 목록 조회
curl -X GET http://localhost:8000/api/v1/playlists \
  -H "Authorization: Bearer <access_token>"
```

**예상 응답:**
```json
[
  {
    "playlist_id": 1,
    "title": "좋아요 표시한 음악",
    "visibility": "private",
    "creator_nickname": "테스트유저",
    "item_count": 0,
    "like_count": 0,
    "created_at": "2026-01-22T10:00:00Z",
    "updated_at": "2026-01-22T10:00:00Z"
  }
]
```

## 로깅

플레이리스트 생성 성공/실패 시 로그가 기록됩니다:

```
[INFO] [Signal] 기본 플레이리스트 생성 완료: user_id=1, playlist_id=1, email=test@example.com
```

실패 시:
```
[ERROR] [Signal] 기본 플레이리스트 생성 실패: user_id=1, 오류: <에러 메시지>
```

## 주의사항

1. **managed=False 모델**: 테스트 시 데이터베이스 테이블이 미리 생성되어 있어야 합니다.
2. **트랜잭션 안전성**: `transaction.on_commit()` 사용으로 DB 커밋 후에만 플레이리스트가 생성됩니다.
3. **중복 생성 방지**: `created=True`일 때만 실행되므로 사용자 정보 수정 시에는 플레이리스트가 중복 생성되지 않습니다.
4. **에러 처리**: 플레이리스트 생성 실패 시에도 회원가입 자체는 성공합니다 (로그로 에러 기록).

## 향후 개선사항

1. **좋아요 연동**: MusicLikes 테이블과 연동하여 좋아요한 곡을 자동으로 플레이리스트에 추가
2. **다국어 지원**: 플레이리스트 제목을 사용자 언어 설정에 따라 변경
3. **커스터마이징**: 사용자가 기본 플레이리스트 제목을 변경할 수 있도록 설정 추가
