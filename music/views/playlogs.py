"""
재생 기록 관련 Views
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample

from ..models import Music, PlayLogs, Users
from ..serializers import PlayLogResponseSerializer


class PlayLogView(APIView):
    """
    재생 기록 API
    - POST: 음악 재생 시 기록 생성
    """
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="재생 기록 생성",
        description="""
음악 재생 시 재생 기록을 저장합니다.

- 로그인 필수 (JWT 토큰)
- 같은 곡을 여러 번 재생해도 모두 기록됨
- 차트 집계의 원본 데이터로 사용됨
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
        tags=["재생 기록"]
    )
    def post(self, request, music_id):
        """재생 기록 생성"""
        # 1. 음악 존재 확인
        music = get_object_or_404(
            Music.objects.filter(is_deleted=False),
            music_id=music_id
        )
        
        # 2. 사용자 조회 (JWT에서 email 추출)
        try:
            user = Users.objects.get(
                email=request.user.email,
                is_deleted=False
            )
        except Users.DoesNotExist:
            return Response(
                {"detail": "사용자를 찾을 수 없습니다"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # 3. 재생 기록 생성
        now = timezone.now()
        play_log = PlayLogs.objects.create(
            music=music,
            user=user,
            played_at=now,
            created_at=now,
            updated_at=now,
            is_deleted=False
        )
        
        # 4. 응답 반환
        response_data = {
            "message": "재생 기록이 저장되었습니다",
            "play_log_id": play_log.play_log_id,
            "music_id": music.music_id,
            "played_at": play_log.played_at
        }
        
        return Response(response_data, status=status.HTTP_201_CREATED)
