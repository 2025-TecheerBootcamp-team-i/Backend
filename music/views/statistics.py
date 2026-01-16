"""
사용자 통계 API View
"""
import logging
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response

from music.services.user_statistics import UserStatisticsService
from music.serializers.statistics import (
    UserStatisticsSerializer,
    ListeningTimeSerializer,
    GenreStatSerializer,
    ArtistStatSerializer,
    TagStatSerializer,
    AIGenerationStatSerializer
)

logger = logging.getLogger(__name__)


class UserStatisticsView(APIView):
    """
    사용자 개인 음악 분석 데이터 API
    
    GET /api/users/{user_id}/statistics/
    GET /api/users/{user_id}/statistics/?period=month  (이번 달)
    GET /api/users/{user_id}/statistics/?period=all    (전체)
    """
    
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


class UserListeningTimeView(APIView):
    """
    사용자 청취 시간 통계 API
    
    GET /api/users/{user_id}/statistics/listening-time/
    """
    
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


class UserTopGenresView(APIView):
    """
    사용자 Top 장르 통계 API
    
    GET /api/users/{user_id}/statistics/genres/
    """
    
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


class UserTopArtistsView(APIView):
    """
    사용자 Top 아티스트 통계 API
    
    GET /api/users/{user_id}/statistics/artists/
    """
    
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


class UserTopTagsView(APIView):
    """
    사용자 Top 태그(분위기/키워드) 통계 API
    
    GET /api/users/{user_id}/statistics/tags/
    """
    
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


class UserAIGenerationView(APIView):
    """
    사용자 AI 생성 활동 통계 API
    
    GET /api/users/{user_id}/statistics/ai-generation/
    """
    
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
