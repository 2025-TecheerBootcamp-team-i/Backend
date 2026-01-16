"""
공통 유틸리티 - 페이지네이션 등
"""
from rest_framework.pagination import PageNumberPagination
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import random
from django.db import connection
from drf_spectacular.utils import extend_schema
from ..models import Music, Artists, Albums, Tags, MusicTags, PlayLogs


class MusicPagination(PageNumberPagination):
    """음악 목록 페이지네이션"""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class ErrorTestView(APIView):
    """
    에러율 테스트용 엔드포인트
    
    사용법:
    - GET /api/v1/test/error?code=500  # 500 에러 발생
    - GET /api/v1/test/error?code=503&rate=0.5  # 50% 확률로 503 에러 발생
    - GET /api/v1/test/error?code=500&rate=1.0  # 100% 확률로 500 에러 발생
    """
    permission_classes = []  # 인증 불필요 (테스트용)
    
    @extend_schema(
        summary="에러율 테스트",
        description="테스트용 에러 발생 엔드포인트 (Grafana 모니터링 테스트용)",
        tags=['테스트']
    )
    
    def get(self, request):
        # 쿼리 파라미터에서 에러 코드와 발생 확률 가져오기
        error_code = int(request.query_params.get('code', 500))
        error_rate = float(request.query_params.get('rate', 1.0))  # 기본값: 100% 에러 발생
        
        # 에러 코드 유효성 검사 (4xx, 5xx만 허용)
        if error_code < 400 or error_code >= 600:
            return Response(
                {'error': '에러 코드는 400-599 범위여야 합니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 확률에 따라 에러 발생 여부 결정
        if random.random() < error_rate:
            # 에러 발생
            error_messages = {
                500: 'Internal Server Error - 서버 내부 오류',
                502: 'Bad Gateway - 게이트웨이 오류',
                503: 'Service Unavailable - 서비스 일시 중단',
                504: 'Gateway Timeout - 게이트웨이 타임아웃',
            }
            message = error_messages.get(error_code, f'HTTP {error_code} 에러')
            
            return Response(
                {
                    'error': message,
                    'code': error_code,
                    'rate': error_rate,
                    'message': '이것은 테스트용 에러입니다.'
                },
                status=error_code
            )
        else:
            # 정상 응답
            return Response(
                {
                    'success': True,
                    'message': '정상 응답입니다.',
                    'code': 200,
                    'error_rate': error_rate,
                    'note': f'{error_rate * 100}% 확률로 {error_code} 에러가 발생하도록 설정되어 있지만, 이번 요청은 정상 처리되었습니다.'
                },
                status=status.HTTP_200_OK
            )


class DatabaseQueryTestView(APIView):
    """
    Database Queries 메트릭 테스트용 엔드포인트
    
    사용법:
    - GET /api/v1/test/db?count=10  # 10개의 다양한 DB 쿼리 실행
    - GET /api/v1/test/db?count=50&type=all  # 모든 타입의 쿼리 실행
    """
    permission_classes = []  # 인증 불필요 (테스트용)
    
    @extend_schema(
        summary="DB 쿼리 테스트",
        description="Database Queries 메트릭 테스트용 엔드포인트 (Grafana 모니터링 테스트용)",
        tags=['테스트']
    )
    
    def get(self, request):
        count = int(request.query_params.get('count', 10))
        query_type = request.query_params.get('type', 'all')  # all, select, insert, update, delete
        
        queries_executed = []
        
        # SELECT 쿼리들
        if query_type in ['all', 'select']:
            # 1. Music 조회
            music_list = list(Music.objects.filter(is_deleted=False)[:count])
            queries_executed.append(f'Music SELECT: {len(music_list)}건')
            
            # 2. Artist 조회
            artist_list = list(Artists.objects.filter(is_deleted=False)[:count])
            queries_executed.append(f'Artists SELECT: {len(artist_list)}건')
            
            # 3. Album 조회
            album_list = list(Albums.objects.filter(is_deleted=False)[:count])
            queries_executed.append(f'Albums SELECT: {len(album_list)}건')
            
            # 4. JOIN 쿼리 (select_related 사용)
            music_with_relations = list(
                Music.objects.select_related('artist', 'album')
                .filter(is_deleted=False)[:count]
            )
            queries_executed.append(f'Music JOIN (select_related): {len(music_with_relations)}건')
            
            # 5. 집계 쿼리
            music_count = Music.objects.filter(is_deleted=False).count()
            queries_executed.append(f'Music COUNT: {music_count}건')
            
            # 6. 조건부 쿼리
            ai_music = list(Music.objects.filter(is_ai=True, is_deleted=False)[:count])
            queries_executed.append(f'Music WHERE (is_ai=True): {len(ai_music)}건')
            
            # 7. Tags 조회
            tags_list = list(Tags.objects.filter(is_deleted=False)[:count])
            queries_executed.append(f'Tags SELECT: {len(tags_list)}건')
            
            # 8. MusicTags 조회 (다대다 관계)
            music_tags = list(MusicTags.objects.select_related('music', 'tag').filter(is_deleted=False)[:count])
            queries_executed.append(f'MusicTags JOIN: {len(music_tags)}건')
            
            # 9. PlayLogs 조회
            play_logs = list(PlayLogs.objects.select_related('music', 'user').filter(is_deleted=False)[:count])
            queries_executed.append(f'PlayLogs JOIN: {len(play_logs)}건')
        
        # INSERT 쿼리 (테스트용 - 실제로는 저장하지 않음)
        if query_type in ['all', 'insert']:
            # 실제 INSERT는 하지 않고 쿼리만 준비
            queries_executed.append('INSERT 쿼리 준비 (실제 실행 안 함)')
        
        # 실제 실행된 쿼리 수 확인
        actual_queries = len(connection.queries)
        
        return Response({
            'success': True,
            'message': 'Database Queries 테스트 완료',
            'queries_executed': queries_executed,
            'total_queries': actual_queries,
            'count': count,
            'type': query_type,
            'note': 'Grafana 대시보드의 Database Queries 패널에서 메트릭을 확인하세요.'
        }, status=status.HTTP_200_OK)
