"""
메타데이터 수집 Celery 작업 (아티스트 이미지, 앨범 이미지, 가사)
"""
import logging
from celery import shared_task
from django.utils import timezone

from ..models import Music, Artists, Albums
from ..utils.s3_upload import upload_image_to_s3, is_s3_url
from ..services import WikidataService, LRCLIBService, DeezerService, LyricsOvhService

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2)
def fetch_artist_image_task(self, artist_id: int, artist_name: str):
    """
    아티스트 이미지를 비동기로 조회하고 S3에 업로드 후 DB 업데이트
    
    API 호출 순서 (fallback 체인):
    1. Wikidata API (1차)
    2. Deezer API (2차 fallback)
    
    이미지 처리:
    1. 외부 API에서 이미지 URL 조회
    2. S3에 업로드 (media/images/artists/original/)
    3. Lambda가 자동으로 리사이징 (원형 228x228, 208x208 / 사각형 220x220)
    4. DB에 S3 URL 저장
    
    Args:
        artist_id: Artist 모델의 ID
        artist_name: 아티스트 이름
        
    Returns:
        S3 이미지 URL 또는 None
    """
    try:
        logger.info(f"[아티스트 이미지] 조회 시작: artist_id={artist_id}, name={artist_name}")
        
        # Artist 객체 조회
        try:
            artist = Artists.objects.get(artist_id=artist_id, is_deleted=False)
        except Artists.DoesNotExist:
            logger.error(f"[아티스트 이미지] Artist를 찾을 수 없음: artist_id={artist_id}")
            return None
        
        # 이미 S3 이미지가 있으면 스킵
        if artist.artist_image and artist.artist_image.strip():
            if is_s3_url(artist.artist_image):
                logger.info(f"[아티스트 이미지] 이미 S3 이미지가 있음: artist_id={artist_id}")
                return artist.artist_image
            # S3 URL이 아니면 새로 업로드 진행
            logger.info(f"[아티스트 이미지] 기존 URL이 S3가 아님, S3로 업로드 진행: artist_id={artist_id}")
        
        image_url = None
        source = None
        
        # 1차: Wikidata에서 이미지 조회
        image_url = WikidataService.fetch_artist_image(artist_name)
        if image_url:
            source = "Wikidata"
        
        # 2차 fallback: Deezer에서 이미지 조회
        if not image_url:
            logger.info(f"[아티스트 이미지] Wikidata 실패, Deezer fallback 시도: {artist_name}")
            image_url = DeezerService.fetch_artist_image(artist_name)
            if image_url:
                source = "Deezer"
        
        if image_url:
            # S3에 이미지 업로드 (Lambda가 자동으로 리사이징)
            try:
                resized_urls = upload_image_to_s3(
                    image_url=image_url,
                    image_type='artists',
                    entity_id=artist_id,
                    entity_name=artist_name
                )
                logger.info(f"[아티스트 이미지] S3 업로드 완료 ({source}): artist_id={artist_id}")
                
                # DB 업데이트 (원본 + 리사이징된 이미지 URL 저장)
                artist.artist_image = resized_urls.get('original')
                artist.image_large_circle = resized_urls.get('image_large_circle')  # 228x228
                artist.image_small_circle = resized_urls.get('image_small_circle')  # 208x208
                artist.image_square = resized_urls.get('image_square')  # 220x220
                artist.updated_at = timezone.now()
                artist.save()
                logger.info(f"[아티스트 이미지] DB 저장 완료: artist_id={artist_id}")
                logger.info(f"  - 원본: {resized_urls.get('original', '')[:60]}...")
                logger.info(f"  - 큰 원: {resized_urls.get('image_large_circle', '')[:60]}...")
                logger.info(f"  - 작은 원: {resized_urls.get('image_small_circle', '')[:60]}...")
                logger.info(f"  - 사각형: {resized_urls.get('image_square', '')[:60]}...")
                return resized_urls.get('original')
                
            except Exception as upload_error:
                # S3 업로드 실패 시 원본 URL이라도 저장
                logger.warning(f"[아티스트 이미지] S3 업로드 실패, 원본 URL 저장: {upload_error}")
                artist.artist_image = image_url
                artist.updated_at = timezone.now()
                artist.save()
                logger.info(f"[아티스트 이미지] 원본 URL 저장 완료 ({source}): artist_id={artist_id}")
                return image_url
        else:
            logger.info(f"[아티스트 이미지] 모든 API에서 이미지를 찾지 못함: artist_id={artist_id}")
            return None
            
    except Exception as e:
        logger.error(f"[아티스트 이미지] 실패: artist_id={artist_id}, 오류: {e}")
        
        if self.request.retries < self.max_retries:
            logger.info(f"[아티스트 이미지] 재시도: {self.request.retries + 1}/{self.max_retries}")
            raise self.retry(exc=e, countdown=30)
        
        return None


@shared_task(bind=True, max_retries=2)
def fetch_album_image_task(self, album_id: int, album_name: str, album_image_url: str):
    """
    앨범 이미지를 S3에 업로드하고 리사이징된 URL을 DB에 저장
    
    이미지 처리:
    1. 외부 URL에서 이미지 다운로드
    2. S3에 업로드 (media/images/albums/original/)
    3. Lambda가 자동으로 리사이징 (사각형 220x220)
    4. DB에 원본 + 리사이징된 URL 저장
    
    Args:
        album_id: Album 모델의 ID
        album_name: 앨범 이름
        album_image_url: 앨범 이미지 URL
        
    Returns:
        S3 이미지 URL 또는 None
    """
    try:
        logger.info(f"[앨범 이미지] 업로드 시작: album_id={album_id}, name={album_name}")
        
        # Album 객체 조회
        try:
            album = Albums.objects.get(album_id=album_id, is_deleted=False)
        except Albums.DoesNotExist:
            logger.error(f"[앨범 이미지] Album을 찾을 수 없음: album_id={album_id}")
            return None
        
        # 이미 S3 이미지가 있으면 스킵
        if album.album_image and album.album_image.strip():
            if is_s3_url(album.album_image):
                logger.info(f"[앨범 이미지] 이미 S3 이미지가 있음: album_id={album_id}")
                return album.album_image
            # S3 URL이 아니면 새로 업로드 진행
            logger.info(f"[앨범 이미지] 기존 URL이 S3가 아님, S3로 업로드 진행: album_id={album_id}")
        
        if not album_image_url:
            logger.info(f"[앨범 이미지] 이미지 URL이 없음: album_id={album_id}")
            return None
        
        # S3에 이미지 업로드 (Lambda가 자동으로 리사이징)
        try:
            resized_urls = upload_image_to_s3(
                image_url=album_image_url,
                image_type='albums',
                entity_id=album_id,
                entity_name=album_name
            )
            logger.info(f"[앨범 이미지] S3 업로드 완료: album_id={album_id}")
            
            # DB 업데이트 (원본 + 리사이징된 이미지 URL 저장)
            album.album_image = resized_urls.get('original')
            album.image_square = resized_urls.get('image_square')  # 220x220
            album.updated_at = timezone.now()
            album.save()
            logger.info(f"[앨범 이미지] DB 저장 완료: album_id={album_id}")
            logger.info(f"  - 원본: {resized_urls.get('original', '')[:60]}...")
            logger.info(f"  - 사각형: {resized_urls.get('image_square', '')[:60]}...")
            return resized_urls.get('original')
            
        except Exception as upload_error:
            # S3 업로드 실패 시 원본 URL이라도 저장
            logger.warning(f"[앨범 이미지] S3 업로드 실패, 원본 URL 저장: {upload_error}")
            album.album_image = album_image_url
            album.updated_at = timezone.now()
            album.save()
            logger.info(f"[앨범 이미지] 원본 URL 저장 완료: album_id={album_id}")
            return album_image_url
            
    except Exception as e:
        logger.error(f"[앨범 이미지] 실패: album_id={album_id}, 오류: {e}")
        
        if self.request.retries < self.max_retries:
            logger.info(f"[앨범 이미지] 재시도: {self.request.retries + 1}/{self.max_retries}")
            raise self.retry(exc=e, countdown=30)
        
        return None


@shared_task(bind=True, max_retries=2)
def fetch_lyrics_task(self, music_id: int, artist_name: str, track_name: str, duration: int = None):
    """
    가사를 비동기로 조회하고 DB 업데이트
    
    API 호출 순서 (fallback 체인):
    1. LRCLIB API (1차) - 동기화된 LRC 가사 지원
    2. lyrics.ovh API (2차 fallback) - 일반 텍스트 가사
    
    Args:
        music_id: Music 모델의 ID
        artist_name: 아티스트 이름
        track_name: 곡 이름
        duration: 곡 길이 (초 단위)
        
    Returns:
        가사 문자열 또는 None
    """
    try:
        logger.info(f"[가사 조회] 시작: music_id={music_id}, {artist_name} - {track_name}")
        
        # Music 객체 조회
        try:
            music = Music.objects.get(music_id=music_id, is_deleted=False)
        except Music.DoesNotExist:
            logger.error(f"[가사 조회] Music을 찾을 수 없음: music_id={music_id}")
            return None
        
        # 이미 가사가 있으면 스킵
        if music.lyrics and music.lyrics.strip():
            logger.info(f"[가사 조회] 이미 가사가 있음: music_id={music_id}")
            return music.lyrics
        
        lyrics = None
        source = None
        
        # 1차: LRCLIB에서 가사 조회 (동기화된 LRC 가사 우선)
        lyrics = LRCLIBService.fetch_lyrics(artist_name, track_name, duration)
        if lyrics:
            source = "LRCLIB"
        
        # 2차 fallback: lyrics.ovh에서 가사 조회
        if not lyrics:
            logger.info(f"[가사 조회] LRCLIB 실패, lyrics.ovh fallback 시도: {artist_name} - {track_name}")
            lyrics = LyricsOvhService.fetch_lyrics(artist_name, track_name)
            if lyrics:
                source = "lyrics.ovh"
        
        if lyrics:
            # DB 업데이트
            music.lyrics = lyrics
            music.updated_at = timezone.now()
            music.save()
            logger.info(f"[가사 조회] 저장 완료 ({source}): music_id={music_id}, 길이={len(lyrics)}")
            return lyrics
        else:
            logger.info(f"[가사 조회] 모든 API에서 가사를 찾지 못함: music_id={music_id}")
            return None
            
    except Exception as e:
        logger.error(f"[가사 조회] 실패: music_id={music_id}, 오류: {e}")
        
        if self.request.retries < self.max_retries:
            logger.info(f"[가사 조회] 재시도: {self.request.retries + 1}/{self.max_retries}")
            raise self.retry(exc=e, countdown=30)
        
        return None
