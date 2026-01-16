"""
검색 관련 Views - iTunes 기반 음악 검색
"""
import re
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes
from ..models import Music, MusicTags, Tags, Artists, Albums
from ..serializers import iTunesSearchResultSerializer
from ..services import iTunesService
from .common import MusicPagination


class MusicSearchView(APIView):
    """
    iTunes API 기반 음악 검색
    
    - 검색어 파싱: 일반 검색어 + 태그 (#으로 구분)
    - iTunes API 우선 호출
    - 태그 필터링 지원
    - AI 필터링 지원
    
    GET /api/v1/search?q={검색어}&exclude_ai={true|false}&page={num}&page_size={num}
    """
    permission_classes = [AllowAny]
    pagination_class = MusicPagination
    
    def parse_search_query(self, query_string):
        """
        검색어 파싱: 일반 검색어와 태그 분리
        
        규칙: '# ' (해시+공백) 패턴만 태그로 인식
        
        예시:
        - "아이유" → {"term": "아이유", "tags": []}
        - "# christmas" → {"term": None, "tags": ["christmas"]}
        - "아이유 # christmas" → {"term": "아이유", "tags": ["christmas"]}
        - "아이유 # christmas # 신나는" → {"term": "아이유", "tags": ["christmas", "신나는"]}
        - "C#" → {"term": "C#", "tags": []} (공백 없으면 일반 텍스트)
        - "I'm #1" → {"term": "I'm #1", "tags": []} (공백 없으면 일반 텍스트)
        """
        if not query_string:
            return {"term": None, "tags": []}
        
        # '# ' (해시+공백) 뒤의 단어들을 태그로 추출
        tag_pattern = r'#\s+(\w+)'
        tags = re.findall(tag_pattern, query_string)
        
        # 태그 패턴 제거한 나머지가 검색어
        term = re.sub(tag_pattern, '', query_string).strip()
        term = term if term else None
        
        return {"term": term, "tags": tags}
    
    @extend_schema(
        summary="iTunes 음악 검색",
        description="""
        iTunes API를 사용한 음악 검색
        
        **검색 문법:**
        - `아이유` - 일반 검색
        - `# christmas` - 태그만 검색 (# 뒤 공백 필수)
        - `아이유 # christmas` - 검색어 + 태그 (AND 조건)
        - `C#` - 일반 검색 (공백 없으면 태그 아님)
        
        **태그 규칙:**
        - '# ' (해시+공백) 패턴만 태그로 인식
        - 프론트: # 입력 → 스페이스바 → 태그 입력 모드
        
        **동작:**
        1. 일반 검색어가 있으면 iTunes API 호출
        2. 태그가 있으면 DB에서 해당 태그를 가진 곡과 매칭
        3. exclude_ai=true 시 AI 생성곡 제외
        """,
        parameters=[
            OpenApiParameter(
                name='q',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='검색어 (# 뒤 공백 있어야 태그 인식)',
                required=True,
                examples=[
                    OpenApiExample(
                        name='일반 검색',
                        value='아이유',
                        description='iTunes API로 아티스트명/곡명 검색'
                    ),
                    OpenApiExample(
                        name='태그 검색',
                        value='# christmas',
                        description='DB에서 태그만 검색 (공백 필수)'
                    ),
                    OpenApiExample(
                        name='복합 검색',
                        value='아이유 # christmas',
                        description='검색어 + 태그 (AND 조건, 공백 필수)'
                    ),
                    OpenApiExample(
                        name='일반 텍스트 (태그 아님)',
                        value='C#',
                        description='공백 없으면 일반 검색 (C# 프로그래밍 음악 등)'
                    ),
                ]
            ),
            OpenApiParameter(
                name='exclude_ai',
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                description='AI 생성곡 제외 여부 (기본값: false - AI곡 포함)\n응답의 is_ai 필드로 클라이언트 사이드 필터링도 가능',
                required=False,
                default=False
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
            503: {'description': 'Service Unavailable - iTunes API 오류'}
        },
        tags=['검색']
    )
    def get(self, request):
        """음악 검색 처리"""
        query = request.query_params.get('q', '')
        exclude_ai = request.query_params.get('exclude_ai', 'false').lower() == 'true'
        
        if not query:
            return Response(
                {'error': 'q 파라미터가 필요합니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 검색어 파싱
        parsed = self.parse_search_query(query)
        term = parsed['term']
        tags = parsed['tags']
        
        results = []
        
        # 1. 일반 검색어가 있으면 iTunes API 호출
        if term:
            itunes_data = iTunesService.search(term, limit=50)
            
            if 'error' in itunes_data:
                return Response(
                    {'error': f'iTunes API 오류: {itunes_data["error"]}'},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE
                )
            
            # iTunes 결과 파싱
            parsed_results = iTunesService.parse_search_results(itunes_data.get('results', []))
            
            # DB에 이미 있는지 확인
            itunes_ids = [r['itunes_id'] for r in parsed_results if r.get('itunes_id')]
            existing_music = Music.objects.filter(
                itunes_id__in=itunes_ids,
                is_deleted=False
            ).values_list('itunes_id', flat=True)
            
            existing_set = set(existing_music)
            
            # 아티스트 이름으로 DB에서 아티스트 ID 조회 (일괄 처리)
            artist_names = [r.get('artist_name') for r in parsed_results if r.get('artist_name')]
            artist_name_to_id = {}
            if artist_names:
                artists = Artists.objects.filter(
                    artist_name__in=artist_names,
                    is_deleted__in=[False, None]
                ).values('artist_id', 'artist_name')
                artist_name_to_id = {a['artist_name']: a['artist_id'] for a in artists}
            
            # 앨범 이름으로 DB에서 앨범 ID 조회 (일괄 처리)
            album_names = [r.get('album_name') for r in parsed_results if r.get('album_name')]
            album_name_to_id = {}
            if album_names:
                albums = Albums.objects.filter(
                    album_name__in=album_names,
                    is_deleted__in=[False, None]
                ).values('album_id', 'album_name')
                album_name_to_id = {a['album_name']: a['album_id'] for a in albums}
            
            for item in parsed_results:
                item['in_db'] = item.get('itunes_id') in existing_set
                item['has_matching_tags'] = False  # 기본값
                # 아티스트 ID 추가 (DB에 있으면)
                item['artist_id'] = artist_name_to_id.get(item.get('artist_name'))
                # 앨범 ID 추가 (DB에 있으면)
                item['album_id'] = album_name_to_id.get(item.get('album_name'))
            
            results = parsed_results
        
        # 2. 태그가 있으면 필터링
        if tags:
            # DB에서 태그를 가진 곡의 itunes_id 찾기
            tag_objects = Tags.objects.filter(
                tag_key__in=tags,
                is_deleted=False
            )
            
            music_ids_with_tags = MusicTags.objects.filter(
                tag__in=tag_objects,
                is_deleted=False
            ).values_list('music__itunes_id', flat=True).distinct()
            
            itunes_ids_with_tags = set(music_ids_with_tags)
            
            if term:
                # iTunes 결과 + 태그 필터링
                for item in results:
                    if item.get('itunes_id') in itunes_ids_with_tags:
                        item['has_matching_tags'] = True
                
                # 태그 매칭된 것만 필터 (AND 로직)
                results = [r for r in results if r['has_matching_tags']]
            else:
                # 태그만 검색 (#christmas)
                # DB에서 해당 태그를 가진 음악 조회
                musics = Music.objects.filter(
                    itunes_id__in=itunes_ids_with_tags,
                    is_deleted=False
                ).select_related('artist', 'album')
                
                if exclude_ai:
                    musics = musics.filter(is_ai=False)
                
                # Music 객체를 iTunes 검색 결과 형식으로 변환
                results = []
                for music in musics:
                    results.append({
                        'itunes_id': music.itunes_id,
                        'music_name': music.music_name,
                        'artist_name': music.artist.artist_name if music.artist else '',
                        'artist_id': music.artist.artist_id if music.artist else None,
                        'album_name': music.album.album_name if music.album else '',
                        'album_id': music.album.album_id if music.album else None,
                        'genre': music.genre or '',
                        'duration': music.duration,
                        'audio_url': music.audio_url,
                        'album_image': music.album.album_image if music.album else '',
                        'is_ai': music.is_ai,
                        'in_db': True,
                        'has_matching_tags': True,
                    })
        
        # 3. AI 필터 적용
        if exclude_ai:
            results = [r for r in results if not r.get('is_ai', False)]
        
        # 4. 페이지네이션
        paginator = self.pagination_class()
        
        # 리스트를 페이지네이션하기 위해 임시로 변환
        page = paginator.paginate_queryset(results, request)
        
        if page is not None:
            serializer = iTunesSearchResultSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
        
        serializer = iTunesSearchResultSerializer(results, many=True)
        return Response({
            'count': len(results),
            'results': serializer.data
        })
