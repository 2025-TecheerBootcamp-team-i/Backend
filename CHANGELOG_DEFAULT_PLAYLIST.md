# 변경 사항: 기본 플레이리스트 자동 생성 기능

## 날짜
2026-01-22

## 개요
사용자가 회원가입을 완료하면 자동으로 "좋아요 표시한 음악" 플레이리스트가 생성되는 기능을 추가했습니다.

## 변경된 파일

### 1. `music/signals.py`
**변경 내용:**
- `Users` 모델에 대한 `post_save` signal 추가
- 회원가입 시 자동으로 "좋아요 표시한 음악" 플레이리스트 생성
- `transaction.on_commit()` 사용하여 트랜잭션 안전성 보장

**주요 코드:**
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

### 2. `music/tests.py`
**변경 내용:**
- `UserSignalTestCase`: 사용자 생성 시 플레이리스트 자동 생성 테스트
- `RegisterAPITestCase`: 회원가입 API 통합 테스트
- `TransactionTestCase` 사용하여 signal의 `transaction.on_commit()` 정상 작동 보장

**테스트 케이스:**
1. `test_create_default_playlist_on_signup`: 회원가입 시 플레이리스트 자동 생성 확인
2. `test_no_playlist_on_user_update`: 사용자 정보 수정 시 중복 생성 방지 확인
3. `test_multiple_users_get_own_playlists`: 여러 사용자가 각각 자신의 플레이리스트 보유 확인
4. `test_register_creates_default_playlist`: 회원가입 API 호출 시 플레이리스트 자동 생성 확인

### 3. `test_default_playlist.py` (새 파일)
**내용:**
- 독립 실행 가능한 테스트 스크립트
- Django shell을 통해 직접 기능 테스트 가능
- 상세한 디버깅 정보 제공

**실행 방법:**
```bash
python test_default_playlist.py
```

### 4. `docs/DEFAULT_PLAYLIST.md` (새 파일)
**내용:**
- 기능 설명 및 구현 세부사항
- 테스트 방법 (단위 테스트, 통합 테스트, 수동 테스트)
- API 사용 예제
- 주의사항 및 향후 개선사항

## 기능 명세

### 자동 생성되는 플레이리스트 속성
- **제목**: "좋아요 표시한 음악"
- **공개 범위**: private
- **소유자**: 회원가입한 사용자
- **생성 시점**: 회원가입 직후 (DB 트랜잭션 커밋 후)

### 동작 방식
1. 사용자가 회원가입 API (`POST /api/v1/auth/users/`) 호출
2. `UserRegisterSerializer.create()`에서 `Users.objects.create()` 실행
3. Django signal (`post_save`)이 자동으로 트리거
4. `create_default_playlist` 함수가 `transaction.on_commit()` 후 실행
5. "좋아요 표시한 음악" 플레이리스트 생성
6. 로그 기록 (`logger.info` 또는 `logger.error`)

## 테스트 결과

### 테스트 실행 결과
```
================================================================================
기본 플레이리스트 자동 생성 기능 테스트
================================================================================

1. 기존 테스트 사용자 확인 및 삭제...
   기존 사용자 발견: 1명
   기존 사용자 소프트 삭제 완료

2. 새 사용자 생성 중...
   [OK] 사용자 생성 완료: user_id=19, email=test_signal_user@example.com

3. 자동 생성된 플레이리스트 확인 중...
   플레이리스트 개수: 1

4. 플레이리스트 상세 정보:

   플레이리스트 #1:
   - playlist_id: 15
   - title: 좋아요 표시한 음악
   - visibility: private
   - user_id: 19
   - created_at: 2026-01-21 15:31:14.558553
   - is_deleted: False

5. 검증 결과:
   [OK] 플레이리스트 개수: PASS (1개 (실제: 1개))
   [OK] 제목: PASS ('좋아요 표시한 음악')
   [OK] 공개 범위: PASS ('private')
   [OK] 소유자: PASS (user_id=19)
   [OK] 삭제 여부: PASS (False)

================================================================================
[SUCCESS] 테스트 성공! 기본 플레이리스트가 정상적으로 생성되었습니다.
================================================================================
```

## 주의사항

1. **managed=False 모델**: 테스트 시 실제 데이터베이스 테이블이 필요합니다.
2. **트랜잭션 안전성**: `transaction.on_commit()` 사용으로 DB 커밋 후에만 플레이리스트가 생성됩니다.
3. **중복 생성 방지**: `created=True`일 때만 실행되므로 사용자 정보 수정 시에는 플레이리스트가 중복 생성되지 않습니다.
4. **에러 처리**: 플레이리스트 생성 실패 시에도 회원가입 자체는 성공합니다 (로그로 에러 기록).

## 향후 개선사항

1. **좋아요 연동**: MusicLikes 테이블과 연동하여 좋아요한 곡을 자동으로 플레이리스트에 추가
2. **다국어 지원**: 플레이리스트 제목을 사용자 언어 설정에 따라 변경
3. **커스터마이징**: 사용자가 기본 플레이리스트 제목을 변경할 수 있도록 설정 추가
4. **더 많은 기본 플레이리스트**: "최근 재생한 음악", "AI 추천 플레이리스트" 등 추가 가능

## 관련 파일
- `music/signals.py`: Signal 정의
- `music/apps.py`: Signal 등록
- `music/tests.py`: 테스트 케이스
- `test_default_playlist.py`: 독립 테스트 스크립트
- `docs/DEFAULT_PLAYLIST.md`: 기능 문서
