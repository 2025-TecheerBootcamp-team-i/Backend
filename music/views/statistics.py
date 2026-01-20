"""
사용자 통계 API View
"""
import logging
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes

from music.services.user_statistics import UserStatisticsService
from music.serializers.statistics import (
    UserStatisticsSerializer,
    ListeningTimeSerializer,
    GenreStatSerializer,
    ArtistStatSerializer,
    TagStatSerializer,
    TrackStatSerializer,
    AIGenerationStatSerializer
)

logger = logging.getLogger(__name__)


@extend_schema(tags=['사용자 통계'])
class UserStatisticsView(APIView):
    """
    사용자 개인 음악 분석 데이터 API
    
    GET /api/users/{user_id}/statistics/
    GET /api/users/{user_id}/statistics/?period=month  (이번 달)
    GET /api/users/{user_id}/statistics/?period=all    (전체)
    """
    
    @extend_schema(
        summary="사용자 전체 음악 통계 조회",
        description="사용자의 청취 시간, Top 장르, Top 아티스트, Top 태그, AI 생성 활동 등 전체 통계를 반환합니다.",
        parameters=[
            OpenApiParameter(
                name='period',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='조회 기간: "month" (이번 달, 기본값) 또는 "all" (전체)',
                required=False,
                default='month',
                examples=[
                    OpenApiExample(name='이번 달', value='month'),
                    OpenApiExample(name='전체 기간', value='all'),
                ]
            )
        ],
        responses={200: UserStatisticsSerializer}
    )
    def get(self, request, user_id: int):
        """
        사용자의 전체 음악 통계를 반환합니다.
        
        Query Parameters:
            - period: 'month' (이번 달, 기본값) 또는 'all' (전체)
        
        Response:
            {
                "listening_time": {
                    "total_seconds": 442800,
                    "total_hours": 123.0,
                    "play_count": 1500,
                    "previous_period_hours": 110.0,
                    "change_percent": 11.8
                },
                "top_genres": [
                    {"rank": 1, "genre": "Indie", "play_count": 500, "percentage": 33.3},
                    {"rank": 2, "genre": "Pop", "play_count": 300, "percentage": 20.0}
                ],
                "top_artists": [
                    {"rank": 1, "artist_id": 1, "artist_name": "아티스트A", ...},
                    ...
                ],
                "top_tags": [
                    {"tag_id": 1, "tag_key": "새벽감성", "play_count": 200},
                    ...
                ],
                "ai_generation": {
                    "total_generated": 3,
                    "last_generated_at": "2026-01-14T10:30:00Z",
                    "last_generated_days_ago": 2
                }
            }
        """
        period = request.query_params.get('period', 'month')
        
        if period not in ['month', 'all']:
            return Response(
                {'error': 'Invalid period. Use "month" or "all".'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            statistics = UserStatisticsService.get_full_statistics(user_id, period)
            serializer = UserStatisticsSerializer(statistics)
            return Response(serializer.data)
        except Exception as e:
            logger.error(f"[UserStatistics] 통계 조회 실패: user_id={user_id}, error={e}")
            return Response(
                {'error': '통계를 조회하는 중 오류가 발생했습니다.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@extend_schema(tags=['사용자 통계'])
class UserListeningTimeView(APIView):
    """
    사용자 청취 시간 통계 API
    
    GET /api/users/{user_id}/statistics/listening-time/
    """
    
    @extend_schema(
        summary="사용자 청취 시간 통계 조회",
        description="사용자의 총 청취 시간, 재생 횟수, 전월 대비 변화율을 반환합니다.",
        parameters=[
            OpenApiParameter(
                name='period',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='조회 기간: "month" (이번 달, 기본값) 또는 "all" (전체)',
                required=False,
                default='month',
                examples=[
                    OpenApiExample(name='이번 달', value='month'),
                    OpenApiExample(name='전체 기간', value='all'),
                ]
            )
        ],
        responses={200: ListeningTimeSerializer}
    )
    def get(self, request, user_id: int):
        period = request.query_params.get('period', 'month')
        
        try:
            data = UserStatisticsService.get_listening_time(user_id, period)
            serializer = ListeningTimeSerializer(data)
            return Response(serializer.data)
        except Exception as e:
            logger.error(f"[UserListeningTime] 조회 실패: user_id={user_id}, error={e}")
            return Response(
                {'error': '청취 시간을 조회하는 중 오류가 발생했습니다.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@extend_schema(tags=['사용자 통계'])
class UserTopGenresView(APIView):
    """
    사용자 Top 장르 통계 API
    
    GET /api/users/{user_id}/statistics/genres/
    """
    
    @extend_schema(
        summary="사용자 Top 장르 통계 조회",
        description="사용자가 가장 많이 들은 장르 목록을 재생 횟수 순으로 반환합니다.",
        parameters=[
            OpenApiParameter(
                name='period',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='조회 기간: "month" (이번 달, 기본값) 또는 "all" (전체)',
                required=False,
                default='month',
                examples=[
                    OpenApiExample(name='이번 달', value='month'),
                    OpenApiExample(name='전체 기간', value='all'),
                ]
            ),
            OpenApiParameter(
                name='limit',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='반환할 Top 장르 수 (기본값: 3)',
                required=False,
                default=3
            )
        ],
        responses={200: GenreStatSerializer(many=True)}
    )
    def get(self, request, user_id: int):
        period = request.query_params.get('period', 'month')
        limit = int(request.query_params.get('limit', 3))
        
        try:
            data = UserStatisticsService.get_top_genres(user_id, period, limit)
            serializer = GenreStatSerializer(data, many=True)
            return Response(serializer.data)
        except Exception as e:
            logger.error(f"[UserTopGenres] 조회 실패: user_id={user_id}, error={e}")
            return Response(
                {'error': '장르 통계를 조회하는 중 오류가 발생했습니다.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@extend_schema(tags=['사용자 통계'])
class UserTopArtistsView(APIView):
    """
    사용자 Top 아티스트 통계 API
    
    GET /api/users/{user_id}/statistics/artists/
    """
    
    @extend_schema(
        summary="사용자 Top 아티스트 통계 조회",
        description="사용자가 가장 많이 들은 아티스트 목록을 재생 횟수 순으로 반환합니다.",
        parameters=[
            OpenApiParameter(
                name='period',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='조회 기간: "month" (이번 달, 기본값) 또는 "all" (전체)',
                required=False,
                default='month',
                examples=[
                    OpenApiExample(name='이번 달', value='month'),
                    OpenApiExample(name='전체 기간', value='all'),
                ]
            ),
            OpenApiParameter(
                name='limit',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='반환할 Top 아티스트 수 (기본값: 3)',
                required=False,
                default=3
            )
        ],
        responses={200: ArtistStatSerializer(many=True)}
    )
    def get(self, request, user_id: int):
        period = request.query_params.get('period', 'month')
        limit = int(request.query_params.get('limit', 3))
        
        try:
            data = UserStatisticsService.get_top_artists(user_id, period, limit)
            serializer = ArtistStatSerializer(data, many=True)
            return Response(serializer.data)
        except Exception as e:
            logger.error(f"[UserTopArtists] 조회 실패: user_id={user_id}, error={e}")
            return Response(
                {'error': '아티스트 통계를 조회하는 중 오류가 발생했습니다.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@extend_schema(tags=['사용자 통계'])
class UserTopTagsView(APIView):
    """
    사용자 Top 태그(분위기/키워드) 통계 API
    
    GET /api/users/{user_id}/statistics/tags/
    """
    
    @extend_schema(
        summary="사용자 Top 태그/키워드 통계 조회",
        description="사용자가 가장 많이 들은 태그(분위기/키워드) 목록을 재생 횟수 순으로 반환합니다.",
        parameters=[
            OpenApiParameter(
                name='period',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='조회 기간: "month" (이번 달, 기본값) 또는 "all" (전체)',
                required=False,
                default='month',
                examples=[
                    OpenApiExample(name='이번 달', value='month'),
                    OpenApiExample(name='전체 기간', value='all'),
                ]
            ),
            OpenApiParameter(
                name='limit',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='반환할 Top 태그 수 (기본값: 6)',
                required=False,
                default=6
            )
        ],
        responses={200: TagStatSerializer(many=True)}
    )
    def get(self, request, user_id: int):
        period = request.query_params.get('period', 'month')
        limit = int(request.query_params.get('limit', 6))
        
        try:
            data = UserStatisticsService.get_top_tags(user_id, period, limit)
            serializer = TagStatSerializer(data, many=True)
            return Response(serializer.data)
        except Exception as e:
            logger.error(f"[UserTopTags] 조회 실패: user_id={user_id}, error={e}")
            return Response(
                {'error': '태그 통계를 조회하는 중 오류가 발생했습니다.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@extend_schema(tags=['사용자 통계'])
class UserTopTracksView(APIView):
    """
    사용자 Top 음악 차트 API
    
    GET /api/users/{user_id}/statistics/tracks/
    """
    
    @extend_schema(
        summary="사용자 Top 음악 차트 조회",
        description="사용자가 가장 많이 들은 음악 목록을 재생 횟수 순으로 반환합니다. (기본 Top 15)",
        parameters=[
            OpenApiParameter(
                name='period',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='조회 기간: "month" (이번 달, 기본값) 또는 "all" (전체)',
                required=False,
                default='month',
                examples=[
                    OpenApiExample(name='이번 달', value='month'),
                    OpenApiExample(name='전체 기간', value='all'),
                ]
            ),
            OpenApiParameter(
                name='limit',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='반환할 Top 음악 수 (기본값: 15)',
                required=False,
                default=15
            )
        ],
        responses={200: TrackStatSerializer(many=True)}
    )
    def get(self, request, user_id: int):
        period = request.query_params.get('period', 'month')
        limit = int(request.query_params.get('limit', 15))
        
        try:
            data = UserStatisticsService.get_top_tracks(user_id, period, limit)
            serializer = TrackStatSerializer(data, many=True)
            return Response(serializer.data)
        except Exception as e:
            logger.error(f"[UserTopTracks] 조회 실패: user_id={user_id}, error={e}")
            return Response(
                {'error': '음악 차트를 조회하는 중 오류가 발생했습니다.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@extend_schema(tags=['사용자 통계'])
class UserAIGenerationView(APIView):
    """
    사용자 AI 생성 활동 통계 API
    
    GET /api/users/{user_id}/statistics/ai-generation/
    """
    
    @extend_schema(
        summary="사용자 AI 음악 생성 활동 통계 조회",
        description="사용자가 AI로 생성한 음악의 총 개수와 마지막 생성 시점을 반환합니다.",
        parameters=[
            OpenApiParameter(
                name='period',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='조회 기간: "month" (이번 달, 기본값) 또는 "all" (전체)',
                required=False,
                default='month',
                examples=[
                    OpenApiExample(name='이번 달', value='month'),
                    OpenApiExample(name='전체 기간', value='all'),
                ]
            )
        ],
        responses={200: AIGenerationStatSerializer}
    )
    def get(self, request, user_id: int):
        period = request.query_params.get('period', 'month')
        
        try:
            data = UserStatisticsService.get_ai_generation_stats(user_id, period)
            serializer = AIGenerationStatSerializer(data)
            return Response(serializer.data)
        except Exception as e:
            logger.error(f"[UserAIGeneration] 조회 실패: user_id={user_id}, error={e}")
            return Response(
                {'error': 'AI 생성 통계를 조회하는 중 오류가 발생했습니다.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
