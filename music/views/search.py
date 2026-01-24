"""
검색 관련 Views - iTunes 기반 음악 검색 및 AI 음악 검색
"""
import re
import random
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from django.utils import timezone
from django.db.models import Q, Prefetch
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes
from ..models import Music, MusicTags, Tags, Artists, Albums, AiInfo
from ..serializers import iTunesSearchResultSerializer, AiMusicSearchResultSerializer, TagMusicSearchSerializer
from ..services import iTunesService
from ..tasks import fetch_artist_image_task, fetch_album_image_task
from .common import MusicPagination


class MusicSearchView(APIView):
    """
    iTunes API 기반 음악 검색

    - 검색어 파싱: 일반 검색어 + 태그 (#으로 구분)
    - iTunes API 우선 호출
    - 태그 필터링 지원

    GET /api/v1/search?q={검색어}&page={num}&page_size={num}
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
            # SoftDeleteManager가 자동으로 is_deleted=False인 레코드만 조회
            itunes_ids = [r['itunes_id'] for r in parsed_results if r.get('itunes_id')]
            existing_music = Music.objects.filter(
                itunes_id__in=itunes_ids
            ).values_list('itunes_id', flat=True)
            
            existing_set = set(existing_music)
            
            # 아티스트 이름으로 DB에서 아티스트 ID 조회 및 생성 (일괄 처리)
            artist_names = list(set([r.get('artist_name') for r in parsed_results if r.get('artist_name')]))
            artist_name_to_id = {}
            if artist_names:
                # DB에 있는 아티스트 조회
                # SoftDeleteManager가 자동으로 is_deleted=False인 레코드만 조회
                existing_artists = Artists.objects.filter(
                    artist_name__in=artist_names
                ).values('artist_id', 'artist_name')
                artist_name_to_id = {a['artist_name']: a['artist_id'] for a in existing_artists}
                
                # DB에 없는 아티스트 생성
                for artist_name in artist_names:
                    if artist_name not in artist_name_to_id:
                        # TrackableMixin이 자동으로 created_at, is_deleted 설정
                        artist, artist_created = Artists.objects.get_or_create(
                            artist_name=artist_name,
                            defaults={
                                'artist_image': '',  # 비동기로 수집
                            }
                        )
                        artist_name_to_id[artist_name] = artist.artist_id
                        
                        # 아티스트 이미지 비동기 수집 (새로 생성되었거나 이미지가 없는 경우)
                        if artist_created or not artist.artist_image:
                            try:
                                fetch_artist_image_task.delay(artist.artist_id, artist_name)
                            except Exception as e:
                                # 태스크 호출 실패해도 기본 저장은 완료되도록 함
                                import logging
                                logging.getLogger(__name__).warning(
                                    f"아티스트 이미지 태스크 호출 실패: {e}"
                                )
            
            # 앨범 이름과 아티스트 조합으로 DB에서 앨범 ID 조회 및 생성
            # 앨범은 아티스트별로 처리해야 하므로 결과별로 처리
            album_key_to_id = {}  # (album_name, artist_id) -> album_id
            
            for item in parsed_results:
                item['in_db'] = item.get('itunes_id') in existing_set
                item['has_matching_tags'] = False  # 기본값
                
                # 아티스트 ID 추가 (없으면 생성했으므로 항상 있음)
                artist_name = item.get('artist_name')
                item['artist_id'] = artist_name_to_id.get(artist_name) if artist_name else None
                
                # 앨범 ID 추가 (아티스트가 있어야 앨범 생성 가능)
                album_name = item.get('album_name')
                artist_id = item['artist_id']
                
                if album_name and artist_id:
                    album_key = (album_name, artist_id)
                    if album_key not in album_key_to_id:
                        # 앨범 조회 또는 생성
                        try:
                            # SoftDeleteManager가 자동으로 is_deleted=False인 레코드만 조회
                            artist = Artists.objects.get(artist_id=artist_id)
                            # TrackableMixin이 자동으로 created_at, is_deleted 설정
                            album, album_created = Albums.objects.get_or_create(
                                album_name=album_name,
                                artist=artist,
                                defaults={
                                    'album_image': '',  # 비동기로 수집
                                }
                            )
                            album_key_to_id[album_key] = album.album_id
                            
                            # 앨범 이미지 비동기 수집 (새로 생성되었거나 이미지가 없는 경우)
                            album_image_url = item.get('album_image', '')
                            if album_created or not album.album_image:
                                try:
                                    # artist_name도 전달하여 YouTube Music 검색 정확도 향상
                                    artist_name = item.get('artist_name', '')
                                    fetch_album_image_task.delay(
                                        album.album_id, 
                                        album_name, 
                                        album_image_url,  # iTunes fallback용
                                        artist_name  # YouTube Music 검색용
                                    )
                                except Exception as e:
                                    # 태스크 호출 실패해도 기본 저장은 완료되도록 함
                                    import logging
                                    logging.getLogger(__name__).warning(
                                        f"앨범 이미지 태스크 호출 실패: {e}"
                                    )
                        except Artists.DoesNotExist:
                            album_key_to_id[album_key] = None
                    
                    item['album_id'] = album_key_to_id[album_key]
                else:
                    item['album_id'] = None
            
            results = parsed_results
        
        # 2. 태그가 있으면 필터링
        if tags:
            # DB에서 태그를 가진 곡의 itunes_id 찾기
            # SoftDeleteManager가 자동으로 is_deleted=False인 레코드만 조회
            tag_objects = Tags.objects.filter(tag_key__in=tags)
            
            music_ids_with_tags = MusicTags.objects.filter(
                tag__in=tag_objects
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
                # SoftDeleteManager가 자동으로 is_deleted=False인 레코드만 조회
                musics = Music.objects.filter(
                    itunes_id__in=itunes_ids_with_tags
                ).select_related('artist', 'album')
                
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
                        'in_db': True,
                        'has_matching_tags': True,
                    })
        
        
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


class AiMusicSearchView(APIView):
    """
    AI 음악 전용 검색 API
    
    - AiInfo 테이블에서 검색 (노래 제목과 input_prompt 필드)
    - is_ai=True인 음악만 반환
    - 검색된 AI 음악 결과들을 반환
    
    GET /api/music/search-ai/?q={검색어}
    """
    permission_classes = [AllowAny]
    pagination_class = MusicPagination
    
    @extend_schema(
        summary="AI 음악 검색",
        description="""
        AI로 생성된 음악 전용 검색 API

        **검색 대상:**
        - 노래 제목 (Music.music_name)
        - AI 생성 프롬프트 (AiInfo.input_prompt)

        **검색 조건:**
        - AiInfo 레코드가 있는 음악만 검색 (AI 생성 음악)
        - 노래 제목 또는 프롬프트에 검색어가 포함된 경우 (대소문자 구분 없음)
        - 하나의 검색어로 통합 검색

        **정렬:**
        - 최신 생성 순 (created_at DESC)
        """,
        parameters=[
            OpenApiParameter(
                name='q',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='검색어 (노래 제목 또는 AI 생성 프롬프트)',
                required=True,
                examples=[
                    OpenApiExample(
                        name='노래 제목 검색',
                        value='사랑',
                        description='노래 제목에 "사랑"이 포함된 AI 음악 검색'
                    ),
                    OpenApiExample(
                        name='프롬프트 검색',
                        value='신나는',
                        description='AI 생성 프롬프트에 "신나는"이 포함된 음악 검색'
                    ),
                ]
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
            200: AiMusicSearchResultSerializer(many=True),
            400: {'description': 'Bad Request - q 파라미터 필요'},
        },
        tags=['검색']
    )
    def get(self, request):
        """AI 음악 검색 처리"""
        query = request.query_params.get('q', '').strip()
        
        if not query:
            return Response(
                {'error': 'q 파라미터가 필요합니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # AI 음악만 검색 (AiInfo가 있는 음악)
        # 노래 제목과 프롬프트를 하나의 검색어로 통합 검색
        music_queryset = Music.objects.filter(
            # AiInfo 레코드가 있는 음악만 (AI 생성 음악)
            aiinfo__isnull=False
        ).filter(
            # 삭제되지 않은 AiInfo만
            aiinfo__is_deleted__in=[False, None]
        ).filter(
            # 노래 제목 또는 AI 프롬프트에서 검색 (통합 검색)
            Q(music_name__icontains=query) |
            Q(aiinfo__input_prompt__icontains=query)
        ).select_related(
            'artist',  # 아티스트 정보
            'album',   # 앨범 정보
        ).prefetch_related(
            Prefetch(
                'aiinfo_set',
                queryset=AiInfo.objects.filter(is_deleted__in=[False, None]),
                to_attr='ai_info_list'
            )
        ).distinct().order_by('-created_at')  # 최신순 정렬
        
        # 페이지네이션
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(music_queryset, request)
        
        if page is not None:
            serializer = AiMusicSearchResultSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
        
        serializer = AiMusicSearchResultSerializer(music_queryset, many=True)
        return Response({
            'count': music_queryset.count(),
            'results': serializer.data
        })


class TagMusicSearchView(APIView):
    """
    태그로 음악 검색
    
    - 최대 3개의 태그를 가진 모든 음악 반환 (OR 조건)
    - 중복 결과 제거
    - music_id, album_name, artist_name, 앨범 이미지 정보 포함
    
    GET /api/v1/search/tags?tag={tag_key}&tag={tag_key2}&tag={tag_key3}&page={num}&page_size={num}
    """
    permission_classes = [AllowAny]
    pagination_class = MusicPagination
    
    @extend_schema(
        summary="태그로 음악 검색",
        description="""
        최대 3개의 태그를 가진 모든 음악을 검색합니다 (OR 조건).
        여러 태그 중 하나라도 가진 음악이 모두 반환되며, 중복 결과는 자동으로 제거됩니다.
        결과는 랜덤으로 반환되며, 최대 150개까지만 반환됩니다.
        
        **반환 정보:**
        - music_id: 음악 ID
        - music_name: 음악 제목
        - album_name: 앨범명
        - artist_name: 아티스트명
        - image_large_square: 360x360 사각형 이미지
        - image_square: 220x220 사각형 이미지
        - album_image: 원본 앨범 이미지
        - score: 태그 밀접도 점수 (music_tags.score, 높을수록 태그와 관련성이 높음)
        
        **주의사항:**
        - 삭제되지 않은 음악과 태그만 반환됩니다
        - 최대 3개의 태그까지 검색 가능합니다
        - 중복된 음악은 자동으로 제거됩니다 (여러 태그에 속한 경우 가장 높은 score 유지)
        - 존재하지 않는 태그는 무시됩니다
        - 최대 150개까지만 반환됩니다 (랜덤 순서, 중복 없음)
        """,
        parameters=[
            OpenApiParameter(
                name='tag',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='태그 이름 (tag_key), 최대 3개까지 가능 (쉼표로 구분)',
                required=True,
                examples=[
                    OpenApiExample(
                        name='단일 태그 검색',
                        value='christmas',
                        description='"christmas" 태그를 가진 모든 음악 검색'
                    ),
                    OpenApiExample(
                        name='여러 태그 검색',
                        value='christmas,신나는,겨울',
                        description='?tag=christmas,신나는,겨울 - 3개 태그 중 하나라도 가진 음악 검색 (쉼표로 구분)'
                    ),
                ]
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
                description='페이지 크기 (최대 150)',
                required=False,
                default=20
            ),
        ],
        responses={
            200: TagMusicSearchSerializer(many=True),
            400: {'description': 'Bad Request - tag 파라미터 필요'},
            404: {'description': 'Not Found - 태그를 찾을 수 없음'},
        },
        tags=['검색']
    )
    def get(self, request):
        """태그로 음악 검색 처리 (최대 3개 태그, 중복 제거)"""
        # 태그 파라미터 받기 (쉼표로 구분)
        tag_param = request.query_params.get('tag', '').strip()
        
        if not tag_param:
            return Response(
                {'error': 'tag 파라미터가 필요합니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 쉼표로 구분된 태그 파싱
        tag_keys = [tag.strip() for tag in tag_param.split(',') if tag.strip()]
        
        # 최대 3개까지만 허용
        if len(tag_keys) > 3:
            return Response(
                {'error': '태그는 최대 3개까지 검색할 수 있습니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 1. 태그 존재 여부 확인 (존재하지 않는 태그는 무시)
        tags = Tags.objects.filter(
            tag_key__in=tag_keys,
            is_deleted=False
        )
        
        if not tags.exists():
            return Response(
                {'error': f'태그를 찾을 수 없습니다: {", ".join(tag_keys)}'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # 2. 각 태그에 대해 음악 조회 (OR 조건)
        # MusicTags를 통해 Music을 직접 조회 (album, artist 포함)
        music_tags = MusicTags.objects.filter(
            tag__in=tags,
            is_deleted=False
        ).select_related(
            'music',      # 음악 정보
            'music__album',  # 앨범 정보
            'music__artist'  # 아티스트 정보
        )
        
        # 3. 삭제되지 않은 음악만 필터링하고 중복 제거 (music_id 기준)
        # 중복 시 가장 높은 score를 가진 것을 유지
        music_dict = {}  # music_id를 키로 사용하여 중복 제거
        for mt in music_tags:
            if mt.music and not mt.music.is_deleted:
                music_id = mt.music.music_id
                # 중복된 경우 더 높은 score를 가진 것을 유지
                if music_id not in music_dict:
                    music_dict[music_id] = {
                        'music': mt.music,
                        'score': mt.score if mt.score is not None else 0.0
                    }
                else:
                    # 기존 score보다 높으면 업데이트
                    if mt.score is not None and mt.score > music_dict[music_id]['score']:
                        music_dict[music_id]['score'] = mt.score
        
        # 리스트로 변환
        music_list = list(music_dict.values())
        
        # 랜덤으로 섞기 (중복 없음 보장)
        random.shuffle(music_list)
        
        # 최대 150개로 제한
        music_list = music_list[:150]
        
        # queryset처럼 사용하기 위해 리스트를 사용
        # 페이지네이션을 위해 리스트를 사용
        
        # 4. 결과 데이터 생성
        results = []
        for item in music_list:
            music = item['music']
            score = item['score']
            album = music.album
            artist = music.artist
            
            results.append({
                'music_id': music.music_id,
                'music_name': music.music_name,
                'album_name': album.album_name if album else None,
                'artist_name': artist.artist_name if artist else None,
                'image_large_square': album.image_large_square if album else None,
                'image_square': album.image_square if album else None,
                'album_image': album.album_image if album else None,
                'score': score,
            })
        
        # 5. 페이지네이션
        paginator = self.pagination_class()
        # 리스트를 페이지네이션하기 위해 임시로 queryset처럼 사용
        # 페이지네이션은 리스트를 직접 처리할 수 없으므로 수동으로 처리
        page = request.query_params.get('page', 1)
        page_size = request.query_params.get('page_size', 20)
        
        try:
            page = int(page)
            page_size = int(page_size)
            page_size = min(page_size, 150)  # 최대 150개
        except (ValueError, TypeError):
            page = 1
            page_size = 20
        
        # 페이지네이션 계산
        total_count = len(results)
        start = (page - 1) * page_size
        end = start + page_size
        paginated_results = results[start:end]
        
        # Serializer로 변환
        serializer = TagMusicSearchSerializer(paginated_results, many=True)
        
        # 페이지네이션 메타데이터 생성
        next_page = None
        previous_page = None
        
        if end < total_count:
            next_page = page + 1
        if start > 0:
            previous_page = page - 1
        
        # URL 파라미터 재구성 (여러 태그 포함, 쉼표로 구분)
        base_url = request.build_absolute_uri().split('?')[0]
        tag_params = f"tag={','.join(tag_keys)}"
        
        # 응답 데이터 구성
        response_data = {
            'count': total_count,
            'next': f"{base_url}?{tag_params}&page={next_page}&page_size={page_size}" if next_page else None,
            'previous': f"{base_url}?{tag_params}&page={previous_page}&page_size={page_size}" if previous_page else None,
            'results': serializer.data
        }
        
        return Response(response_data)
