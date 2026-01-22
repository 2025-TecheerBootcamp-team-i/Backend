"""
AI 음악 생성 비즈니스 로직 서비스

이 모듈은 AI 음악 생성의 핵심 비즈니스 로직을 담당합니다:
- Llama를 통한 프롬프트 변환
- Suno API를 통한 음악 생성
- DB에 Music, Artist, Album, AiInfo 저장
- S3 업로드 및 가사 조회 비동기 작업 큐잉

View에서는 이 서비스를 호출하고 HTTP 응답만 생성합니다.
"""
import os
import json
import traceback
from typing import Dict, Optional, Tuple
from django.utils import timezone
from django.db import transaction

from music.models import Music, AiInfo, Users, Artists, Albums
from music.music_generate.services import LlamaService, SunoAPIService
from music.music_generate.utils import extract_genre_from_prompt
from music.music_generate.exceptions import (
    SunoAPIError, 
    SunoCreditInsufficientError, 
    SunoAuthenticationError
)


class AiMusicGenerationService:
    """
    AI 음악 생성 비즈니스 로직을 담당하는 서비스 클래스
    """
    
    def __init__(self):
        self.llama_service = LlamaService()
        self.suno_service = SunoAPIService()
    
    def generate_music(
        self, 
        user_prompt: str, 
        user_id: Optional[int] = None,
        make_instrumental: bool = False,
        timeout: int = 120
    ) -> Tuple[Music, Artists, Albums, AiInfo]:
        """
        AI 음악 생성 메인 로직
        
        Args:
            user_prompt: 사용자가 입력한 프롬프트 (예: "여름의 장미")
            user_id: 사용자 ID (선택)
            make_instrumental: 반주만 생성할지 여부
            timeout: Suno API 대기 시간 (초)
            
        Returns:
            (Music, Artists, Albums, AiInfo) 튜플
            
        Raises:
            SunoCreditInsufficientError: 크레딧 부족
            SunoAuthenticationError: 인증 실패
            SunoAPIError: 기타 Suno API 오류
            Exception: 기타 예외
        """
        # 1. Llama로 음악 파라미터 생성
        music_params = self._generate_music_params(user_prompt)
        llama_style = music_params.get('style', 'K-Pop')
        llama_prompt = music_params.get('prompt', '')
        
        # 2. Suno API로 음악 생성
        combined_prompt = llama_prompt or user_prompt
        combined_prompt = self._validate_prompt_length(combined_prompt)
        
        print(f"[통합 프롬프트] 길이: {len(combined_prompt)}자")
        print(f"[통합 프롬프트] 내용: {combined_prompt}")
        
        music_result = self._generate_with_suno(
            prompt=combined_prompt,
            make_instrumental=make_instrumental,
            timeout=timeout
        )
        
        # 3. 음악 데이터 추출
        music_data = self._extract_music_data(
            music_result=music_result,
            user_prompt=user_prompt,
            llama_style=llama_style,
            llama_prompt=llama_prompt
        )
        
        # 4. 사용자 확인
        user = self._get_user_if_exists(user_id)
        artist_name = self._get_artist_name(user)
        
        # 5. DB 저장 (원자적 트랜잭션)
        music, artist, album, ai_info = self._save_to_database(
            music_data=music_data,
            user=user,
            artist_name=artist_name,
            user_prompt=user_prompt,
            llama_style=llama_style,
            llama_prompt=llama_prompt
        )
        
        # 6. 비동기 작업 큐잉 (타임스탬프 가사, S3 업로드)
        self._queue_async_tasks(
            music=music,
            make_instrumental=make_instrumental,
            task_id=music_data['task_id'],
            audio_id=music_data.get('audio_id'),
            audio_url=music_data.get('audio_url')
        )
        
        print(f"[DB 저장 완료] ✅ 모든 데이터 저장 성공!")
        print(f"[DB 저장 완료] music_id={music.music_id}, artist_id={artist.artist_id}, album_id={album.album_id}")
        
        return music, artist, album, ai_info
    
    def _generate_music_params(self, user_prompt: str) -> Dict:
        """Llama 서비스로 음악 파라미터 생성"""
        music_params = self.llama_service.generate_music_params(user_prompt)
        
        if not music_params:
            raise Exception("프롬프트 변환에 실패했습니다. Llama 서버 연결을 확인하세요.")
        
        llama_style = music_params.get('style', 'K-Pop')
        llama_prompt = music_params.get('prompt', '')
        
        print(f"[Llama 결과] style: {llama_style}")
        print(f"[Llama 결과] prompt: {llama_prompt}")
        
        return music_params
    
    def _validate_prompt_length(self, prompt: str, max_length: int = 450) -> str:
        """프롬프트 길이 검증 및 자르기"""
        if len(prompt) > max_length:
            print(f"[경고] 프롬프트가 {max_length}자를 초과합니다! ({len(prompt)}자)")
            return prompt[:max_length]
        return prompt
    
    def _generate_with_suno(
        self, 
        prompt: str, 
        make_instrumental: bool,
        timeout: int
    ) -> Dict:
        """Suno API로 음악 생성"""
        music_result = self.suno_service.generate_music(
            prompt=prompt,
            style=None,  # Non-custom Mode
            title=None,  # Non-custom Mode
            make_instrumental=make_instrumental,
            wait_audio=True,
            timeout=timeout
        )
        
        if not music_result:
            raise SunoAPIError("음악 생성 요청에 실패했습니다. Suno API 연결을 확인하세요.")
        
        # Polling 실패 경고
        if music_result.get('status') == 'pending' or not music_result.get('audioUrl'):
            print(f"[경고] Polling 실패 또는 타임아웃, 기본 데이터만 저장 (taskId: {music_result.get('taskId')})")
            print(f"[경고] webhook으로 나중에 업데이트될 수 있습니다: {os.getenv('SUNO_CALLBACK_URL')}")
        
        # 응답 로깅
        print(f"[음악 생성 완료] Suno API 전체 응답 (JSON): {json.dumps(music_result, indent=2, ensure_ascii=False)[:2000]}")
        
        return music_result
    
    def _extract_music_data(
        self,
        music_result: Dict,
        user_prompt: str,
        llama_style: str,
        llama_prompt: str
    ) -> Dict:
        """
        Suno API 응답에서 필요한 데이터 추출
        
        다양한 응답 형식을 지원:
        1. sunoData 리스트
        2. 직접 필드 접근
        3. Polling 실패 시 기본 데이터
        """
        def extract_field(data, *keys):
            """여러 키 이름을 시도하여 값 추출"""
            for key in keys:
                value = data.get(key)
                if value:
                    return value
            return None
        
        # 응답 형식 1: sunoData 리스트
        suno_data = music_result.get('sunoData', [])
        if isinstance(suno_data, list) and len(suno_data) > 0:
            print(f"[데이터 추출] sunoData 리스트 형식 발견 (길이: {len(suno_data)})")
            first_song = suno_data[0]
            audio_url = extract_field(first_song, 'audioUrl', 'audio_url', 'url', 'audio', 'audioFile')
            music_title = user_prompt[:50]
            duration = extract_field(first_song, 'duration', 'length', 'time', 'duration_seconds')
            lyrics = extract_field(first_song, 'lyrics', 'lyric', 'text', 'song_lyrics')
            image_url = extract_field(first_song, 'imageUrl', 'image_url', 'image', 'cover', 'cover_url')
            api_genre = extract_field(first_song, 'genre', 'style', 'music_genre', 'category')
            audio_id = extract_field(first_song, 'audioId', 'audio_id', 'id')
        
        # 응답 형식 2: 직접 필드 접근
        elif isinstance(music_result, dict):
            print(f"[데이터 추출] 직접 필드 접근 형식")
            audio_url = extract_field(music_result, 'audioUrl', 'audio_url', 'url', 'audio', 'audioFile')
            music_title = user_prompt[:50]
            duration = extract_field(music_result, 'duration', 'length', 'time', 'duration_seconds')
            lyrics = extract_field(music_result, 'lyrics', 'lyric', 'text', 'song_lyrics')
            image_url = extract_field(music_result, 'imageUrl', 'image_url', 'image', 'cover', 'cover_url')
            api_genre = extract_field(music_result, 'genre', 'style', 'music_genre', 'category') or llama_style
            audio_id = extract_field(music_result, 'audioId', 'audio_id', 'id')
        
        # 응답 형식 3: 알 수 없는 형식
        else:
            print(f"[데이터 추출] ⚠️ 알 수 없는 응답 형식: {type(music_result)}")
            audio_url = None
            duration = None
            lyrics = None
            image_url = None
            api_genre = llama_style
            audio_id = None
            music_title = user_prompt[:50]
        
        task_id = music_result.get('taskId', 'unknown')
        
        # 장르 결정 및 정리
        genre = api_genre or llama_style or extract_genre_from_prompt(llama_prompt)
        genre = self._clean_genre(genre)
        
        print(f"[음악 생성 완료] 추출된 데이터:")
        print(f"  - task_id: {task_id}")
        print(f"  - audio_id: {audio_id}")
        print(f"  - audio_url: {audio_url}")
        print(f"  - title: {music_title}")
        print(f"  - duration: {duration}")
        print(f"  - lyrics: {lyrics[:100] if lyrics else 'None'}...")
        print(f"  - image_url: {image_url}")
        print(f"  - genre: {genre}")
        
        return {
            'task_id': task_id,
            'audio_id': audio_id,
            'audio_url': audio_url,
            'title': music_title,
            'duration': duration,
            'lyrics': lyrics,
            'image_url': image_url,
            'genre': genre,
        }
    
    def _clean_genre(self, genre: Optional[str]) -> str:
        """장르 문자열 정리 (쉼표 분리, 길이 제한)"""
        if not genre:
            return 'K-Pop'
        
        # 쉼표로 구분된 경우 첫 번째만 사용
        if ',' in genre:
            original_genre = genre
            genre = genre.split(',')[0].strip()
            print(f"[DB 저장] genre에서 첫 번째 값만 사용: 원본: {original_genre} → 저장: {genre}")
        
        # 길이 제한 (max_length=50)
        if len(genre) > 50:
            original_genre = genre
            genre = genre[:50]
            print(f"[DB 저장] 경고: genre가 50자를 초과하여 잘렸습니다. 원본: {original_genre[:100]}... → 저장: {genre}")
        
        return genre
    
    def _get_user_if_exists(self, user_id: Optional[int]) -> Optional[Users]:
        """사용자 ID로 Users 객체 조회 (존재하지 않으면 None)"""
        if not user_id:
            return None
        
        try:
            user = Users.objects.get(user_id=user_id, is_deleted=False)
            print(f"[DB 저장] 사용자 확인: user_id={user_id}")
            return user
        except Users.DoesNotExist:
            print(f"[DB 저장] 경고: user_id={user_id}에 해당하는 사용자를 찾을 수 없습니다.")
            return None
        except Exception as e:
            print(f"[DB 저장] 오류: 사용자 조회 중 예외 발생: {e}")
            return None
    
    def _get_artist_name(self, user: Optional[Users]) -> str:
        """아티스트 이름 결정 (사용자 닉네임 또는 기본값)"""
        if user and user.nickname:
            return user.nickname
        elif user:
            return f"User {user.user_id}"
        else:
            return "AI Artist"
    
    @transaction.atomic
    def _save_to_database(
        self,
        music_data: Dict,
        user: Optional[Users],
        artist_name: str,
        user_prompt: str,
        llama_style: str,
        llama_prompt: str
    ) -> Tuple[Music, Artists, Albums, AiInfo]:
        """
        DB에 Music, Artist, Album, AiInfo 저장 (원자적 트랜잭션)
        
        Returns:
            (Music, Artists, Albums, AiInfo) 튜플
        """
        from music.utils.s3_upload import upload_image_to_s3, is_suno_url
        
        now = timezone.now()
        
        # Artists 저장 (먼저 생성하여 ID 확보)
        print(f"[DB 저장] Artists 저장 시작: artist_name={artist_name}")
        artist = Artists.objects.create(
            artist_name=artist_name,
            artist_image=None,  # 이미지는 나중에 업데이트
            created_at=now,
            updated_at=now,
            is_deleted=False
        )
        print(f"[DB 저장] ✅ Artists 저장 완료: artist_id={artist.artist_id}")
        
        # Albums 저장 (먼저 생성하여 ID 확보)
        album_name = f"AI Generated - {music_data['title']}"
        print(f"[DB 저장] Albums 저장 시작: album_name={album_name}")
        album = Albums.objects.create(
            artist=artist,
            album_name=album_name,
            album_image=None,  # 이미지는 나중에 업데이트
            created_at=now,
            updated_at=now,
            is_deleted=False
        )
        print(f"[DB 저장] ✅ Albums 저장 완료: album_id={album.album_id}")
        
        # Suno 이미지 URL을 S3에 업로드 및 리사이징 (CORS 문제 해결)
        album_image_url = music_data['image_url']
        if album_image_url and is_suno_url(album_image_url):
            try:
                print(f"[S3 이미지 업로드] Suno 이미지를 S3에 업로드 중: {album_image_url}")
                # 실제 album_id 사용하여 S3 업로드 및 리사이징
                resized_urls = upload_image_to_s3(
                    image_url=album_image_url,
                    image_type='albums',
                    entity_id=album.album_id,
                    entity_name=f"ai_album_{user_prompt[:20]}"
                )
                print(f"[S3 이미지 업로드] ✅ S3 업로드 완료")
                print(f"  - original: {resized_urls.get('original', 'N/A')[:60]}...")
                print(f"  - image_square (220x220): {resized_urls.get('image_square', 'N/A')[:60]}...")
                print(f"  - image_large_square (360x360): {resized_urls.get('image_large_square', 'N/A')[:60]}...")
                
                # Album 이미지 URL 업데이트
                album.album_image = resized_urls.get('original', album_image_url)
                album.image_square = resized_urls.get('image_square')
                album.image_large_square = resized_urls.get('image_large_square')
                album.save(update_fields=['album_image', 'image_square', 'image_large_square', 'updated_at'])
                print(f"[DB 저장] ✅ Albums 이미지 URL 업데이트 완료")
                
                # Artist 이미지도 동일하게 설정
                artist.artist_image = resized_urls.get('original', album_image_url)
                artist.save(update_fields=['artist_image', 'updated_at'])
                print(f"[DB 저장] ✅ Artists 이미지 URL 업데이트 완료")
                
            except Exception as e:
                print(f"[S3 이미지 업로드] ⚠️ S3 업로드 실패, 원본 URL 사용: {e}")
                traceback.print_exc()
                # S3 업로드 실패 시 원본 URL 사용 (fallback)
                album.album_image = album_image_url
                album.save(update_fields=['album_image', 'updated_at'])
                artist.artist_image = album_image_url
                artist.save(update_fields=['artist_image', 'updated_at'])
        else:
            # Suno URL이 아니거나 이미지가 없는 경우
            if album_image_url:
                album.album_image = album_image_url
                album.save(update_fields=['album_image', 'updated_at'])
                artist.artist_image = album_image_url
                artist.save(update_fields=['artist_image', 'updated_at'])
                print(f"[DB 저장] 원본 이미지 URL 사용: {album_image_url[:60]}...")
        
        # Music 저장
        print(f"[DB 저장] Music 저장 시작:")
        print(f"  - music_name: {music_data['title']}")
        print(f"  - audio_url: {music_data['audio_url']}")
        print(f"  - duration: {music_data['duration']}")
        print(f"  - genre: {music_data['genre']}")
        print(f"  - lyrics 길이: {len(music_data['lyrics']) if music_data['lyrics'] else 0}")
        
        music = Music.objects.create(
            user=user,
            artist=artist,
            album=album,
            music_name=music_data['title'],
            audio_url=music_data['audio_url'],
            is_ai=True,
            genre=music_data['genre'],
            duration=music_data['duration'],
            lyrics=music_data['lyrics'],
            valence=None,
            arousal=None,
            itunes_id=None,
            created_at=now,
            updated_at=now,
            is_deleted=False
        )
        print(f"[DB 저장] ✅ Music 저장 완료: music_id={music.music_id}")
        
        # AiInfo 저장
        print(f"[DB 저장] AiInfo 저장 시작: task_id={music_data['task_id']}")
        input_prompt_text = f"TaskID: {music_data['task_id']}\nOriginal: {user_prompt}\nStyle: {llama_style}\nPrompt: {llama_prompt}"
        ai_info = AiInfo.objects.create(
            music=music,
            task_id=music_data['task_id'],
            input_prompt=input_prompt_text,
            created_at=now,
            updated_at=now,
            is_deleted=False
        )
        print(f"[DB 저장] ✅ AiInfo 저장 완료: aiinfo_id={ai_info.aiinfo_id}")
        
        return music, artist, album, ai_info
    
    def _queue_async_tasks(
        self,
        music: Music,
        make_instrumental: bool,
        task_id: str,
        audio_id: Optional[str],
        audio_url: Optional[str]
    ):
        """비동기 작업 큐잉 (타임스탬프 가사, S3 업로드)"""
        from music.tasks import upload_suno_audio_to_s3_task, fetch_timestamped_lyrics_task
        from music.utils.s3_upload import is_suno_url, is_s3_url
        
        # 타임스탬프 가사 조회
        if not make_instrumental and task_id and task_id != 'unknown' and audio_url:
            try:
                print(f"[타임스탬프 가사] 조회 태스크 호출: taskId={task_id}, audioId={audio_id}")
                fetch_timestamped_lyrics_task.delay(music.music_id, task_id, audio_id)
                print(f"[타임스탬프 가사] ✅ 태스크 큐에 추가됨 (비동기 처리)")
            except Exception as e:
                print(f"[타임스탬프 가사] 태스크 호출 실패 (치명적이지 않음): {e}")
        
        # S3 업로드
        if audio_url and is_suno_url(audio_url) and not is_s3_url(audio_url):
            try:
                print(f"[S3 업로드] 태스크 호출: music_id={music.music_id}, suno_url={audio_url}")
                upload_suno_audio_to_s3_task.delay(music.music_id, audio_url)
                print(f"[S3 업로드] ✅ 태스크 큐에 추가됨 (비동기 처리)")
            except Exception as e:
                print(f"[S3 업로드] 태스크 호출 실패 (치명적이지 않음): {e}")


class AiMusicServiceError(Exception):
    """AI 음악 생성 서비스 기본 예외"""
    pass


class PromptTransformationError(AiMusicServiceError):
    """프롬프트 변환 실패 예외"""
    pass


class MusicGenerationError(AiMusicServiceError):
    """음악 생성 실패 예외"""
    pass
