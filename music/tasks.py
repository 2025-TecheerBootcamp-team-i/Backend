"""
Celery 비동기 작업 정의
"""
from celery import shared_task
from django.utils import timezone
from .models import Music, AiInfo, Users, Artists, Albums
from .services import LlamaService, SunoAPIService
from .music_generate.utils import extract_genre_from_prompt


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
