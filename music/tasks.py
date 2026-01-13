"""
Celery 비동기 작업 정의 (AI 음악 생성, 차트 계산, 데이터 정리)
"""
import time
import logging
from datetime import timedelta
from celery import shared_task
from django.utils import timezone
from django.utils.timezone import localtime
from django.db.models import Count
from django.db import transaction

from .models import Music, AiInfo, Users, Artists, Albums, PlayLogs, Charts
from .music_generate.services import LlamaService, SunoAPIService
from .music_generate.utils import extract_genre_from_prompt
from .utils.s3_upload import download_and_upload_to_s3, is_suno_url, is_s3_url, upload_image_to_s3
from .services import WikidataService, LRCLIBService, DeezerService, LyricsOvhService

logger = logging.getLogger(__name__)


<<<<<<< HEAD
@shared_task(bind=True)
def test_task(self, message: str = "테스트 메시지", delay_seconds: int = 1):
    """
    RabbitMQ 메트릭 테스트용 간단한 작업
    
    Args:
        message: 출력할 메시지
        delay_seconds: 대기 시간 (초)
    
    Returns:
        작업 완료 메시지
    """
    logger.info(f"테스트 작업 시작: {message}")
    time.sleep(delay_seconds)  # 지정된 시간만큼 대기
    logger.info(f"테스트 작업 완료: {message}")
    return {"status": "success", "message": message, "task_id": self.request.id}


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


@shared_task(bind=True, max_retries=3)
def generate_music_task(self, user_prompt: str, user_id: int = None, make_instrumental: bool = False):
    """
    비동기로 음악을 생성하는 Celery 작업
    
    Args:
        self: Celery task 인스턴스
        user_prompt: 사용자가 입력한 프롬프트
        user_id: 사용자 ID (선택)
        make_instrumental: 반주만 생성할지 여부
        
    Returns:
        생성된 음악 정보 딕셔너리 (artist, album, music, ai_info 포함)
    """
    try:
        # 1. Llama 서비스로 프롬프트 변환
        llama_service = LlamaService()
        english_prompt = llama_service.convert_to_music_prompt(user_prompt)
        
        if not english_prompt:
            raise Exception("프롬프트 변환에 실패했습니다.")
        
        # 2. Suno API로 음악 생성
        suno_service = SunoAPIService()
        music_result = suno_service.generate_music(
            prompt=english_prompt,
            make_instrumental=make_instrumental,
            wait_audio=True,
            timeout=120
        )
        
        if not music_result:
            raise Exception("음악 생성에 실패했습니다.")
        
        # 3. 사용자 확인
        user = None
        artist_name = "AI Artist"
        if user_id:
            try:
                user = Users.objects.get(user_id=user_id, is_deleted=False)
                artist_name = user.nickname if user.nickname else f"User {user.user_id}"
            except Users.DoesNotExist:
                pass
        
        now = timezone.now()
        genre = extract_genre_from_prompt(english_prompt)
        
        # Suno API 응답 매핑
        music_title = (
            music_result.get('title') or 
            music_result.get('name') or 
            music_result.get('song_name') or 
            music_result.get('data', {}).get('title') or
            user_prompt[:50]
        )
        
        audio_url = (
            music_result.get('audio_url') or
            music_result.get('audioUrl') or
            music_result.get('url') or
            music_result.get('audio') or
            music_result.get('data', {}).get('audio_url')
        )
        
        duration = (
            music_result.get('duration') or
            music_result.get('length') or
            music_result.get('data', {}).get('duration')
        )
        
        lyrics = (
            music_result.get('lyrics') or
            music_result.get('lyric') or
            music_result.get('data', {}).get('lyrics')
        )
        
        image_url = (
            music_result.get('imageUrl') or
            music_result.get('image_url') or
            music_result.get('data', {}).get('image_url')
        )
        
        # task_id 추출 (Webhook에서 사용)
        task_id = music_result.get('taskId') or music_result.get('task_id') or 'unknown'
        
        # 4. Artists 모델에 저장
        artist = Artists.objects.create(
            artist_name=artist_name,
            artist_image=image_url,
            created_at=now,
            updated_at=now,
            is_deleted=False
        )
        
        # 5. Albums 모델에 AI 앨범 저장
        album = Albums.objects.create(
            artist=artist,
            album_name=f"AI Generated - {music_title}",
            album_image=image_url,
            created_at=now,
            updated_at=now,
            is_deleted=False
        )
        
        # 6. Music 모델에 저장
        music = Music.objects.create(
            user=user,
            artist=artist,
            album=album,
            music_name=music_title,
            audio_url=audio_url,
            is_ai=True,
            genre=genre,
            duration=duration,
            lyrics=lyrics,
            valence=None,
            arousal=None,
            created_at=now,
            updated_at=now,
            is_deleted=False
        )
        
        # 7. AiInfo 모델에 프롬프트 정보 저장
        # task_id 필드를 직접 설정해야 webhook 태스크에서 찾을 수 있음
        ai_info = AiInfo.objects.create(
            music=music,
            task_id=task_id,  # Webhook 태스크에서 이 필드로 검색함
            input_prompt=f"TaskID: {task_id}\nOriginal: {user_prompt}\nConverted: {english_prompt}",
            created_at=now,
            updated_at=now,
            is_deleted=False
        )
        
        # 8. 결과 반환
        return {
            'success': True,
            'artist': {
                'artist_id': artist.artist_id,
                'artist_name': artist.artist_name,
            },
            'album': {
                'album_id': album.album_id,
                'album_name': album.album_name,
            },
            'music': {
                'music_id': music.music_id,
                'music_name': music.music_name,
                'audio_url': music.audio_url,
                'genre': music.genre,
            },
            'ai_info': {
                'aiinfo_id': ai_info.aiinfo_id,
                'input_prompt': ai_info.input_prompt[:100] + '...',
            },
            'created_at': str(music.created_at)
        }
        
    except Exception as e:
        # 재시도 로직
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=5)
        else:
            return {
                'success': False,
                'error': str(e)
            }


@shared_task(bind=True, max_retries=3)
def upload_suno_audio_to_s3_task(self, music_id: int, suno_audio_url: str):
    """
    Suno에서 생성된 오디오를 S3에 업로드하고 Music 모델의 audio_url을 업데이트합니다.
    
    Args:
        self: Celery task 인스턴스
        music_id: Music 모델의 ID
        suno_audio_url: Suno CDN의 오디오 URL
        
    Returns:
        업데이트된 S3 URL 또는 None (실패 시)
    """
    try:
        # Music 객체 조회
        try:
            music = Music.objects.get(music_id=music_id, is_deleted=False)
        except Music.DoesNotExist:
            logger.error(f"[S3 업로드] Music 객체를 찾을 수 없습니다: music_id={music_id}")
            return None
        
        # 이미 S3 URL이면 스킵
        if is_s3_url(music.audio_url):
            logger.info(f"[S3 업로드] 이미 S3 URL입니다: music_id={music_id}, url={music.audio_url}")
            return music.audio_url
        
        # Suno URL이 아니면 스킵
        if not is_suno_url(suno_audio_url):
            logger.warning(f"[S3 업로드] Suno URL이 아닙니다: music_id={music_id}, url={suno_audio_url}")
            return None
        
        logger.info(f"[S3 업로드] 시작: music_id={music_id}, suno_url={suno_audio_url}")
        
        # 파일명 생성 (music_name 기반)
        file_name = f"{music.music_name.replace(' ', '_')}.mp3" if music.music_name else None
        
        # S3 업로드
        s3_url = download_and_upload_to_s3(
            url=suno_audio_url,
            file_name=file_name,
            content_type='audio/mpeg'
        )
        
        # Music 모델 업데이트
        music.audio_url = s3_url
        music.updated_at = timezone.now()
        music.save()
        
        logger.info(f"[S3 업로드] 완료: music_id={music_id}, s3_url={s3_url}")
        return s3_url
        
    except Exception as e:
        logger.error(f"[S3 업로드] 실패: music_id={music_id}, 오류: {e}")
        
        # 재시도 로직
        if self.request.retries < self.max_retries:
            logger.info(f"[S3 업로드] 재시도: {self.request.retries + 1}/{self.max_retries}")
            raise self.retry(exc=e, countdown=60)  # 1분 후 재시도
        
        logger.error(f"[S3 업로드] 최대 재시도 횟수 초과: music_id={music_id}")
        return None


@shared_task(bind=True, max_retries=3)
def fetch_timestamped_lyrics_task(self, music_id: int, task_id: str, audio_id: str = None):
    """
    타임스탬프 가사를 비동기로 조회하고 Music 모델의 lyrics를 업데이트합니다.
    
    Args:
        self: Celery task 인스턴스
        music_id: Music 모델의 ID
        task_id: Suno task ID
        audio_id: Suno audio ID (선택)
        
    Returns:
        타임스탬프 가사 문자열 또는 None (실패 시)
    """
    try:
        # Music 객체 조회
        try:
            music = Music.objects.get(music_id=music_id, is_deleted=False)
        except Music.DoesNotExist:
            logger.error(f"[타임스탬프 가사] Music 객체를 찾을 수 없습니다: music_id={music_id}")
            return None
        
        logger.info(f"[타임스탬프 가사] 조회 시작: music_id={music_id}, taskId={task_id}, audioId={audio_id}")
        
        # 타임스탬프 가사 조회
        suno_service = SunoAPIService()
        timestamped_lyrics = suno_service.get_timestamped_lyrics(task_id, audio_id)
        
        if timestamped_lyrics:
            # Music 모델 업데이트
            music.lyrics = timestamped_lyrics
            music.updated_at = timezone.now()
            music.save()
            
            logger.info(f"[타임스탬프 가사] 완료: music_id={music_id}, 가사 길이={len(timestamped_lyrics)}")
            return timestamped_lyrics
        else:
            logger.warning(f"[타임스탬프 가사] 조회 실패 또는 가사 없음: music_id={music_id}")
            return None
        
    except Exception as e:
        logger.error(f"[타임스탬프 가사] 실패: music_id={music_id}, 오류: {e}")
        
        # 재시도 로직
        if self.request.retries < self.max_retries:
            logger.info(f"[타임스탬프 가사] 재시도: {self.request.retries + 1}/{self.max_retries}")
            raise self.retry(exc=e, countdown=30)  # 30초 후 재시도
        
        logger.error(f"[타임스탬프 가사] 최대 재시도 횟수 초과: music_id={music_id}")
        return None


@shared_task(bind=True, max_retries=3)
def process_suno_webhook_task(self, webhook_data: dict):
    """
    Suno webhook 데이터를 처리하는 Celery 태스크
    
    webhook은 즉시 200 OK를 반환하고, 실제 DB 업데이트는 이 태스크에서 비동기로 처리합니다.
    
    Args:
        self: Celery task 인스턴스
        webhook_data: Suno webhook에서 받은 전체 데이터
        
    Returns:
        처리 결과 딕셔너리
    """
    try:
        logger.info(f"[Webhook 태스크] 시작: {webhook_data.get('data', {}).get('taskId', 'unknown')}")
        
        # 데이터 구조: data.data.task_id 또는 data.data.taskId
        callback_data = webhook_data.get('data', {})
        callback_type = callback_data.get('callbackType', 'complete')
        
        # task_id 추출
        task_id = callback_data.get('task_id') or callback_data.get('taskId')
        
        if not task_id:
            logger.error(f"[Webhook 태스크] task_id를 찾을 수 없습니다.")
            return {"status": "error", "message": "taskId가 없습니다."}
        
        logger.info(f"[Webhook 태스크] taskId={task_id}, callbackType={callback_type}")
        
        # 음악 데이터 추출
        music_list = callback_data.get('data', [])
        
        if not music_list or len(music_list) == 0:
            if callback_type == 'text':
                logger.info(f"[Webhook 태스크] callbackType='text' - 아직 생성 중")
                return {"status": "pending", "message": "생성 중"}
            logger.warning(f"[Webhook 태스크] 음악 데이터가 없습니다.")
            return {"status": "error", "message": "음악 데이터가 없습니다."}
        
        first_music = music_list[0]
        
        # task_id로 AiInfo 찾기
        ai_info = AiInfo.objects.filter(
            task_id=task_id,
            is_deleted=False
        ).first()
        
        # task_id 필드로 찾지 못하면 input_prompt에서 찾기 (하위 호환성)
        if not ai_info:
            ai_info = AiInfo.objects.filter(
                input_prompt__contains=f"TaskID: {task_id}",
                is_deleted=False
            ).first()
        
        if not ai_info:
            logger.error(f"[Webhook 태스크] taskId={task_id}에 해당하는 AiInfo를 찾을 수 없습니다.")
            return {"status": "error", "message": "해당 작업을 찾을 수 없습니다."}
        
        music = ai_info.music
        
        if not music or music.is_deleted:
            logger.error(f"[Webhook 태스크] Music 객체를 찾을 수 없습니다: music_id={ai_info.music_id}")
            return {"status": "error", "message": "음악 정보를 찾을 수 없습니다."}
        
        logger.info(f"[Webhook 태스크] Music 찾음: music_id={music.music_id}")
        
        # 필수 필드 추출 함수
        def extract_field(data_dict, *keys):
            """여러 키 이름을 시도하여 값 추출"""
            for key in keys:
                value = data_dict.get(key)
                if value and value != '' and value != []:
                    return value
            return None
        
        # 필드 추출
        audio_url_raw = extract_field(first_music, 'audio_url', 'audioUrl', 'url', 'audio', 'audioFile', 'mp3_url', 'mp3Url', 'song_url', 'songUrl', 'source_audio_url', 'sourceAudioUrl')
        image_url_raw = extract_field(first_music, 'image_url', 'imageUrl', 'image', 'cover', 'coverUrl', 'cover_url', 'source_image_url', 'sourceImageUrl')
        title = extract_field(first_music, 'title', 'name', 'song_name', 'songName')
        duration = extract_field(first_music, 'duration', 'length', 'time', 'duration_seconds')
        lyrics = extract_field(first_music, 'lyrics', 'lyric', 'song_lyrics')
        prompt_text = extract_field(first_music, 'prompt', 'description')
        genre = extract_field(first_music, 'genre', 'style', 'music_genre', 'category', 'tags') or music.genre or 'Unknown'
        audio_id = extract_field(first_music, 'audioId', 'audio_id', 'id', 'audioId')
        
        # 빈 문자열 처리
        audio_url = audio_url_raw.strip() if audio_url_raw and isinstance(audio_url_raw, str) else audio_url_raw
        image_url = image_url_raw.strip() if image_url_raw and isinstance(image_url_raw, str) else image_url_raw
        
        if audio_url == '':
            audio_url = None
        if image_url == '':
            image_url = None
        
        # genre 처리: 쉼표로 구분된 경우 첫 번째만 사용
        if genre and ',' in genre:
            genre = genre.split(',')[0].strip()
        
        # genre 길이 제한 (50자)
        if genre and len(genre) > 50:
            genre = genre[:50]
        
        # callbackType이 "text"이고 audio_url이 없으면 아직 생성 중
        if callback_type == 'text' and not audio_url:
            logger.info(f"[Webhook 태스크] callbackType='text', audio_url 없음 - 생성 진행 중")
            return {"status": "pending", "message": "생성 진행 중"}
        
        # Music 업데이트
        now = timezone.now()
        
        # 제목: Suno가 생성한 제목 사용 (유효한 제목인 경우에만)
        # 'AI Generated Song' 등의 기본값은 무시
        invalid_titles = ['AI Generated Song', 'Untitled', 'Unknown', '', None]
        if title and title not in invalid_titles:
            old_title = music.music_name
            music.music_name = title
            logger.info(f"[Webhook 태스크] 제목 업데이트 (Suno 제목): {old_title} → {title}")
        else:
            logger.info(f"[Webhook 태스크] 제목 유지 (Suno 제목 무효): {music.music_name}")
        
        # audio_url: S3 URL이 아닐 때만 업데이트
        if audio_url and not is_s3_url(music.audio_url):
            music.audio_url = audio_url
            logger.info(f"[Webhook 태스크] audio_url 업데이트: {audio_url[:80]}...")
        elif audio_url and is_s3_url(music.audio_url):
            logger.info(f"[Webhook 태스크] audio_url은 이미 S3 URL - 유지")
        
        if duration:
            music.duration = duration
        
        # lyrics: prompt에 가사 패턴이 있으면 fallback으로 사용
        if not lyrics and isinstance(prompt_text, str):
            if ('[Verse' in prompt_text or '[Chorus' in prompt_text or '[Bridge' in prompt_text) or prompt_text.count('\n') > 5:
                lyrics = prompt_text
                logger.info(f"[Webhook 태스크] prompt를 가사로 사용 (길이={len(lyrics)})")
        
        if lyrics:
            music.lyrics = lyrics
        
        if genre:
            music.genre = genre
        
        music.updated_at = now
        music.save()
        
        logger.info(f"[Webhook 태스크] Music 업데이트 완료: music_id={music.music_id}")
        
        # S3 업로드 태스크 호출
        if audio_url and is_suno_url(audio_url) and not is_s3_url(audio_url):
            try:
                logger.info(f"[Webhook 태스크] S3 업로드 태스크 호출: music_id={music.music_id}")
                upload_suno_audio_to_s3_task.delay(music.music_id, audio_url)
            except Exception as e:
                logger.error(f"[Webhook 태스크] S3 업로드 태스크 호출 실패: {e}")
        
        # 타임스탬프 가사 조회 태스크 호출 (가사가 있는 경우에만)
        # is_instrumental 필드가 Music 모델에 없으므로, 가사 존재 여부로 판단
        has_vocals = lyrics and len(lyrics) > 50  # 가사가 50자 이상이면 vocal 곡으로 간주
        if audio_url and task_id and callback_type in ['first', 'complete'] and has_vocals:
            try:
                logger.info(f"[Webhook 태스크] 타임스탬프 가사 조회 태스크 호출")
                fetch_timestamped_lyrics_task.delay(music.music_id, task_id, audio_id)
            except Exception as e:
                logger.error(f"[Webhook 태스크] 타임스탬프 가사 조회 태스크 호출 실패: {e}")
        
        # Artist 이미지 업데이트
        if image_url:
            artist = music.artist
            if artist:
                artist.artist_image = image_url
                artist.updated_at = now
                artist.save()
                logger.info(f"[Webhook 태스크] Artist 이미지 업데이트")
        
        # Album 업데이트
        album = music.album
        if album:
            album.album_name = f"AI Generated - {music.music_name}"
            if image_url:
                album.album_image = image_url
            album.updated_at = now
            album.save()
            logger.info(f"[Webhook 태스크] Album 업데이트")
        
        logger.info(f"[Webhook 태스크] 완료: music_id={music.music_id}")
        
        return {
            "status": "success",
            "music_id": music.music_id,
            "callback_type": callback_type
        }
        
    except Exception as e:
        logger.error(f"[Webhook 태스크] 실패: {e}")
        import traceback
        traceback.print_exc()
        
        # 재시도 로직
        if self.request.retries < self.max_retries:
            logger.info(f"[Webhook 태스크] 재시도: {self.request.retries + 1}/{self.max_retries}")
            raise self.retry(exc=e, countdown=60)
        
        logger.error(f"[Webhook 태스크] 최대 재시도 횟수 초과")
        return {"status": "error", "message": str(e)}


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
    from django.db import transaction
    
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


# ============================================================
# 차트 계산 작업
# ============================================================

@shared_task(name='music.tasks.update_realtime_chart')
def update_realtime_chart():
    """
    실시간 차트 갱신 (10분마다 실행)
    - 최근 3시간 동안의 재생 횟수 집계
    - 상위 100곡 저장
    """
    now = timezone.now()
    start_time = now - timedelta(hours=3)
    
    logger.info(f"[실시간 차트] 집계 시작: {start_time} ~ {now}")
    
    try:
        with transaction.atomic():
            # 1. 최근 3시간 재생 집계
            results = PlayLogs.objects.filter(
                played_at__gte=start_time,
                played_at__lt=now,
                is_deleted=False
            ).values('music_id').annotate(
                play_count=Count('play_log_id')
            ).order_by('-play_count')[:100]
            
            if not results:
                logger.info("[실시간 차트] 집계 데이터 없음")
                return {"status": "no_data", "count": 0}
            
            # 2. 기존 동일 시점 차트 삭제 (중복 방지)
            # chart_date를 분 단위로 정규화 (timezone 제거 - DB가 timestamp 타입)
            chart_date = localtime(now).replace(second=0, microsecond=0, tzinfo=None)
            
            # 3. 순위별 차트 저장
            created_count = 0
            for rank, item in enumerate(results, start=1):
                Charts.objects.create(
                    music_id=item['music_id'],
                    play_count=item['play_count'],
                    chart_date=chart_date,
                    rank=rank,
                    type='realtime',
                    created_at=now,
                    updated_at=now,
                    is_deleted=False
                )
                created_count += 1
            
            logger.info(f"[실시간 차트] 갱신 완료: {created_count}개 항목")
            return {"status": "success", "count": created_count}
            
    except Exception as e:
        logger.error(f"[실시간 차트] 오류: {str(e)}")
        raise


@shared_task(name='music.tasks.update_daily_chart')
def update_daily_chart():
    """
    일일 차트 갱신 (매일 자정 실행)
    - 어제 하루 동안의 재생 횟수 집계
    - 전체 곡 상위 100곡 저장
    """
    now = timezone.now()
    yesterday = now - timedelta(days=1)
    yesterday_start = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday_end = yesterday_start + timedelta(days=1)
    
    logger.info(f"[일일 차트] 집계 시작: {yesterday_start} ~ {yesterday_end}")
    
    try:
        with transaction.atomic():
            # 1. 어제 전체 재생 집계
            results = PlayLogs.objects.filter(
                played_at__gte=yesterday_start,
                played_at__lt=yesterday_end,
                is_deleted=False
            ).values('music_id').annotate(
                play_count=Count('play_log_id')
            ).order_by('-play_count')[:100]
            
            if not results:
                logger.info("[일일 차트] 집계 데이터 없음")
                return {"status": "no_data", "count": 0}
            
            # 2. 순위별 차트 저장
            # timezone 제거 (DB가 timestamp 타입)
            chart_date = localtime(yesterday_start).replace(tzinfo=None)
            created_count = 0
            
            for rank, item in enumerate(results, start=1):
                Charts.objects.create(
                    music_id=item['music_id'],
                    play_count=item['play_count'],
                    chart_date=chart_date,
                    rank=rank,
                    type='daily',
                    created_at=now,
                    updated_at=now,
                    is_deleted=False
                )
                created_count += 1
            
            logger.info(f"[일일 차트] 갱신 완료: {created_count}개 항목")
            return {"status": "success", "count": created_count}
            
    except Exception as e:
        logger.error(f"[일일 차트] 오류: {str(e)}")
        raise


@shared_task(name='music.tasks.update_ai_chart')
def update_ai_chart():
    """
    AI 차트 갱신 (매일 자정 실행)
    - 어제 하루 동안의 AI 곡 재생 횟수 집계
    - AI 곡만 상위 100곡 저장
    """
    now = timezone.now()
    yesterday = now - timedelta(days=1)
    yesterday_start = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday_end = yesterday_start + timedelta(days=1)
    
    logger.info(f"[AI 차트] 집계 시작: {yesterday_start} ~ {yesterday_end}")
    
    try:
        with transaction.atomic():
            # 1. 어제 AI 곡 재생 집계
            results = PlayLogs.objects.filter(
                played_at__gte=yesterday_start,
                played_at__lt=yesterday_end,
                is_deleted=False,
                music__is_ai=True,  # AI 곡만
                music__is_deleted=False
            ).values('music_id').annotate(
                play_count=Count('play_log_id')
            ).order_by('-play_count')[:100]
            
            if not results:
                logger.info("[AI 차트] 집계 데이터 없음")
                return {"status": "no_data", "count": 0}
            
            # 2. 순위별 차트 저장
            # timezone 제거 (DB가 timestamp 타입)
            chart_date = localtime(yesterday_start).replace(tzinfo=None)
            created_count = 0
            
            for rank, item in enumerate(results, start=1):
                Charts.objects.create(
                    music_id=item['music_id'],
                    play_count=item['play_count'],
                    chart_date=chart_date,
                    rank=rank,
                    type='ai',
                    created_at=now,
                    updated_at=now,
                    is_deleted=False
                )
                created_count += 1
            
            logger.info(f"[AI 차트] 갱신 완료: {created_count}개 항목")
            return {"status": "success", "count": created_count}
            
    except Exception as e:
        logger.error(f"[AI 차트] 오류: {str(e)}")
        raise


# ============================================================
# 데이터 정리 작업
# ============================================================

@shared_task(name='music.tasks.cleanup_old_playlogs')
def cleanup_old_playlogs():
    """
    오래된 재생 기록 삭제 (매일 새벽 2시 실행)
    - 90일 이전 재생 기록 물리 삭제
    """
    now = timezone.now()
    cutoff = now - timedelta(days=90)
    
    logger.info(f"[PlayLogs 정리] 삭제 기준일: {cutoff}")
    
    try:
        deleted_count, _ = PlayLogs.objects.filter(
            played_at__lt=cutoff
        ).delete()
        
        logger.info(f"[PlayLogs 정리] 삭제 완료: {deleted_count}개")
        return {"status": "success", "deleted_count": deleted_count}
        
    except Exception as e:
        logger.error(f"[PlayLogs 정리] 오류: {str(e)}")
        raise


@shared_task(name='music.tasks.cleanup_old_realtime_charts')
def cleanup_old_realtime_charts():
    """
    오래된 실시간 차트 삭제 (매일 새벽 3시 실행)
    - 7일 이전 실시간 차트 물리 삭제
    - daily, ai 차트는 영구 보관
    """
    now = timezone.now()
    cutoff = now - timedelta(days=7)
    
    logger.info(f"[실시간 차트 정리] 삭제 기준일: {cutoff}")
    
    try:
        deleted_count, _ = Charts.objects.filter(
            type='realtime',
            chart_date__lt=cutoff
        ).delete()
        
        logger.info(f"[실시간 차트 정리] 삭제 완료: {deleted_count}개")
        return {"status": "success", "deleted_count": deleted_count}
        
    except Exception as e:
        logger.error(f"[실시간 차트 정리] 오류: {str(e)}")
        raise
