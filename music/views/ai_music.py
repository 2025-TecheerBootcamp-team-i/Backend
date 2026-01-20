"""
AI 음악 생성 API Views

이 모듈은 AI 음악 생성의 API 엔드포인트를 제공합니다.
기존 legacy.py의 FBV를 CBV로 전환하고 Service Layer를 활용합니다.
"""
import traceback
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.decorators import api_view
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from celery.result import AsyncResult

from ..models import Music
from ..serializers.ai_music import (
    MusicGenerateRequestSerializer,
    MusicGenerateResponseSerializer,
    MusicGenerateSimpleResponseSerializer,
    TaskStatusSerializer,
    MusicListSerializer,
    SunoTaskStatusResponseSerializer
)
from ..services import AiMusicGenerationService
from ..music_generate.services import SunoAPIService
from ..music_generate.exceptions import (
    SunoCreditInsufficientError,
    SunoAuthenticationError,
    SunoAPIError
)
from ..parsers import FlexibleJSONParser


class AiMusicGenerateView(APIView):
    """
    AI 음악 생성 API (동기 방식)
    
    POST /api/music/generate/
    
    기존 legacy.py의 generate_music 함수를 CBV로 전환했습니다.
    """
    permission_classes = [AllowAny]
    parser_classes = [FlexibleJSONParser]
    
    @extend_schema(
        summary="AI 음악 생성 (동기)",
        description="Suno API를 사용한 AI 음악 생성 (동기 처리, 완료까지 대기)",
        request=MusicGenerateRequestSerializer,
        responses={
            201: MusicGenerateSimpleResponseSerializer,
            400: OpenApiTypes.OBJECT,
            401: OpenApiTypes.OBJECT,
            402: OpenApiTypes.OBJECT,
            500: OpenApiTypes.OBJECT,
            503: OpenApiTypes.OBJECT
        },
        tags=['AI 음악 생성']
    )
    def post(self, request):
        """
        AI 음악 생성 요청 처리
        
        지원하는 입력 형식:
        1. JSON: {"prompt": "여름의 장미", "user_id": 1, "make_instrumental": false}
        2. 단순 텍스트: 여름의 장미 (FlexibleJSONParser가 자동 변환)
        """
        # 1. 요청 데이터 검증
        serializer = MusicGenerateRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {
                    "error": "입력 데이터가 유효하지 않습니다.",
                    "details": serializer.errors
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        validated_data = serializer.validated_data
        user_prompt = validated_data['prompt']
        user_id = validated_data.get('user_id')
        make_instrumental = validated_data.get('make_instrumental', False)
        
        try:
            # 2. Service Layer를 통해 음악 생성
            service = AiMusicGenerationService()
            music, artist, album, ai_info = service.generate_music(
                user_prompt=user_prompt,
                user_id=user_id,
                make_instrumental=make_instrumental,
                timeout=120
            )
            
            # 3. 응답 생성
            response_data = MusicGenerateSimpleResponseSerializer.from_music_model(
                music=music,
                artist=artist,
                album=album
            )
            
            return Response(response_data, status=status.HTTP_201_CREATED)
        
        except SunoCreditInsufficientError as e:
            # 크레딧 부족 오류
            return Response(
                {
                    "error": "Suno API 크레딧이 부족합니다. 크레딧을 충전해주세요.",
                    "details": str(e)
                },
                status=status.HTTP_402_PAYMENT_REQUIRED
            )
        
        except SunoAuthenticationError as e:
            # 인증 오류
            return Response(
                {
                    "error": "Suno API 인증에 실패했습니다. API 키를 확인해주세요.",
                    "details": str(e)
                },
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        except SunoAPIError as e:
            # Suno API 오류
            return Response(
                {
                    "error": "Suno API 요청에 실패했습니다.",
                    "details": str(e)
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        
        except Exception as e:
            # 기타 예외
            error_message = str(e)
            print(f"음악 생성 중 예상치 못한 오류 발생: {error_message}")
            traceback.print_exc()
            
            # 크레딧/인증 관련 키워드 체크 (폴백)
            if any(keyword in error_message.lower() for keyword in ['크레딧', 'credit', 'insufficient']):
                return Response(
                    {
                        "error": "Suno API 크레딧이 부족합니다. 크레딧을 충전해주세요.",
                        "details": error_message
                    },
                    status=status.HTTP_402_PAYMENT_REQUIRED
                )
            elif any(keyword in error_message.lower() for keyword in ['인증', 'authentication', '401']):
                return Response(
                    {
                        "error": "Suno API 인증에 실패했습니다. API 키를 확인해주세요.",
                        "details": error_message
                    },
                    status=status.HTTP_401_UNAUTHORIZED
                )
            else:
                return Response(
                    {
                        "error": "음악 생성 중 예상치 못한 오류가 발생했습니다.",
                        "details": error_message
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )


class AiMusicGenerateAsyncView(APIView):
    """
    AI 음악 생성 API (비동기 방식)
    
    POST /api/music/generate-async/
    
    Celery를 사용하여 비동기로 음악을 생성하고 task_id를 반환합니다.
    """
    permission_classes = [AllowAny]
    parser_classes = [FlexibleJSONParser]
    
    @extend_schema(
        summary="AI 음악 생성 (비동기)",
        description="Celery를 사용한 AI 음악 생성 (비동기 처리, task_id 반환)",
        request=MusicGenerateRequestSerializer,
        responses={
            202: TaskStatusSerializer,
            400: OpenApiTypes.OBJECT
        },
        tags=['AI 음악 생성']
    )
    def post(self, request):
        """
        비동기 AI 음악 생성 요청 처리
        
        즉시 task_id를 반환하고, 실제 생성은 백그라운드에서 처리합니다.
        """
        from ..tasks import generate_music_task
        
        # 1. 요청 데이터 검증
        serializer = MusicGenerateRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {
                    "error": "입력 데이터가 유효하지 않습니다.",
                    "details": serializer.errors
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        validated_data = serializer.validated_data
        
        # 2. Celery 작업 시작
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


class CeleryTaskStatusView(APIView):
    """
    Celery 작업 상태 조회 API
    
    GET /api/music/task/{task_id}/
    """
    permission_classes = [AllowAny]
    
    @extend_schema(
        summary="Celery 작업 상태 조회",
        description="Celery 작업의 상태 및 결과 조회",
        parameters=[
            OpenApiParameter(
                name='task_id',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
                description='Celery Task ID'
            )
        ],
        responses={
            200: TaskStatusSerializer
        },
        tags=['작업 상태']
    )
    def get(self, request, task_id):
        """Celery 작업 상태 조회"""
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


class MusicListView(APIView):
    """
    음악 목록 조회 API
    
    GET /api/music/
    
    기존 legacy.py의 list_music 함수를 CBV로 전환했습니다.
    """
    permission_classes = [AllowAny]
    
    @extend_schema(
        summary="음악 목록 조회",
        description="음악 목록 조회 (is_ai, user_id 필터링 지원)",
        parameters=[
            OpenApiParameter(
                name='is_ai',
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                description='AI 생성 음악 필터링 (true/false)',
                required=False
            ),
            OpenApiParameter(
                name='user_id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='사용자 ID 필터링',
                required=False
            )
        ],
        responses={
            200: MusicListSerializer(many=True)
        },
        tags=['음악']
    )
    def get(self, request):
        """음악 목록 조회 (필터링 및 정렬)"""
        # SoftDeleteManager가 자동으로 is_deleted=False인 레코드만 조회
        queryset = Music.objects.all()
        
        # is_ai 필터링
        is_ai = request.query_params.get('is_ai')
        if is_ai is not None:
            is_ai_bool = is_ai.lower() in ['true', '1', 'yes']
            queryset = queryset.filter(is_ai=is_ai_bool)
        
        # user_id 필터링
        user_id = request.query_params.get('user_id')
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        
        # 최신순 정렬
        queryset = queryset.select_related('artist', 'album').order_by('-created_at')
        
        serializer = MusicListSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class MusicDetailView(APIView):
    """
    음악 상세 조회 API
    
    GET /api/music/{music_id}/
    
    기존 legacy.py의 get_music_detail 함수를 CBV로 전환했습니다.
    """
    permission_classes = [AllowAny]
    
    @extend_schema(
        summary="음악 상세 조회",
        description="음악 ID로 상세 정보 조회",
        parameters=[
            OpenApiParameter(
                name='music_id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description='음악 ID'
            )
        ],
        responses={
            200: MusicGenerateResponseSerializer,
            404: OpenApiTypes.OBJECT
        },
        tags=['음악']
    )
    def get(self, request, music_id):
        """음악 상세 정보 조회"""
        try:
            # SoftDeleteManager가 자동으로 is_deleted=False인 레코드만 조회
            music = Music.objects.select_related('artist', 'album').get(music_id=music_id)
            serializer = MusicGenerateResponseSerializer(music)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Music.DoesNotExist:
            return Response(
                {"error": "음악을 찾을 수 없습니다."},
                status=status.HTTP_404_NOT_FOUND
            )


class SunoTaskStatusView(APIView):
    """
    Suno API 작업 상태 조회 API
    
    GET /api/music/suno-task/{task_id}/
    
    기존 legacy.py의 get_suno_task_status 함수를 CBV로 전환했습니다.
    """
    permission_classes = [AllowAny]
    
    @extend_schema(
        summary="Suno 작업 상태 조회",
        description="Suno API 작업 상태 조회 (Polling용)",
        parameters=[
            OpenApiParameter(
                name='task_id',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
                description='Suno API TaskID'
            )
        ],
        responses={
            200: SunoTaskStatusResponseSerializer,
            404: SunoTaskStatusResponseSerializer,
            500: OpenApiTypes.OBJECT
        },
        tags=['작업 상태']
    )
    def get(self, request, task_id):
        """Suno API 작업 상태 조회"""
        try:
            suno_service = SunoAPIService()
            result = suno_service.get_task_status(task_id)
            
            if result:
                return Response(
                    {
                        "task_id": task_id,
                        "status": result.get('status', 'unknown'),
                        "data": result
                    },
                    status=status.HTTP_200_OK
                )
            else:
                return Response(
                    {
                        "task_id": task_id,
                        "status": "not_found",
                        "data": None
                    },
                    status=status.HTTP_404_NOT_FOUND
                )
        
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class SunoWebhookView(APIView):
    """
    Suno API 웹훅 엔드포인트
    
    POST /api/music/webhook/suno/
    
    Suno API가 음악 생성 완료 시 호출하는 웹훅입니다.
    즉시 200 OK를 반환하고, 실제 DB 업데이트는 Celery 태스크에서 비동기로 처리합니다.
    """
    permission_classes = [AllowAny]  # 외부 API 요청이므로 인증 제외
    parser_classes = [FlexibleJSONParser]
    
    @extend_schema(
        summary="Suno 웹훅",
        description="Suno API가 음악 생성 완료 시 호출하는 웹훅",
        tags=['Suno 웹훅']
    )
    def post(self, request):
        """
        Suno API 콜백 처리
        
        즉시 200 OK를 반환하고, 실제 처리는 Celery 태스크로 위임합니다.
        """
        from ..tasks import process_suno_webhook_task
        
        try:
            print(f"[Suno Webhook] ✅ 요청 받음 ({request.META.get('CONTENT_LENGTH', '?')} bytes)")
            
            data = request.data
            callback_data = data.get('data', {})
            task_id = callback_data.get('task_id') or callback_data.get('taskId')
            
            print(f"[Suno Webhook] 데이터 파싱 완료: code={data.get('code')}, taskId={task_id[:50] if task_id else 'unknown'}")
            
            # 기본 검증
            if data.get('code') != 200:
                print(f"[Suno Webhook] ⚠️ 오류 응답 받음 (code={data.get('code')})")
                return Response(
                    {
                        "status": "error",
                        "message": f"Suno API 오류: {data.get('msg', 'unknown')}"
                    },
                    status=status.HTTP_200_OK  # Suno 재시도 방지
                )
            
            if not task_id:
                print(f"[Suno Webhook] ⚠️ taskId 없음")
                return Response(
                    {
                        "status": "error",
                        "message": "taskId가 필요합니다."
                    },
                    status=status.HTTP_200_OK
                )
            
            # Celery 태스크로 위임
            print(f"[Suno Webhook] Celery 태스크로 전달: taskId={task_id}")
            try:
                process_suno_webhook_task.delay(data)
                print(f"[Suno Webhook] ✅ Celery 큐에 추가 완료 - 즉시 200 OK 반환")
            except Exception as e:
                print(f"[Suno Webhook] ⚠️ Celery 큐 추가 실패 (계속 진행): {e}")
            
            # 즉시 200 OK 반환
            return Response(
                {
                    "status": "accepted",
                    "message": "Webhook 수신 완료. 백그라운드에서 처리 중입니다.",
                    "task_id": task_id
                },
                status=status.HTTP_200_OK
            )
        
        except Exception as e:
            print(f"[Suno Webhook] 처리 중 오류: {e}")
            traceback.print_exc()
            
            # 에러가 발생해도 200 OK 반환 (Suno 재시도 방지)
            return Response(
                {
                    "status": "error",
                    "message": "Webhook 처리 중 오류가 발생했습니다. 로그를 확인하세요.",
                    "error": str(e)
                },
                status=status.HTTP_200_OK
            )
