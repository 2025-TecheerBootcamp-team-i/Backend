"""
AI 음악 생성 관련 Celery 작업 (Suno API)
"""
import logging
from celery import shared_task
from django.utils import timezone

from ..models import Music, AiInfo, Users, Artists, Albums
from ..music_generate.services import LlamaService, SunoAPIService
from ..music_generate.utils import extract_genre_from_prompt
from ..utils.s3_upload import download_and_upload_to_s3, is_suno_url, is_s3_url, upload_image_to_s3

logger = logging.getLogger(__name__)


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
            
            # 앨범 이미지를 S3로 업로드 (S3 URL이 아닐 때만)
            if image_url and not is_s3_url(image_url):
                try:
                    logger.info(f"[Webhook 태스크] 앨범 이미지 S3 업로드 시작: album_id={album.album_id}")
                    resized_urls = upload_image_to_s3(
                        image_url=image_url,
                        image_type='albums',
                        entity_id=album.album_id,
                        entity_name=album.album_name
                    )
                    # 원본 이미지 URL 저장 (Lambda가 리사이징한 사각형 이미지는 image_square 필드에 자동 저장됨)
                    album.album_image = resized_urls.get('original')
                    album.image_square = resized_urls.get('image_square')  # 220x220
                    logger.info(f"[Webhook 태스크] 앨범 이미지 S3 업로드 완료: album_id={album.album_id}")
                except Exception as upload_error:
                    # S3 업로드 실패 시 원본 URL이라도 저장
                    logger.warning(f"[Webhook 태스크] 앨범 이미지 S3 업로드 실패, 원본 URL 저장: {upload_error}")
                    album.album_image = image_url
            elif image_url:
                # 이미 S3 URL이면 그대로 저장
                album.album_image = image_url
                logger.info(f"[Webhook 태스크] 앨범 이미지가 이미 S3 URL - 유지: album_id={album.album_id}")
            
            album.updated_at = now
            album.save()
            logger.info(f"[Webhook 태스크] Album 업데이트 완료: album_id={album.album_id}")
        
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
