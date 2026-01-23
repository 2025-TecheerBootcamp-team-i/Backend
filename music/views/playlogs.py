"""
재생 기록 관련 Views - PlayLog 도메인
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.utils import timezone
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample

from ..models import Music, PlayLogs, Users
from ..serializers import PlayLogResponseSerializer, PlayLogListItemSerializer


class PlayLogCreateView(APIView):
    """
    재생 기록 생성 API (PlayLog 도메인)
    - POST: 음악 재생 시 기록 생성
    
    참고: 음악 재생 정보 조회(GET)는 MusicPlayView로 이동됨
    """
    permission_classes = [AllowAny]
    
    @extend_schema(
        summary="재생 기록 생성",
        description="""
        음악 재생 시 재생 기록을 저장합니다.
        
        **요구사항:**
        - 로그인 필수 (JWT 토큰)
        - 같은 곡을 여러 번 재생해도 모두 기록됨
        - 차트 집계의 원본 데이터로 사용됨
        
        **참고:**
        - 음악 재생 정보 조회는 GET /tracks/{music_id}/play 사용
        """,
        request=None,
        responses={
            201: OpenApiResponse(
                response=PlayLogResponseSerializer,
                description="재생 기록 생성 성공",
                examples=[
                    OpenApiExample(
                        name="성공 응답",
                        value={
                            "message": "재생 기록이 저장되었습니다",
                            "play_log_id": 123,
                            "music_id": 456,
                            "played_at": "2026-01-13T15:30:00Z"
                        }
                    )
                ]
            ),
            401: OpenApiResponse(description="인증 실패"),
            404: OpenApiResponse(description="음악을 찾을 수 없음"),
        },
        tags=['음악 재생']
    )
    def post(self, request, music_id):
        """재생 기록 생성 (PlayLog 도메인)"""
        # 0. 인증 확인
        if not request.user.is_authenticated:
            return Response(
                {"detail": "인증이 필요합니다"},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # 1. 음악 존재 확인 (SoftDeleteManager가 자동으로 is_deleted=False인 레코드만 조회)
        music = get_object_or_404(Music, music_id=music_id)
        
        # 2. 사용자 조회 (JWT에서 email 추출)
        # SoftDeleteManager가 자동으로 is_deleted=False인 레코드만 조회
        try:
            user = Users.objects.get(email=request.user.email)
        except Users.DoesNotExist:
            return Response(
                {"detail": "사용자를 찾을 수 없습니다"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # 3. 재생 기록 생성
        # TrackableMixin이 created_at, updated_at, is_deleted를 자동으로 관리
        play_log = PlayLogs.objects.create(
            music=music,
            user=user,
            played_at=timezone.now()
        )
        
        # 4. 응답 반환
        response_data = {
            "message": "재생 기록이 저장되었습니다",
            "play_log_id": play_log.play_log_id,
            "music_id": music.music_id,
            "played_at": play_log.played_at
        }
        
        return Response(response_data, status=status.HTTP_201_CREATED)


class PlayLogView(APIView):
    """
    음악 재생 및 로그 기록을 위한 복합 View
    
    - GET: MusicPlayView로 위임 (Music 도메인 - 재생 정보 조회)
    - POST: PlayLogCreateView로 위임 (PlayLog 도메인 - 로그 기록)
    
    이 복합 View는 단일 URL 엔드포인트에서 도메인별로 분리된 View들을 조합하는 역할만 수행합니다.
    실제 비즈니스 로직은 각 도메인 View에 위치합니다.
    """
    permission_classes = [AllowAny]
    
    def get(self, request, music_id):
        """음악 재생 정보 조회 - MusicPlayView로 위임"""
        from .music import MusicPlayView
        return MusicPlayView().get(request, music_id)
    
    def post(self, request, music_id):
        """재생 기록 생성 - PlayLogCreateView로 위임"""
        return PlayLogCreateView().post(request, music_id)


class MusicPlayLogsView(APIView):
    """
    음악 ID로 재생 로그 목록 조회 API
    - GET: 특정 음악의 모든 재생 로그 조회 (user_id, played_at)
    """
    permission_classes = [AllowAny]
    
    @extend_schema(
        summary="음악별 재생 로그 조회",
        description="""
        특정 음악의 재생 로그 목록을 조회합니다.
        
        **반환 정보:**
        - user_id: 재생한 사용자 ID
        - played_at: 재생 시간 (소수점 제거)
        
        **참고:**
        - 삭제되지 않은 재생 로그만 조회됨
        - 최신 재생 순으로 정렬
        """,
        responses={
            200: OpenApiResponse(
                response=PlayLogListItemSerializer(many=True),
                description="재생 로그 조회 성공",
                examples=[
                    OpenApiExample(
                        name="성공 응답",
                        value=[
                            {
                                "user_id": 1,
                                "played_at": "2026-01-23T15:30:00Z"
                            },
                            {
                                "user_id": 2,
                                "played_at": "2026-01-23T14:20:00Z"
                            }
                        ]
                    )
                ]
            ),
            404: OpenApiResponse(description="음악을 찾을 수 없음"),
        },
        tags=['음악 재생']
    )
    def get(self, request, music_id):
        """특정 음악의 재생 로그 목록 조회"""
        # 1. 음악 존재 확인
        music = get_object_or_404(Music, music_id=music_id)
        
        # 2. 해당 음악의 재생 로그 조회 (최신순)
        play_logs = PlayLogs.objects.filter(music=music).order_by('-played_at')
        
        # 3. Serializer로 변환
        serializer = PlayLogListItemSerializer(play_logs, many=True)
        
        # 4. 응답 반환
        return Response(serializer.data, status=status.HTTP_200_OK)
