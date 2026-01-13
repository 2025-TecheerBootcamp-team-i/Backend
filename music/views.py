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
from .models import Music, AiInfo, Users, Artists, Albums
from .serializers import (
    MusicGenerateRequestSerializer,
    MusicGenerateResponseSerializer,
    TaskStatusSerializer
)
from .services import LlamaService, SunoAPIService
from .parsers import FlexibleJSONParser
from .music_generate.utils import extract_genre_from_prompt


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
@parser_classes([FlexibleJSONParser])
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
        llama_title = music_params.get('title', user_prompt[:50])
        llama_style = music_params.get('style', 'K-Pop')
        llama_prompt = music_params.get('prompt', '')
        
        print(f"[Llama 결과] title: {llama_title}")
        print(f"[Llama 결과] style: {llama_style}")
        print(f"[Llama 결과] prompt: {llama_prompt}")
        
        # 프롬프트 길이 확인 (200자 이내 권장)
        if len(llama_prompt) > 200:
            print(f"[경고] 프롬프트가 200자를 초과합니다! ({len(llama_prompt)}자)")
            llama_prompt = llama_prompt[:200]
        
        # 2. Suno API로 음악 생성 (Polling 방식)
        suno_service = SunoAPIService()
        music_result = suno_service.generate_music(
            prompt=llama_prompt,
            style=llama_style,
            title=llama_title,
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
            music_title = extract_field(first_song, 'title', 'name', 'song_name', 'songName') or llama_title or user_prompt[:50]
            duration = extract_field(first_song, 'duration', 'length', 'time', 'duration_seconds')
            lyrics = extract_field(first_song, 'lyrics', 'lyric', 'text', 'song_lyrics')
            image_url = extract_field(first_song, 'imageUrl', 'image_url', 'image', 'cover', 'coverUrl', 'cover_url')
            api_genre = extract_field(first_song, 'genre', 'style', 'music_genre', 'category')
            valence = extract_field(first_song, 'valence', 'emotion_valence')
            arousal = extract_field(first_song, 'arousal', 'emotion_arousal')
        
        # 응답 형식 2: 직접 필드 접근 (Polling 실패 시 기본 데이터 포함)
        elif isinstance(music_result, dict):
            print(f"[데이터 추출] 직접 필드 접근 형식")
            audio_url = extract_field(music_result, 'audioUrl', 'audio_url', 'url', 'audio', 'audioFile')
            music_title = extract_field(music_result, 'title', 'name', 'song_name', 'songName') or music_result.get('title') or llama_title or user_prompt[:50]
            duration = extract_field(music_result, 'duration', 'length', 'time', 'duration_seconds')
            lyrics = extract_field(music_result, 'lyrics', 'lyric', 'text', 'song_lyrics')
            image_url = extract_field(music_result, 'imageUrl', 'image_url', 'image', 'cover', 'coverUrl', 'cover_url')
            api_genre = extract_field(music_result, 'genre', 'style', 'music_genre', 'category') or music_result.get('style') or llama_style
            valence = extract_field(music_result, 'valence', 'emotion_valence')
            arousal = extract_field(music_result, 'arousal', 'emotion_arousal')
        
        # 응답 형식 3: 알 수 없는 형식 또는 None
        else:
            print(f"[데이터 추출] ⚠️ 알 수 없는 응답 형식 또는 Polling 실패: {type(music_result)}")
            # Polling 실패 시에도 기본 데이터는 music_result에 포함되어 있음
            if isinstance(music_result, dict):
                audio_url = music_result.get('audioUrl')
                music_title = music_result.get('title') or llama_title or user_prompt[:50]
                duration = music_result.get('duration')
                lyrics = music_result.get('lyrics')
                image_url = music_result.get('imageUrl')
                api_genre = music_result.get('style') or music_result.get('genre') or llama_style
            else:
                audio_url = None
                music_title = llama_title or user_prompt[:50]
                duration = None
                lyrics = None
                image_url = None
                api_genre = llama_style
            valence = None
            arousal = None
        
        task_id = music_result.get('taskId', 'unknown')
        
        print(f"[음악 생성 완료] 추출된 데이터:")
        print(f"  - task_id: {task_id}")
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
    from .tasks import generate_music_task
    
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
def list_music(request):
    """
    음악 목록 조회
    
    GET /api/music/
    Query Parameters:
    - is_ai: true/false (AI 생성 음악만 필터링)
    - user_id: 사용자 ID로 필터링
    """
    from .serializers import MusicSerializer
    
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
def suno_webhook(request):
    """
    Suno API 콜백 엔드포인트
    
    POST /api/music/webhook/suno/
    
    Suno API가 음악 생성 완료 시 호출하는 웹훅입니다.
    
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
    try:
        data = request.data
        
        # 전체 요청 데이터 로깅
        print(f"[Suno Webhook] 받은 데이터: {json.dumps(data, indent=2, ensure_ascii=False)[:1000]}")
        
        # 응답 검증
        if data.get('code') != 200:
            print(f"[Suno Webhook] 오류 응답: {data}")
            return Response({"status": "error", "message": data.get('msg')}, status=status.HTTP_400_BAD_REQUEST)
        
        # 데이터 구조: data.data.task_id 또는 data.data.taskId
        callback_data = data.get('data', {})
        callback_type = callback_data.get('callbackType', 'complete')  # first, text, complete 등
        
        # task_id 추출 (다양한 필드명 시도)
        task_id = callback_data.get('task_id') or callback_data.get('taskId') or callback_data.get('task_id')
        
        if not task_id:
            print(f"[Suno Webhook] task_id를 찾을 수 없습니다. 데이터 구조: {json.dumps(callback_data, indent=2, ensure_ascii=False)[:500]}")
            return Response({"status": "error", "message": "taskId가 필요합니다."}, status=status.HTTP_400_BAD_REQUEST)
        
        print(f"[Suno Webhook] taskId={task_id}, callbackType={callback_type} 처리 중...")
        
        # 음악 데이터 추출 (data.data.data 배열에서 첫 번째 항목)
        music_list = callback_data.get('data', [])
        
        if not music_list or len(music_list) == 0:
            print(f"[Suno Webhook] 음악 데이터가 없습니다. callbackType={callback_type}")
            # callbackType이 'text'이면 아직 생성 중이므로 대기
            if callback_type == 'text':
                return Response({"status": "pending", "message": "음악 생성 진행 중..."}, status=status.HTTP_200_OK)
            return Response({"status": "error", "message": "음악 데이터가 없습니다."}, status=status.HTTP_400_BAD_REQUEST)
        
        first_music = music_list[0]
        
        # task_id로 AiInfo 찾기 (task_id 필드 직접 사용)
        try:
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
                print(f"[Suno Webhook] taskId={task_id}에 해당하는 AiInfo를 찾을 수 없습니다.")
                return Response({"status": "error", "message": "해당 작업을 찾을 수 없습니다."}, status=status.HTTP_404_NOT_FOUND)
            
            music = ai_info.music
            
            # 필수 필드 추출 (다양한 필드명 지원)
            def extract_field(data_dict, *keys):
                """여러 키 이름을 시도하여 값 추출"""
                for key in keys:
                    value = data_dict.get(key)
                    if value and value != '' and value != []:
                        return value
                return None
            
            audio_url_raw = extract_field(first_music, 'audio_url', 'audioUrl', 'url', 'audio', 'audioFile', 'mp3_url', 'mp3Url', 'song_url', 'songUrl', 'source_audio_url', 'sourceAudioUrl')
            image_url_raw = extract_field(first_music, 'image_url', 'imageUrl', 'image', 'cover', 'coverUrl', 'cover_url', 'source_image_url', 'sourceImageUrl')
            title = extract_field(first_music, 'title', 'name', 'song_name', 'songName')
            duration = extract_field(first_music, 'duration', 'length', 'time', 'duration_seconds')
            lyrics = extract_field(first_music, 'lyrics', 'lyric', 'song_lyrics')
            genre = extract_field(first_music, 'genre', 'style', 'music_genre', 'category', 'tags') or music.genre or 'Unknown'
            
            # 빈 문자열 처리
            audio_url = audio_url_raw.strip() if audio_url_raw and isinstance(audio_url_raw, str) else audio_url_raw
            image_url = image_url_raw.strip() if image_url_raw and isinstance(image_url_raw, str) else image_url_raw
            
            # 빈 문자열이면 None으로 변환
            if audio_url == '':
                audio_url = None
            if image_url == '':
                image_url = None
            
            # callbackType에 따른 처리
            # "text": 텍스트만 생성됨 (audio_url 없음) - DB 업데이트 없이 pending 반환
            # "first": 첫 번째 오디오 생성됨 (audio_url 있음) - DB 업데이트
            # "complete": 모든 오디오 생성 완료 (audio_url 있음) - DB 업데이트
            
            # callbackType이 "text"이고 audio_url이 없으면 생성 진행 중으로 처리
            if callback_type == 'text' and not audio_url:
                print(f"[Suno Webhook] callbackType='text', audio_url 없음 - 생성 진행 중 (DB 업데이트 없음)")
                return Response({
                    "status": "pending",
                    "message": "음악 생성 진행 중...",
                    "task_id": task_id,
                    "callback_type": callback_type
                }, status=status.HTTP_200_OK)
            
            # callbackType이 "text"이지만 audio_url이 있으면 업데이트 진행 (예외 케이스)
            # callbackType이 "first" 또는 "complete"이면 업데이트 진행
            
            # 필수 필드가 없으면 경고 로그
            if not audio_url:
                print(f"[Suno Webhook] 경고: audio_url이 없습니다. taskId={task_id}, callbackType={callback_type}")
            if not title:
                print(f"[Suno Webhook] 경고: title이 없습니다. taskId={task_id}")
            if not lyrics:
                print(f"[Suno Webhook] 경고: lyrics가 없습니다. taskId={task_id}")
            
            # Music 업데이트 (callbackType이 "text"가 아니거나, "text"이지만 audio_url이 있는 경우)
            now = timezone.now()
            if title:
                music.music_name = title
            if audio_url:
                music.audio_url = audio_url
            if duration:
                music.duration = duration
            if lyrics:
                music.lyrics = lyrics
            if genre:
                music.genre = genre
            # valence, arousal은 null로 유지
            music.updated_at = now
            music.save()
            
            print(f"[Suno Webhook] 저장된 데이터:")
            print(f"  - audio_url: {audio_url}")
            print(f"  - title: {title}")
            print(f"  - duration: {duration}")
            print(f"  - lyrics: {lyrics[:100] if lyrics else 'None'}...")
            print(f"  - image_url: {image_url}")
            print(f"  - genre: {genre}")
            print(f"  - callback_type: {callback_type}")
            
            # Artist 이미지 업데이트
            if image_url:
                artist = music.artist
                if artist:
                    artist.artist_image = image_url
                    artist.updated_at = now
                    artist.save()
            
            # Album 업데이트
            album = music.album
            if album:
                album.album_name = f"AI Generated - {music.music_name}"
                if image_url:
                    album.album_image = image_url
                album.updated_at = now
                album.save()
            
            print(f"[Suno Webhook] music_id={music.music_id} 업데이트 완료")
            
            # 응답 반환 (callbackType과 audio_url 상태에 따라)
            # "complete": 모든 오디오 생성 완료
            if callback_type == 'complete' and audio_url:
                return Response({
                    "status": "success",
                    "message": "음악 정보가 업데이트되었습니다.",
                    "music_id": music.music_id,
                    "music_name": music.music_name,
                    "audio_url": music.audio_url,
                    "callback_type": callback_type
                }, status=status.HTTP_200_OK)
            elif callback_type == 'complete' and not audio_url:
                return Response({
                    "status": "warning",
                    "message": "음악 정보가 업데이트되었지만 audio_url이 없습니다.",
                    "music_id": music.music_id,
                    "music_name": music.music_name,
                    "audio_url": None,
                    "callback_type": callback_type
                }, status=status.HTTP_200_OK)
            # "first": 첫 번째 오디오 생성됨
            elif callback_type == 'first' and audio_url:
                return Response({
                    "status": "success",
                    "message": "첫 번째 오디오가 생성되었습니다.",
                    "music_id": music.music_id,
                    "music_name": music.music_name,
                    "audio_url": music.audio_url,
                    "callback_type": callback_type
                }, status=status.HTTP_200_OK)
            elif callback_type == 'first' and not audio_url:
                return Response({
                    "status": "warning",
                    "message": "음악 정보가 업데이트되었지만 audio_url이 없습니다.",
                    "music_id": music.music_id,
                    "music_name": music.music_name,
                    "audio_url": None,
                    "callback_type": callback_type
                }, status=status.HTTP_200_OK)
            # "text": 텍스트만 생성됨 (하지만 audio_url이 있는 예외 케이스)
            elif callback_type == 'text':
                return Response({
                    "status": "success",
                    "message": "음악 정보가 업데이트되었습니다.",
                    "music_id": music.music_id,
                    "music_name": music.music_name,
                    "audio_url": music.audio_url,
                    "callback_type": callback_type
                }, status=status.HTTP_200_OK)
            # 기타 경우
            else:
                return Response({
                    "status": "success",
                    "message": "음악 정보가 업데이트되었습니다.",
                    "music_id": music.music_id,
                    "music_name": music.music_name,
                    "audio_url": music.audio_url,
                    "callback_type": callback_type
                }, status=status.HTTP_200_OK)
            
        except Exception as e:
            print(f"[Suno Webhook] DB 업데이트 오류: {e}")
            return Response({"status": "error", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    except Exception as e:
        print(f"[Suno Webhook] 처리 중 오류: {e}")
        return Response({"status": "error", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
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
