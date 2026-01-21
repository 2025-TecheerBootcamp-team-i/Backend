"""
기본 플레이리스트 자동 생성 기능 테스트 스크립트

실행 방법:
python manage.py shell < test_default_playlist.py

또는:
python manage.py shell
>>> exec(open('test_default_playlist.py').read())
"""

import os
import sys
import django

# Django 설정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.hashers import make_password
from django.utils import timezone
from music.models import Users, Playlists

def test_default_playlist_creation():
    """기본 플레이리스트 자동 생성 테스트"""
    
    print("\n" + "="*80)
    print("기본 플레이리스트 자동 생성 기능 테스트")
    print("="*80 + "\n")
    
    # 테스트용 이메일
    test_email = "test_signal_user@example.com"
    
    # 1. 기존 테스트 사용자 삭제
    print("1. 기존 테스트 사용자 확인 및 삭제...")
    existing_users = Users.objects.filter(email=test_email)
    if existing_users.exists():
        print(f"   기존 사용자 발견: {existing_users.count()}명")
        existing_users.update(is_deleted=True, updated_at=timezone.now())
        print("   기존 사용자 소프트 삭제 완료")
    else:
        print("   기존 사용자 없음")
    
    # 2. 새 사용자 생성
    print("\n2. 새 사용자 생성 중...")
    now = timezone.now()
    user = Users.objects.create(
        email=test_email,
        password=make_password("TestPassword123!"),
        nickname="테스트시그널유저",
        created_at=now,
        updated_at=now,
        is_deleted=False
    )
    print(f"   [OK] 사용자 생성 완료: user_id={user.user_id}, email={user.email}")
    
    # 3. 플레이리스트 확인
    print("\n3. 자동 생성된 플레이리스트 확인 중...")
    import time
    time.sleep(1)  # signal 처리 대기
    
    playlists = Playlists.objects.filter(user=user, is_deleted=False)
    print(f"   플레이리스트 개수: {playlists.count()}")
    
    if playlists.count() == 0:
        print("   [ERROR] 플레이리스트가 생성되지 않았습니다!")
        print("\n   디버깅 정보:")
        print(f"   - User ID: {user.user_id}")
        print(f"   - Email: {user.email}")
        print(f"   - Nickname: {user.nickname}")
        print("\n   가능한 원인:")
        print("   1. signal이 등록되지 않았을 수 있습니다 (apps.py 확인)")
        print("   2. transaction.on_commit()이 실행되지 않았을 수 있습니다")
        print("   3. 로그를 확인해서 에러가 있는지 확인하세요")
        return False
    
    # 4. 플레이리스트 상세 정보 확인
    print("\n4. 플레이리스트 상세 정보:")
    for idx, playlist in enumerate(playlists, 1):
        print(f"\n   플레이리스트 #{idx}:")
        print(f"   - playlist_id: {playlist.playlist_id}")
        print(f"   - title: {playlist.title}")
        print(f"   - visibility: {playlist.visibility}")
        print(f"   - user_id: {playlist.user.user_id}")
        print(f"   - created_at: {playlist.created_at}")
        print(f"   - is_deleted: {playlist.is_deleted}")
    
    # 5. 검증
    print("\n5. 검증 결과:")
    playlist = playlists.first()
    
    checks = []
    checks.append(("플레이리스트 개수", playlists.count() == 1, f"1개 (실제: {playlists.count()}개)"))
    checks.append(("제목", playlist.title == "좋아요 표시한 음악", f"'{playlist.title}'"))
    checks.append(("공개 범위", playlist.visibility == "private", f"'{playlist.visibility}'"))
    checks.append(("소유자", playlist.user == user, f"user_id={playlist.user.user_id}"))
    checks.append(("삭제 여부", playlist.is_deleted == False, f"{playlist.is_deleted}"))
    
    all_passed = True
    for check_name, passed, value in checks:
        status_icon = "[OK]" if passed else "[FAIL]"
        status_text = "PASS" if passed else "FAIL"
        print(f"   {status_icon} {check_name}: {status_text} ({value})")
        if not passed:
            all_passed = False
    
    # 6. 최종 결과
    print("\n" + "="*80)
    if all_passed:
        print("[SUCCESS] 테스트 성공! 기본 플레이리스트가 정상적으로 생성되었습니다.")
    else:
        print("[FAILED] 테스트 실패! 일부 검증이 통과하지 못했습니다.")
    print("="*80 + "\n")
    
    # 7. 정리 (선택사항)
    cleanup = input("테스트 데이터를 삭제하시겠습니까? (y/N): ").strip().lower()
    if cleanup == 'y':
        user.is_deleted = True
        user.updated_at = timezone.now()
        user.save()
        print(f"테스트 사용자 삭제 완료: {test_email}")
    else:
        print("테스트 데이터가 유지됩니다.")
    
    return all_passed


if __name__ == "__main__":
    try:
        test_default_playlist_creation()
    except Exception as e:
        print(f"\n[ERROR] 테스트 중 에러 발생: {e}")
        import traceback
        traceback.print_exc()
