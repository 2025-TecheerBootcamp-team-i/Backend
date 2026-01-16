import os
import json
import traceback

from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.shortcuts import render
from rest_framework import status
from rest_framework.decorators import api_view, parser_classes, authentication_classes, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from drf_spectacular.utils import extend_schema
from ..models import Music, AiInfo, Users, Artists, Albums
# 레거시 serializers는 legacy_serializers 모듈에서 직접 import
from ..legacy_serializers import (
    MusicGenerateRequestSerializer,
    MusicGenerateResponseSerializer,
    TaskStatusSerializer
)
# Services는 music_generate 모듈에서 직접 import
from ..music_generate.services import LlamaService, SunoAPIService
from ..parsers import FlexibleJSONParser
from ..music_generate.utils import extract_genre_from_prompt
from ..tasks import upload_suno_audio_to_s3_task, fetch_timestamped_lyrics_task
from ..utils.s3_upload import is_suno_url, is_s3_url


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
@parser_classes([FlexibleJSONParser])
@extend_schema(
    summary="AI 음악 생성 (동기) - 웹 페이지용",
    description="Suno API를 사용한 AI 음악 생성 (동기 처리, 완료까지 대기) - 웹 페이지 템플릿에서 사용",
    tags=['AI 음악 생성 (웹 페이지)']
)
def generate_music(request):
    """
    AI 음악 생성 API 엔드포인트
    
    POST /api/music/generate/
    
    지원하는 입력 형식:
    1. JSON: {"prompt": "여름의 장미", "user_id": 1, "make_instrumental": false}
    2. 단순 텍스트: 여름의 장미
    
    Response:
    {
        "music_id": 123,
        "music_name": "Summer Roses",
        "audio_url": "https://cdn.suno.ai/xxxxx.mp3",
        "is_ai": true,
        "artist": {...},
        "album": {...},
        "ai_info": [...],
        "created_at": "2026-01-13T10:30:00Z"
    }
    """
    # 커스텀 파서가 자동으로 처리 (FlexibleJSONParser)
    # 단순 텍스트는 {"prompt": "텍스트"} 형태로 변환됨
    data = request.data
    
    # Serializer로 검증
    serializer = MusicGenerateRequestSerializer(data=data)
    if not serializer.is_valid():
        return Response(
            {"error": "입력 데이터가 유효하지 않습니다.", "details": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    validated_data = serializer.validated_data
    user_prompt = validated_data['prompt']
    user_id = validated_data.get('user_id')
    make_instrumental = validated_data.get('make_instrumental', False)
    
    try:
        # 1. Llama 서비스로 음악 파라미터 생성 (title, style, prompt)
        llama_service = LlamaService()
        music_params = llama_service.generate_music_params(user_prompt)
        
        if not music_params:
            return Response(
                {"error": "프롬프트 변환에 실패했습니다. Llama 서버 연결을 확인하세요."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        
        # Llama가 생성한 파라미터 추출
        # 제목은 이제 Llama가 만든 것을 쓰지 않고, 사용자가 입력한 내용을 그대로 사용
        llama_title = music_params.get('title', user_prompt[:50])
        llama_style = music_params.get('style', 'K-Pop')
        llama_prompt = music_params.get('prompt', '')
        
        print(f"[Llama 결과] title: {llama_title}")
        print(f"[Llama 결과] style: {llama_style}")
        print(f"[Llama 결과] prompt: {llama_prompt}")
        
        # Suno Description Mode용 최종 프롬프트 생성
        # 요구사항: Title / Style 텍스트를 제거하고, content(프롬프트)에
        # "사용자 입력의 영어 번역"만 넣어준다.
        # 예) "나의 꽃이면" -> "my flower"
        combined_prompt = llama_prompt or user_prompt
        
        # 프롬프트 길이 확인 (450자 미만으로 제한)
        if len(combined_prompt) > 450:
            print(f"[경고] 프롬프트가 450자를 초과합니다! ({len(combined_prompt)}자)")
            combined_prompt = combined_prompt[:450]
        
        # 프롬프트 전체 내용 출력 (최대 450자이므로 전체 출력)
        print(f"[통합 프롬프트] 길이: {len(combined_prompt)}자")
        print(f"[통합 프롬프트] 내용: {combined_prompt}")
        
        # 2. Suno API로 음악 생성 (Polling 방식)
        suno_service = SunoAPIService()
        music_result = suno_service.generate_music(
            prompt=combined_prompt,  # 제목, 스타일, 프롬프트 모두 포함
            style=None,  # Non-custom Mode에서는 style 필드 사용 안 함
            title=None,  # Non-custom Mode에서는 title 필드도 사용 안 함 (프롬프트에 포함)
            make_instrumental=make_instrumental,
            wait_audio=True,
            timeout=120  # 타임아웃 단축: 300초 → 120초 (2분)
        )
        
        if not music_result:
            return Response(
                {"error": "음악 생성 요청에 실패했습니다. Suno API 연결을 확인하세요."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        
        # Polling 실패 시에도 기본 데이터는 있음 (taskId 포함)
        # webhook으로 나중에 업데이트될 수 있도록 저장
        if music_result.get('status') == 'pending' or not music_result.get('audioUrl'):
            print(f"[경고] Polling 실패 또는 타임아웃, 기본 데이터만 저장 (taskId: {music_result.get('taskId')})")
            print(f"[경고] webhook으로 나중에 업데이트될 수 있습니다: {os.getenv('SUNO_CALLBACK_URL')}")
        
        # 전체 응답 로깅 (상세 디버깅용)
        print(f"[음악 생성 완료] Suno API 전체 응답 (JSON): {json.dumps(music_result, indent=2, ensure_ascii=False)[:2000]}")
        print(f"[음악 생성 완료] Suno API 응답 타입: {type(music_result)}")
        print(f"[음악 생성 완료] Suno API 응답 키: {list(music_result.keys()) if isinstance(music_result, dict) else 'Not a dict'}")
        
        # Suno API 응답에서 데이터 추출 (다양한 필드명 및 형식 지원)
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
            # 제목은 Suno가 생성한 제목을 우선 사용하고, 없으면 사용자 입력을 fallback으로 사용
            music_title = extract_field(first_song, 'title', 'name', 'song_name', 'songName') or user_prompt[:50]
            duration = extract_field(first_song, 'duration', 'length', 'time', 'duration_seconds')
            lyrics = extract_field(first_song, 'lyrics', 'lyric', 'text', 'song_lyrics')
            image_url = extract_field(first_song, 'imageUrl', 'image_url', 'image', 'cover', 'cover_url', 'cover_url')
            api_genre = extract_field(first_song, 'genre', 'style', 'music_genre', 'category')
            valence = extract_field(first_song, 'valence', 'emotion_valence')
            arousal = extract_field(first_song, 'arousal', 'emotion_arousal')
            audio_id = extract_field(first_song, 'audioId', 'audio_id', 'id', 'audioId')
        
        # 응답 형식 2: 직접 필드 접근 (Polling 실패 시 기본 데이터 포함)
        elif isinstance(music_result, dict):
            print(f"[데이터 추출] 직접 필드 접근 형식")
            audio_url = extract_field(music_result, 'audioUrl', 'audio_url', 'url', 'audio', 'audioFile')
            # 제목은 Suno가 생성한 제목을 우선 사용하고, 없으면 사용자 입력을 fallback으로 사용
            music_title = extract_field(music_result, 'title', 'name', 'song_name', 'songName') or music_result.get('title') or user_prompt[:50]
            duration = extract_field(music_result, 'duration', 'length', 'time', 'duration_seconds')
            lyrics = extract_field(music_result, 'lyrics', 'lyric', 'text', 'song_lyrics')
            image_url = extract_field(music_result, 'imageUrl', 'image_url', 'image', 'cover', 'cover_url')
            api_genre = extract_field(music_result, 'genre', 'style', 'music_genre', 'category') or music_result.get('style') or llama_style
            valence = extract_field(music_result, 'valence', 'emotion_valence')
            arousal = extract_field(music_result, 'arousal', 'emotion_arousal')
            audio_id = extract_field(music_result, 'audioId', 'audio_id', 'id', 'audioId')
        
        # 응답 형식 3: 알 수 없는 응답 형식 또는 Polling 실패
        else:
            print(f"[데이터 추출] ⚠️ 알 수 없는 응답 형식 또는 Polling 실패: {type(music_result)}")
            # Polling 실패 시에도 기본 데이터는 music_result에 포함되어 있음
            if isinstance(music_result, dict):
                audio_url = music_result.get('audioUrl')
                # 제목은 Suno가 생성한 제목을 우선 사용하고, 없으면 사용자 입력을 fallback으로 사용
                music_title = music_result.get('title') or user_prompt[:50]
                duration = music_result.get('duration')
                lyrics = music_result.get('lyrics')
                image_url = music_result.get('imageUrl')
                api_genre = music_result.get('style') or music_result.get('genre') or llama_style
                audio_id = music_result.get('audioId') or music_result.get('audio_id') or music_result.get('id')
            else:
                audio_url = None
                music_title = user_prompt[:50]
                duration = None
                lyrics = None
                image_url = None
                api_genre = llama_style
                audio_id = None
            valence = None
            arousal = None
        
        task_id = music_result.get('taskId', 'unknown')
        
        print(f"[음악 생성 완료] 추출된 데이터:")
        print(f"  - task_id: {task_id}")
        print(f"  - audio_id: {audio_id}")
        print(f"  - audio_url: {audio_url}")
        print(f"  - title: {music_title}")
        print(f"  - duration: {duration}")
        print(f"  - lyrics: {lyrics[:100] if lyrics else 'None'}...")
        print(f"  - image_url: {image_url}")
        print(f"  - genre: {api_genre}")
        
        # 3. 사용자 확인 (user_id가 제공된 경우)
        user = None
        artist_name = "AI Artist"
        if user_id:
            try:
                user = Users.objects.get(user_id=user_id, is_deleted=False)
                # 로그인한 사용자의 닉네임을 아티스트 이름으로 사용
                artist_name = user.nickname if user.nickname else f"User {user.user_id}"
                print(f"[DB 저장] 사용자 확인: user_id={user_id}, artist_name={artist_name}")
            except Users.DoesNotExist:
                # 사용자가 없어도 계속 진행 (user=None)
                print(f"[DB 저장] 경고: user_id={user_id}에 해당하는 사용자를 찾을 수 없습니다.")
            except Exception as e:
                print(f"[DB 저장] 오류: 사용자 조회 중 예외 발생: {e}")
        
        now = timezone.now()
        # 장르: API 응답 > Llama 생성 > 프롬프트 추출 순으로 사용
        genre = api_genre or llama_style or extract_genre_from_prompt(llama_prompt)
        
        # 쉼표로 구분된 경우 첫 번째 장르만 사용 (예: "pop, dance" → "pop")
        if genre and ',' in genre:
            original_genre = genre
            genre = genre.split(',')[0].strip()
            print(f"[DB 저장] genre에서 첫 번째 값만 사용: 원본: {original_genre} → 저장: {genre}")
        
        # genre 필드는 max_length=50이므로 50자로 제한 (DB 오류 방지)
        if genre and len(genre) > 50:
            original_genre = genre
            genre = genre[:50]
            print(f"[DB 저장] 경고: genre가 50자를 초과하여 잘렸습니다. 원본: {original_genre[:100]}... → 저장: {genre}")
        print(f"[DB 저장] 장르 결정: {genre} (api_genre={api_genre}, llama_style={llama_style})")
        
        # DB 저장 시작 (트랜잭션 없이 단계별 저장, 각 단계에서 예외 처리)
        try:
            # 4. Artists 모델에 저장 (로그인한 사용자 이름 또는 AI Artist)
            print(f"[DB 저장] Artists 저장 시작: artist_name={artist_name}")
            artist = Artists.objects.create(
                artist_name=artist_name,
                artist_image=image_url,  # Suno API에서 받은 이미지
                created_at=now,
                updated_at=now,
                is_deleted=False
            )
            print(f"[DB 저장] ✅ Artists 저장 완료: artist_id={artist.artist_id}")
        except Exception as e:
            print(f"[DB 저장] ❌ Artists 저장 실패: {e}")
            traceback.print_exc()
            return Response(
                {"error": "아티스트 정보 저장에 실패했습니다.", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        try:
            # 5. Albums 모델에 AI 앨범 저장
            print(f"[DB 저장] Albums 저장 시작: album_name=AI Generated - {music_title}")
            album = Albums.objects.create(
                artist=artist,
                album_name=f"AI Generated - {music_title}",
                album_image=image_url,  # Suno API에서 받은 이미지
                created_at=now,
                updated_at=now,
                is_deleted=False
            )
            print(f"[DB 저장] ✅ Albums 저장 완료: album_id={album.album_id}")
        except Exception as e:
            print(f"[DB 저장] ❌ Albums 저장 실패: {e}")
            traceback.print_exc()
            return Response(
                {"error": "앨범 정보 저장에 실패했습니다.", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        try:
            # 6. Music 모델에 저장 (Suno API 응답 데이터 사용)
            print(f"[DB 저장] Music 저장 시작:")
            print(f"  - music_name: {music_title}")
            print(f"  - audio_url: {audio_url}")
            print(f"  - duration: {duration}")
            print(f"  - genre: {genre}")
            print(f"  - lyrics 길이: {len(lyrics) if lyrics else 0}")
            
            music = Music.objects.create(
                user=user,
                artist=artist,
                album=album,
                music_name=music_title,  # Suno가 생성한 제목
                audio_url=audio_url,  # Suno가 생성한 오디오 URL
                is_ai=True,
                genre=genre,
                duration=duration,  # 곡 길이
                lyrics=lyrics,  # 한국어 가사
                valence=None,  # null로 저장
                arousal=None,  # null로 저장
                itunes_id=None,  # null로 저장
                created_at=now,
                updated_at=now,
                is_deleted=False
            )
            print(f"[DB 저장] ✅ Music 저장 완료: music_id={music.music_id}")
        except Exception as e:
            print(f"[DB 저장] ❌ Music 저장 실패: {e}")
            traceback.print_exc()
            return Response(
                {"error": "음악 정보 저장에 실패했습니다.", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # 6-1. 타임스탬프 가사 가져오기 (비동기 처리 - API 응답 지연 방지)
        if not make_instrumental and task_id and task_id != 'unknown' and audio_url:
            try:
                print(f"[타임스탬프 가사] 조회 태스크 호출: taskId={task_id}, audioId={audio_id}")
                fetch_timestamped_lyrics_task.delay(music.music_id, task_id, audio_id)
                print(f"[타임스탬프 가사] ✅ 태스크 큐에 추가됨 (비동기 처리)")
            except Exception as e:
                print(f"[타임스탬프 가사] 태스크 호출 실패 (치명적이지 않음): {e}")
                # 타임스탬프 가사 조회 실패는 치명적이지 않으므로 계속 진행
        
        # 6-2. S3 업로드 태스크 호출 (Suno URL인 경우)
        if audio_url and is_suno_url(audio_url) and not is_s3_url(audio_url):
            try:
                print(f"[S3 업로드] 태스크 호출: music_id={music.music_id}, suno_url={audio_url}")
                upload_suno_audio_to_s3_task.delay(music.music_id, audio_url)
                print(f"[S3 업로드] ✅ 태스크 큐에 추가됨 (비동기 처리)")
            except Exception as e:
                print(f"[S3 업로드] 태스크 호출 실패 (치명적이지 않음): {e}")
                # S3 업로드 실패는 치명적이지 않으므로 계속 진행
        
        try:
            # 7. AiInfo 모델에 프롬프트 정보 저장
            print(f"[DB 저장] AiInfo 저장 시작: task_id={task_id}")
            ai_info = AiInfo.objects.create(
                music=music,
                input_prompt=f"TaskID: {task_id}\nOriginal: {user_prompt}\nTitle: {llama_title}\nStyle: {llama_style}\nPrompt: {llama_prompt}",
                created_at=now,
                updated_at=now,
                is_deleted=False
            )
            print(f"[DB 저장] ✅ AiInfo 저장 완료: aiinfo_id={ai_info.aiinfo_id}")
        except Exception as e:
            print(f"[DB 저장] ❌ AiInfo 저장 실패: {e}")
            traceback.print_exc()
            # AiInfo 저장 실패는 치명적이지 않으므로 경고만 출력하고 계속 진행
        
        print(f"[DB 저장 완료] ✅ 모든 데이터 저장 성공!")
        print(f"[DB 저장 완료] music_id={music.music_id}, artist_id={artist.artist_id}, album_id={album.album_id}")
        
        # 8. 응답 반환 (사용자 요청 형식)
        # valence와 arousal은 null로 저장되므로 null로 반환
        return Response({
            "music_id": music.music_id,
            "music_name": music.music_name,
            "audio_url": music.audio_url,
            "is_ai": music.is_ai,
            "genre": music.genre,
            "duration": music.duration,
            "lyrics": music.lyrics,
            "valence": None,  # null로 저장
            "arousal": None,  # null로 저장
            "artist_name": artist.artist_name if artist else "AI Artist",
            "album_name": album.album_name if album else None,
            "created_at": music.created_at.isoformat() if music.created_at else None
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        error_message = str(e)
        print(f"음악 생성 중 예상치 못한 오류 발생: {error_message}")
        traceback.print_exc()
        
        # 크레딧 부족 오류인 경우 명확한 메시지 반환
        if "크레딧" in error_message or "credit" in error_message.lower() or "insufficient" in error_message.lower():
            return Response(
                {"error": "Suno API 크레딧이 부족합니다. 크레딧을 충전해주세요.", "details": error_message},
                status=status.HTTP_402_PAYMENT_REQUIRED
            )
        # 인증 오류인 경우
        elif "인증" in error_message or "authentication" in error_message.lower() or "401" in error_message:
            return Response(
                {"error": "Suno API 인증에 실패했습니다. API 키를 확인해주세요.", "details": error_message},
                status=status.HTTP_401_UNAUTHORIZED
            )
        # 기타 오류
        else:
            return Response(
                {"error": "음악 생성 중 예상치 못한 오류가 발생했습니다.", "details": error_message},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@api_view(['POST'])
@csrf_exempt
@parser_classes([FlexibleJSONParser])
@extend_schema(
    summary="AI 음악 생성 (비동기) - 웹 페이지용",
    description="Celery를 사용한 AI 음악 생성 (비동기 처리, task_id 반환) - 웹 페이지 템플릿에서 사용",
    tags=['AI 음악 생성 (웹 페이지)']
)
def generate_music_async(request):
    """
    비동기 AI 음악 생성 API 엔드포인트 (Celery 사용)
    
    POST /api/music/generate-async/
    
    지원하는 입력 형식:
    1. JSON: {"prompt": "여름의 장미", "user_id": 1, "make_instrumental": false}
    2. 단순 텍스트: 여름의 장미
    
    Response:
    {
        "task_id": "abc123-def456",
        "status": "pending",
        "message": "음악 생성이 시작되었습니다."
    }
    """
    from ..tasks import generate_music_task
    
    # 커스텀 파서가 자동으로 처리
    data = request.data
    
    # Serializer로 검증
    serializer = MusicGenerateRequestSerializer(data=data)
    if not serializer.is_valid():
        return Response(
            {"error": "입력 데이터가 유효하지 않습니다.", "details": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    validated_data = serializer.validated_data
    
    # Celery 작업 시작
    task = generate_music_task.delay(
        user_prompt=validated_data['prompt'],
        user_id=validated_data.get('user_id'),
        make_instrumental=validated_data.get('make_instrumental', False)
    )
    
    return Response(
        {
            "task_id": task.id,
            "status": "pending",
            "message": "음악 생성이 시작되었습니다. task_id로 상태를 확인하세요."
        },
        status=status.HTTP_202_ACCEPTED
    )


@api_view(['GET'])
@extend_schema(
    summary="Celery 작업 상태 조회 - 웹 페이지용",
    description="Celery 작업의 상태 및 결과 조회 - 웹 페이지 템플릿에서 사용",
    tags=['작업 상태 (웹 페이지)']
)
def get_task_status(request, task_id):
    """
    Celery 작업 상태 조회
    
    GET /api/music/task/{task_id}/
    
    Response:
    {
        "task_id": "abc123",
        "status": "SUCCESS",
        "result": {...},
        "error": null
    }
    """
    from celery.result import AsyncResult
    
    task_result = AsyncResult(task_id)
    
    response_data = {
        "task_id": task_id,
        "status": task_result.status,
        "result": None,
        "error": None
    }
    
    if task_result.successful():
        response_data["result"] = task_result.result
    elif task_result.failed():
        response_data["error"] = str(task_result.info)
    
    serializer = TaskStatusSerializer(response_data)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['GET'])
@extend_schema(
    summary="음악 목록 조회 (웹 페이지용)",
    description="음악 목록 조회 (is_ai, user_id 필터링 지원) - 웹 페이지 템플릿에서 사용",
    tags=['음악 (웹 페이지)']
)
def list_music(request):
    """
    음악 목록 조회
    
    GET /api/music/
    Query Parameters:
    - is_ai: true/false (AI 생성 음악만 필터링)
    - user_id: 사용자 ID로 필터링
    """
    from ..legacy_serializers import MusicSerializer
    
    queryset = Music.objects.filter(is_deleted=False)
    
    # 필터링
    is_ai = request.query_params.get('is_ai')
    if is_ai is not None:
        is_ai_bool = is_ai.lower() in ['true', '1', 'yes']
        queryset = queryset.filter(is_ai=is_ai_bool)
    
    user_id = request.query_params.get('user_id')
    if user_id:
        queryset = queryset.filter(user_id=user_id)
    
    # 최신순 정렬
    queryset = queryset.order_by('-created_at')
    
    serializer = MusicSerializer(queryset, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['GET'])
@extend_schema(
    summary="음악 상세 조회 (웹 페이지용)",
    description="음악 ID로 상세 정보 조회 - 웹 페이지 템플릿에서 사용",
    tags=['음악 (웹 페이지)']
)
def get_music_detail(request, music_id):
    """
    음악 상세 정보 조회
    
    GET /api/music/{music_id}/
    """
    try:
        music = Music.objects.get(music_id=music_id, is_deleted=False)
        serializer = MusicGenerateResponseSerializer(music)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except Music.DoesNotExist:
        return Response(
            {"error": "음악을 찾을 수 없습니다."},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['POST'])
@csrf_exempt  # Suno API 외부 요청이므로 CSRF 제외
@extend_schema(
    summary="Suno 웹훅 (내부)",
    description="Suno API가 음악 생성 완료 시 호출하는 웹훅 - 내부 시스템에서만 사용",
    tags=['Suno 웹훅 (내부)']
)
def suno_webhook(request):
    """
    Suno API 콜백 엔드포인트 (즉시 응답 모드)
    
    POST /api/music/webhook/suno/
    
    Suno API가 음악 생성 완료 시 호출하는 웹훅입니다.
    
    이 webhook은 즉시 200 OK를 반환하고, 실제 DB 업데이트는 Celery 태스크에서 비동기로 처리합니다.
    
    Request Body:
    {
        "code": 200,
        "msg": "success",
        "data": {
            "taskId": "e408c70a29cab5204b2a345b05429d0e",
            "audioUrl": "https://...",
            "imageUrl": "https://...",
            "title": "Summer Roses",
            "duration": 180,
            "lyrics": "...",
            "valence": 0.8,
            "arousal": 0.6
        }
    }
    """
    # Celery 태스크는 music 앱 루트의 tasks.py에 정의되어 있으므로,
    # views 서브패키지 기준으로 한 단계 상위로 올라가서 임포트한다.
    from ..tasks import process_suno_webhook_task
    
    try:
        # 요청 받자마자 즉시 로그 출력
        print(f"[Suno Webhook] ✅ 요청 받음 ({request.META.get('CONTENT_LENGTH', '?')} bytes)")
        
        data = request.data
        
        # 간단한 검증만 수행
        callback_data = data.get('data', {})
        task_id = callback_data.get('task_id') or callback_data.get('taskId')
        
        print(f"[Suno Webhook] 데이터 파싱 완료: code={data.get('code')}, taskId={task_id[:50] if task_id else 'unknown'}")
        
        # 기본 검증
        if data.get('code') != 200:
            print(f"[Suno Webhook] ⚠️ 오류 응답 받음 (code={data.get('code')})")
            # 오류 응답도 200 OK로 반환 (Suno 재시도 방지)
            return Response({
                "status": "error",
                "message": f"Suno API 오류: {data.get('msg', 'unknown')}"
            }, status=status.HTTP_200_OK)
        
        if not task_id:
            print(f"[Suno Webhook] ⚠️ taskId 없음")
            return Response({
                "status": "error",
                "message": "taskId가 필요합니다."
            }, status=status.HTTP_200_OK)
        
        # 모든 무거운 작업은 Celery 태스크로 위임
        print(f"[Suno Webhook] Celery 태스크로 전달: taskId={task_id}")
        try:
            process_suno_webhook_task.delay(data)
            print(f"[Suno Webhook] ✅ Celery 큐에 추가 완료 - 즉시 200 OK 반환")
        except Exception as e:
            print(f"[Suno Webhook] ⚠️ Celery 큐 추가 실패 (계속 진행): {e}")
        
        # 즉시 200 OK 반환 (1초 이내)
        return Response({
            "status": "accepted",
            "message": "Webhook 수신 완료. 백그라운드에서 처리 중입니다.",
            "task_id": task_id
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        print(f"[Suno Webhook] 처리 중 오류: {e}")
        import traceback
        traceback.print_exc()
        # 에러가 발생해도 200 OK 반환 (Suno가 재시도하지 않도록, ngrok에서 200 OK 확인 가능)
        return Response({
            "status": "error",
            "message": "Webhook 처리 중 오류가 발생했습니다. 로그를 확인하세요.",
            "error": str(e)
        }, status=status.HTTP_200_OK)


@api_view(['GET'])
@extend_schema(
    summary="Suno 작업 상태 조회 - 웹 페이지용",
    description="Suno API 작업 상태 조회 (Polling용) - 웹 페이지 템플릿에서 사용",
    tags=['작업 상태 (웹 페이지)']
)
def get_suno_task_status(request, task_id):
    """
    Suno API 작업 상태 조회
    
    GET /api/music/suno-task/{task_id}/
    
    Response:
    {
        "task_id": "xxx",
        "status": "completed",
        "data": {...}
    }
    """
    try:
        suno_service = SunoAPIService()
        result = suno_service.get_task_status(task_id)
        
        if result:
            return Response({
                "task_id": task_id,
                "status": result.get('status', 'unknown'),
                "data": result
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                "task_id": task_id,
                "status": "not_found",
                "data": None
            }, status=status.HTTP_404_NOT_FOUND)
            
    except Exception as e:
        return Response({
            "error": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def music_generator_page(request):
    """
    음악 생성기 웹 페이지
    
    GET /music/generator/
    """
    return render(request, 'music/music_generator.html')


def music_monitor_page(request, music_id):
    """
    음악 생성 모니터링 웹 페이지
    
    GET /music/monitor/{music_id}/
    """
    return render(request, 'music/monitor.html', {'music_id': music_id})


def music_list_page(request):
    """
    AI 음악 목록 웹 페이지
    
    GET /music/list/
    """
    return render(request, 'music/music_list.html')
