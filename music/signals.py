"""
Django Signals for automatic image processing and user setup

앨범이나 아티스트의 이미지 URL이 변경되면 자동으로 S3에 업로드하고 리사이징합니다.
사용자가 회원가입하면 자동으로 기본 플레이리스트를 생성합니다.
"""
import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction
from django.utils import timezone
from .models import Albums, Artists, Users, Playlists

logger = logging.getLogger(__name__)


def is_s3_url(url: str) -> bool:
    """URL이 S3 URL인지 확인"""
    if not url:
        return False
    return 's3.amazonaws.com' in url or 'amazonaws.com' in url


@receiver(post_save, sender=Albums)
def album_image_changed(sender, instance, created, update_fields, **kwargs):
    """
    앨범의 이미지 URL이 변경되면 자동으로 S3에 업로드하고 리사이징
    
    - 새로 생성되었거나 album_image가 변경된 경우
    - album_image가 S3 URL이 아닌 경우 (외부 URL인 경우)
    - 자동으로 fetch_album_image_task를 실행
    """
    # update_fields가 있고 album_image가 포함되지 않으면 스킵
    if update_fields is not None and 'album_image' not in update_fields:
        return
    
    # album_image가 없으면 스킵
    if not instance.album_image:
        return
    
    # transaction 밖에서 실행되도록 on_commit 사용
    def process_album_image():
        try:
            # DB에서 최신 데이터 다시 조회 (트랜잭션 안전성)
            try:
                album = Albums.objects.get(album_id=instance.album_id)
            except Albums.DoesNotExist:
                logger.error(f"[Signal] 앨범을 찾을 수 없음: album_id={instance.album_id}")
                return
            
            # 최신 데이터로 다시 확인
            if not album.album_image:
                return
            
            # 이미 S3 URL이면 스킵
            if is_s3_url(album.album_image):
                logger.debug(f"[Signal] 앨범 이미지가 이미 S3 URL임, 스킵: album_id={album.album_id}")
                return
            
            # image_square가 이미 있으면 스킵 (이미 처리됨)
            if album.image_square and is_s3_url(album.image_square):
                logger.debug(f"[Signal] 앨범 이미지가 이미 처리됨, 스킵: album_id={album.album_id}")
                return
            
            # Celery 태스크 실행 (순환 참조 방지를 위해 여기서 import)
            from .tasks.metadata import fetch_album_image_task
            
            logger.info(f"[Signal] 앨범 이미지 처리 태스크 시작: album_id={album.album_id}, name={album.album_name}")
            
            # 비동기로 이미지 처리 (artist_name도 전달하여 YouTube Music 검색 정확도 향상)
            artist_name = album.artist.artist_name if album.artist else None
            fetch_album_image_task.delay(
                album_id=album.album_id,
                album_name=album.album_name or '',
                album_image_url=album.album_image,  # iTunes fallback용
                artist_name=artist_name  # YouTube Music 검색용
            )
            
        except Exception as e:
            logger.error(f"[Signal] 앨범 이미지 처리 실패: album_id={instance.album_id}, 오류: {e}")
    
    # DB transaction이 완료된 후 실행
    transaction.on_commit(process_album_image)


@receiver(post_save, sender=Artists)
def artist_image_changed(sender, instance, created, update_fields, **kwargs):
    """
    아티스트의 이미지 URL이 변경되면 자동으로 S3에 업로드하고 리사이징
    
    - 새로 생성되었거나 artist_image가 변경된 경우
    - artist_image가 S3 URL이 아닌 경우 (외부 URL인 경우)
    - 자동으로 fetch_artist_image_task를 실행
    """
    # update_fields가 있고 artist_image가 포함되지 않으면 스킵
    if update_fields is not None and 'artist_image' not in update_fields:
        return
    
    # artist_image가 없으면 스킵
    if not instance.artist_image:
        return
    
    # transaction 밖에서 실행되도록 on_commit 사용
    def process_artist_image():
        try:
            # DB에서 최신 데이터 다시 조회 (트랜잭션 안전성)
            try:
                artist = Artists.objects.get(artist_id=instance.artist_id)
            except Artists.DoesNotExist:
                logger.error(f"[Signal] 아티스트를 찾을 수 없음: artist_id={instance.artist_id}")
                return
            
            # 최신 데이터로 다시 확인
            if not artist.artist_image:
                return
            
            # 이미 S3 URL이면 스킵
            if is_s3_url(artist.artist_image):
                logger.debug(f"[Signal] 아티스트 이미지가 이미 S3 URL임, 스킵: artist_id={artist.artist_id}")
                return
            
            # image_square가 이미 있으면 스킵 (이미 처리됨)
            if artist.image_square and is_s3_url(artist.image_square):
                logger.debug(f"[Signal] 아티스트 이미지가 이미 처리됨, 스킵: artist_id={artist.artist_id}")
                return
            
            # Celery 태스크 실행 (순환 참조 방지를 위해 여기서 import)
            from .tasks.metadata import fetch_artist_image_task
            
            logger.info(f"[Signal] 아티스트 이미지 처리 태스크 시작: artist_id={artist.artist_id}, name={artist.artist_name}")
            
            # 비동기로 이미지 처리
            fetch_artist_image_task.delay(
                artist_id=artist.artist_id,
                artist_name=artist.artist_name
            )
            
        except Exception as e:
            logger.error(f"[Signal] 아티스트 이미지 처리 실패: artist_id={instance.artist_id}, 오류: {e}")
    
    # DB transaction이 완료된 후 실행
    transaction.on_commit(process_artist_image)


@receiver(post_save, sender=Users)
def create_default_playlist(sender, instance, created, **kwargs):
    """
    사용자가 회원가입하면 자동으로 "나의 좋아요 목록록" 플레이리스트를 생성
    
    - 회원가입 시에만 실행 (created=True)
    - 제목: "좋아요 표시한 음악"
    - visibility: private
    - 생성자: 회원가입한 사용자
    """
    # 신규 사용자가 아니면 스킵
    if not created:
        return
    
    # transaction 밖에서 실행되도록 on_commit 사용
    def create_playlist():
        try:
            # DB에서 최신 데이터 다시 조회 (트랜잭션 안전성)
            try:
                user = Users.objects.get(user_id=instance.user_id)
            except Users.DoesNotExist:
                logger.error(f"[Signal] 사용자를 찾을 수 없음: user_id={instance.user_id}")
                return
            
            # 기본 플레이리스트 생성
            now = timezone.now()
            playlist = Playlists.objects.create(
                user=user,
                title="나의 좋아요 목록",
                visibility="private",
                created_at=now,
                updated_at=now,
                is_deleted=False
            )
            
            logger.info(f"[Signal] 기본 플레이리스트 생성 완료: user_id={user.user_id}, "
                       f"playlist_id={playlist.playlist_id}, email={user.email}")
            
        except Exception as e:
            logger.error(f"[Signal] 기본 플레이리스트 생성 실패: user_id={instance.user_id}, 오류: {e}")
    
    # DB transaction이 완료된 후 실행
    transaction.on_commit(create_playlist)
