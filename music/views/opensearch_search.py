"""
OpenSearch 기반 검색 Views
"""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes
from ..services.opensearch import opensearch_service
from ..serializers import iTunesSearchResultSerializer
from .common import MusicPagination


class OpenSearchMusicSearchView(APIView):
    """
    OpenSearch 기반 음악 검색
    
    - 빠른 전문 검색 (Full-text Search)
    - 한글 검색 지원
    - 퍼지 검색 (오타 허용)
    - 정렬 옵션 (관련도, 인기도, 최신순)
    
    GET /api/v1/search/opensearch?q={검색어}&sort_by={정렬}&exclude_ai={bool}
    """
    permission_classes = [AllowAny]
    pagination_class = MusicPagination
    
    @extend_schema(
        summary="OpenSearch 음악 검색",
        description="""
        OpenSearch를 활용한 고속 음악 검색
        
        **특징:**
        - 전문 검색 (Full-text Search)
        - 한글 형태소 분석
        - 퍼지 매칭 (오타 허용)
        - ngram 기반 부분 일치
        
        **검색 대상:**
        - 곡명 (가중치: 높음)
        - 아티스트명 (가중치: 중간)
        - 앨범명 (가중치: 낮음)
        
        **정렬 옵션:**
        - `relevance` (기본값): 검색 관련도 순
        - `popularity`: 인기도 순 (재생수 + 좋아요)
        - `recent`: 최신순
        """,
        parameters=[
            OpenApiParameter(
                name='q',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='검색어',
                required=True,
                examples=[
                    OpenApiExample(
                        name='일반 검색',
                        value='아이유',
                        description='아티스트명 또는 곡명 검색'
                    ),
                    OpenApiExample(
                        name='부분 검색',
                        value='분홍',
                        description='곡명 부분 일치 검색'
                    ),
                ]
            ),
            OpenApiParameter(
                name='sort_by',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='정렬 기준',
                required=False,
                default='relevance',
                enum=['relevance', 'popularity', 'recent']
            ),
            OpenApiParameter(
                name='exclude_ai',
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                description='AI 생성곡 제외',
                required=False,
                default=False
            ),
            OpenApiParameter(
                name='genre',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='장르 필터',
                required=False,
            ),
            OpenApiParameter(
                name='page',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='페이지 번호',
                required=False,
                default=1
            ),
            OpenApiParameter(
                name='page_size',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='페이지 크기 (최대 100)',
                required=False,
                default=20
            ),
        ],
        responses={
            200: iTunesSearchResultSerializer(many=True),
            400: {'description': 'Bad Request - q 파라미터 필요'},
            503: {'description': 'Service Unavailable - OpenSearch 사용 불가'}
        },
        tags=['검색']
    )
    def get(self, request):
        """OpenSearch 음악 검색 처리"""
        # OpenSearch 사용 가능 여부 확인
        if not opensearch_service.is_available():
            return Response(
                {'error': 'OpenSearch 서비스를 사용할 수 없습니다.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        
        # 쿼리 파라미터 추출
        query = request.query_params.get('q', '').strip()
        
        if not query:
            return Response(
                {'error': 'q 파라미터가 필요합니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 필터 옵션
        filters = {}
        
        # AI 제외 옵션
        exclude_ai = request.query_params.get('exclude_ai', '').lower() == 'true'
        if exclude_ai:
            filters['is_ai'] = False
        
        # 장르 필터
        genre = request.query_params.get('genre', '').strip()
        if genre:
            filters['genre'] = genre
        
        # 정렬 옵션
        sort_by = request.query_params.get('sort_by', 'relevance')
        if sort_by not in ['relevance', 'popularity', 'recent']:
            sort_by = 'relevance'
        
        # 페이지네이션 파라미터
        try:
            page = int(request.query_params.get('page', 1))
            page_size = int(request.query_params.get('page_size', 20))
            page_size = min(page_size, 100)  # 최대 100개
        except ValueError:
            page = 1
            page_size = 20
        
        # OpenSearch에서 시작 위치 계산
        from_ = (page - 1) * page_size
        
        # 검색 실행
        search_results = opensearch_service.search(
            query=query,
            filters=filters,
            size=page_size,
            from_=from_,
            sort_by=sort_by
        )
        
        # 에러 처리
        if 'error' in search_results:
            return Response(
                {'error': f'검색 중 오류 발생: {search_results["error"]}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # 결과를 iTunes 검색 결과 형식으로 변환
        results = []
        for hit in search_results['hits']:
            results.append({
                'itunes_id': hit.get('itunes_id'),
                'music_name': hit.get('music_name', ''),
                'artist_name': hit.get('artist_name', ''),
                'artist_id': hit.get('artist_id'),
                'album_name': hit.get('album_name', ''),
                'album_id': hit.get('album_id'),
                'genre': hit.get('genre', ''),
                'duration': hit.get('duration'),
                'audio_url': None,  # OpenSearch에는 URL 저장 안 함
                'album_image': None,  # OpenSearch에는 이미지 URL 저장 안 함
                'in_db': True,  # OpenSearch에 있다는 것은 DB에도 있다는 의미
                'has_matching_tags': False,
                '_score': hit.get('_score'),  # 검색 점수
                '_highlight': hit.get('_highlight', {}),  # 하이라이트
            })
        
        # 응답 생성 (페이지네이션 메타데이터 포함)
        total = search_results['total']
        
        # 페이지네이션 링크 생성
        next_page = None
        previous_page = None
        
        if (page * page_size) < total:
            # 다음 페이지가 있음
            next_page = page + 1
        
        if page > 1:
            # 이전 페이지가 있음
            previous_page = page - 1
        
        serializer = iTunesSearchResultSerializer(results, many=True)
        
        return Response({
            'count': total,
            'next': next_page,
            'previous': previous_page,
            'results': serializer.data
        })


class OpenSearchIndexManagementView(APIView):
    """
    OpenSearch 인덱스 관리
    
    - 인덱스 생성/삭제
    - 음악 데이터 인덱싱
    """
    permission_classes = [AllowAny]  # TODO: 관리자 권한으로 변경 필요
    
    @extend_schema(
        summary="OpenSearch 인덱스 생성",
        description="음악 검색용 OpenSearch 인덱스 생성",
        responses={
            200: {'description': '인덱스 생성 성공'},
            500: {'description': '인덱스 생성 실패'}
        },
        tags=['검색']
    )
    def post(self, request):
        """인덱스 생성"""
        if opensearch_service.create_index():
            return Response({
                'message': '인덱스가 성공적으로 생성되었습니다.',
                'index_name': opensearch_service.index_name
            })
        else:
            return Response(
                {'error': '인덱스 생성에 실패했습니다.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @extend_schema(
        summary="OpenSearch 인덱스 삭제",
        description="음악 검색용 OpenSearch 인덱스 삭제",
        responses={
            200: {'description': '인덱스 삭제 성공'},
            500: {'description': '인덱스 삭제 실패'}
        },
        tags=['검색']
    )
    def delete(self, request):
        """인덱스 삭제"""
        if opensearch_service.delete_index():
            return Response({
                'message': '인덱스가 성공적으로 삭제되었습니다.',
                'index_name': opensearch_service.index_name
            })
        else:
            return Response(
                {'error': '인덱스 삭제에 실패했습니다.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class OpenSearchSyncView(APIView):
    """
    DB와 OpenSearch 동기화
    
    - DB의 음악 데이터를 OpenSearch에 인덱싱
    """
    permission_classes = [AllowAny]  # TODO: 관리자 권한으로 변경 필요
    
    @extend_schema(
        summary="DB → OpenSearch 동기화",
        description="""
        DB의 모든 음악 데이터를 OpenSearch에 인덱싱
        
        **주의:** 대량의 데이터를 처리하므로 시간이 오래 걸릴 수 있습니다.
        """,
        responses={
            200: {'description': '동기화 성공'},
            500: {'description': '동기화 실패'}
        },
        tags=['검색']
    )
    def post(self, request):
        """DB 데이터를 OpenSearch에 동기화"""
        from ..models import Music
        
        try:
            # DB에서 모든 음악 조회
            musics = Music.objects.select_related(
                'artist', 'album'
            ).prefetch_related('musictags_set__tag')
            
            music_list = []
            for music in musics:
                # 태그 추출
                tags = [mt.tag.tag_key for mt in music.musictags_set.all() if mt.tag]
                
                music_data = {
                    'music_id': music.music_id,
                    'itunes_id': music.itunes_id,
                    'music_name': music.music_name or '',
                    'artist_name': music.artist.artist_name if music.artist else '',
                    'artist_id': music.artist.artist_id if music.artist else None,
                    'album_name': music.album.album_name if music.album else '',
                    'album_id': music.album.album_id if music.album else None,
                    'genre': music.genre or '',
                    'duration': music.duration or 0,
                    'is_ai': getattr(music, 'is_ai', False),
                    'tags': tags,
                    'lyrics': music.lyrics or '',  # 가사 추가
                    'created_at': music.created_at.isoformat() if music.created_at else None,
                    'play_count': 0,  # TODO: 재생 수 통계 추가
                    'like_count': 0,  # TODO: 좋아요 수 통계 추가
                }
                music_list.append(music_data)
            
            # 일괄 인덱싱
            indexed_count = opensearch_service.bulk_index_music(music_list)
            
            return Response({
                'message': 'DB 데이터가 성공적으로 동기화되었습니다.',
                'total': len(music_list),
                'indexed': indexed_count
            })
            
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"동기화 실패: {e}")
            return Response(
                {'error': f'동기화 중 오류 발생: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
