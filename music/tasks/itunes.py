"""
iTunes 통합 관련 Celery 작업
"""
import logging
from celery import shared_task
from django.utils import timezone
from django.db import transaction

from ..models import Music, Artists, Albums

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def save_itunes_track_to_db_task(self, itunes_data: dict):
    """
    iTunes 곡을 DB에 저장하는 백그라운드 태스크 (방안 2: 비동기 DB 저장)
    
    **목적:**
    - 상세 조회 API에서 즉시 응답하기 위해 DB 저장을 백그라운드로 처리
    - 응답 시간 50-200ms 절약 (DB 저장 시간)
    
    **동작 흐름:**
    1. 상세 조회 API: iTunes API 호출 → 파싱 → 이 태스크 호출(.delay()) → 즉시 응답 (202 Accepted)
    2. Celery 워커: 이 태스크를 백그라운드에서 실행 → DB 저장
    3. 사용자: 대기 없이 음악 재생 가능
    
    **중복 방지:**
    - DB에 이미 같은 itunes_id가 있으면 저장하지 않음
    
    **재시도:**
    - 실패 시 최대 3번까지 재시도 (10초 간격)
    
    Args:
        self: Celery task 인스턴스
        itunes_data: iTunes API에서 파싱된 데이터
            {
                'itunes_id': int,
                'music_name': str,
                'artist_name': str,
                'album_name': str,
                'genre': str,
                'duration': int,
                'audio_url': str,
                ...
            }
        
    Returns:
        저장된 music_id (성공 시) 또는 None (실패 시)
    """
    try:
        itunes_id = itunes_data.get('itunes_id')
        
        # iTunes ID 검증
        if not itunes_id:
            logger.error("[iTunes 저장] itunes_id가 없습니다.")
            return None
        
        # 중복 확인: 이미 DB에 있으면 저장하지 않음
        if Music.objects.filter(itunes_id=itunes_id, is_deleted=False).exists():
            logger.info(f"[iTunes 저장] 이미 DB에 존재 (중복 방지): itunes_id={itunes_id}")
            existing_music = Music.objects.get(itunes_id=itunes_id, is_deleted=False)
            return existing_music.music_id
        
        logger.info(f"[iTunes 저장] 시작: itunes_id={itunes_id}, music_name={itunes_data.get('music_name')}")
        
        now = timezone.now()
        
        # 트랜잭션으로 묶어서 전체 저장 성공 또는 전체 실패 보장
        with transaction.atomic():
            # Artist 생성 또는 조회
            # - 같은 이름의 아티스트가 있으면 재사용
            # - 없으면 새로 생성
            artist = None
            artist_name = itunes_data.get('artist_name', '')
            if artist_name:
                artist, created = Artists.objects.get_or_create(
                    artist_name=artist_name,
                    defaults={
                        'artist_image': '',  # 비동기로 수집
                        'created_at': now,
                        'is_deleted': False,
                    }
                )
                if created:
                    logger.info(f"[iTunes 저장] Artist 생성: {artist_name}")
                
                # 아티스트 이미지 비동기 수집 (새로 생성되었거나 이미지가 없는 경우)
                if created or not artist.artist_image:
                    try:
                        # 순환 참조 방지를 위해 지연 import
                        from .metadata import fetch_artist_image_task
                        fetch_artist_image_task.delay(artist.artist_id, artist_name)
                    except Exception as e:
                        logger.warning(f"[iTunes 저장] 아티스트 이미지 태스크 호출 실패: {e}")
            
            # Album 생성 또는 조회
            # - 같은 아티스트의 같은 앨범이 있으면 재사용
            # - 없으면 새로 생성
            album = None
            album_name = itunes_data.get('album_name', '')
            if album_name and artist:
                album, created = Albums.objects.get_or_create(
                    album_name=album_name,
                    artist=artist,
                    defaults={
                        'album_image': '',  # 비동기로 수집
                        'created_at': now,
                        'is_deleted': False,
                    }
                )
                if created:
                    logger.info(f"[iTunes 저장] Album 생성: {album_name}")
                
                # 앨범 이미지 비동기 수집 (새로 생성되었거나 이미지가 없는 경우)
                album_image_url = itunes_data.get('album_image', '')
                if album_image_url and (created or not album.album_image):
                    try:
                        # 순환 참조 방지를 위해 지연 import
                        from .metadata import fetch_album_image_task
                        fetch_album_image_task.delay(album.album_id, album_name, album_image_url)
                    except Exception as e:
                        logger.warning(f"[iTunes 저장] 앨범 이미지 태스크 호출 실패: {e}")
            
            # Music 생성
            music = Music.objects.create(
                itunes_id=itunes_id,
                music_name=itunes_data.get('music_name', ''),
                artist=artist,
                album=album,
                genre=itunes_data.get('genre', ''),
                duration=itunes_data.get('duration'),
                audio_url=itunes_data.get('audio_url', ''),
                is_ai=False,  # iTunes 곡은 AI 생성곡이 아님
                created_at=now,
                is_deleted=False,
            )
            
            logger.info(f"[iTunes 저장] 완료: music_id={music.music_id}, itunes_id={itunes_id}")
            return music.music_id
        
    except Exception as e:
        logger.error(f"[iTunes 저장] 실패: itunes_id={itunes_data.get('itunes_id')}, 오류: {e}")
        
        # 재시도 로직 (최대 3번)
        if self.request.retries < self.max_retries:
            logger.info(f"[iTunes 저장] 재시도 예약: {self.request.retries + 1}/{self.max_retries}")
            raise self.retry(exc=e, countdown=10)  # 10초 후 재시도
        
        logger.error(f"[iTunes 저장] 최대 재시도 횟수 초과 - 저장 실패")
        return None
