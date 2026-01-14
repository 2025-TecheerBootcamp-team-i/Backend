"""
Celery 비동기 작업 정의
"""
import os
from typing import Optional

from celery import shared_task
from django.conf import settings
from django.utils import timezone
from .models import Music, AiInfo, Users, Artists, Albums
from .music_generate.services import LlamaService, SunoAPIService
from .music_generate.utils import extract_genre_from_prompt
from .utils import download_and_upload_to_s3


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
        ai_info = AiInfo.objects.create(
            music=music,
            input_prompt=f"Original: {user_prompt}\nConverted: {english_prompt}",
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


def _is_s3_configured() -> bool:
    """
    S3 설정이 되어있는지 확인합니다.
    - settings.py에서 AWS_STORAGE_BUCKET_NAME이 있으면 S3 사용으로 간주
    """
    return bool(getattr(settings, 'AWS_STORAGE_BUCKET_NAME', ''))


def _is_s3_url(url: Optional[str]) -> bool:
    """
    이미 S3 URL인지 판단합니다. (멱등성/중복 업로드 방지용)
    """
    if not url:
        return False
    custom_domain = getattr(settings, 'AWS_S3_CUSTOM_DOMAIN', '')
    return bool(custom_domain) and custom_domain in url


@shared_task(
    bind=True,
    max_retries=5,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=60,
    retry_jitter=True,
)
def upload_suno_audio_to_s3_task(self, music_id: int, suno_url: str, file_name: str = None):
    """
    Suno에서 생성된 MP3를 다운로드하여 S3에 업로드하고, 성공 시 Music.audio_url을 S3 URL로 교체합니다.

    - Celery 비동기 실행
    - 멱등성: 이미 audio_url이 S3면 스킵
    - S3 미설정이면 스킵
    """
    if not _is_s3_configured():
        return {'success': False, 'skipped': True, 'reason': 'S3_NOT_CONFIGURED'}

    if not suno_url:
        return {'success': False, 'skipped': True, 'reason': 'SUNO_URL_EMPTY'}

    music = Music.objects.filter(music_id=music_id, is_deleted=False).first()
    if not music:
        return {'success': False, 'skipped': True, 'reason': 'MUSIC_NOT_FOUND'}

    # 이미 S3로 교체된 경우 스킵
    if _is_s3_url(music.audio_url):
        return {'success': True, 'skipped': True, 'reason': 'ALREADY_S3', 'audio_url': music.audio_url}

    # 파일명 기본값: music_id 기반
    if not file_name:
        file_name = f'music_{music_id}.mp3'

    # S3 업로드 (다운로드→업로드)
    s3_url = download_and_upload_to_s3(suno_url, file_name=file_name)

    # 업로드 성공 시 DB 업데이트
    music.audio_url = s3_url
    music.updated_at = timezone.now()
    music.save(update_fields=['audio_url', 'updated_at'])

    return {'success': True, 'music_id': music_id, 'audio_url': s3_url}
