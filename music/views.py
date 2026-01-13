"""
Music 앱의 View 모듈
음악, 인증 관련 API 엔드포인트 처리
"""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.hashers import check_password
from .models import Users, Music, MusicLikes, MusicTags, Tags, Artists, Albums
from .serializers import (
    MusicDetailSerializer, 
    MusicLikeSerializer,
    UserRegisterSerializer,
    UserLoginSerializer,
    iTunesSearchResultSerializer
)
from .services import iTunesService
from django.db import transaction
from django.utils import timezone
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes


class MusicPagination(PageNumberPagination):
    """음악 목록 페이지네이션"""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class MusicLikeView(APIView):
    """
    음악 좋아요 등록/취소 API
    
    - POST: 좋아요 등록
    - DELETE: 좋아요 취소
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, music_id):
        """
        좋아요 등록
        POST /api/v1/tracks/{musicId}/likes
        """
        # 음악 존재 확인
        music = get_object_or_404(Music, music_id=music_id, is_deleted=False)
        
        # 이미 좋아요가 있는지 확인
        like, created = MusicLikes.objects.get_or_create(
            user=request.user,
            music=music,
            defaults={'is_deleted': False}
        )
        
        if not created and like.is_deleted:
            # 삭제된 좋아요를 복구
            like.is_deleted = False
            like.save()
            created = True
        elif not created:
            # 이미 좋아요가 있음
            return Response(
                {
                    'message': '이미 좋아요를 누른 음악입니다.',
                    'music_id': music_id,
                    'is_liked': True
                },
                status=status.HTTP_200_OK
            )
        
        serializer = MusicLikeSerializer({
            'message': '좋아요가 등록되었습니다.',
            'music_id': music_id,
            'is_liked': True
        })
        
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    def delete(self, request, music_id):
        """
        좋아요 취소
        DELETE /api/v1/tracks/{musicId}/likes
        """
        # 음악 존재 확인
        music = get_object_or_404(Music, music_id=music_id, is_deleted=False)
        
        # 좋아요 찾기
        try:
            like = MusicLikes.objects.get(
                user=request.user,
                music=music,
                is_deleted=False
            )
            like.is_deleted = True
            like.save()
            
            serializer = MusicLikeSerializer({
                'message': '좋아요가 취소되었습니다.',
                'music_id': music_id,
                'is_liked': False
            })
            
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except MusicLikes.DoesNotExist:
            return Response(
                {
                    'message': '좋아요를 누르지 않은 음악입니다.',
                    'music_id': music_id,
                    'is_liked': False
                },
                status=status.HTTP_404_NOT_FOUND
            )


class RegisterView(APIView):
    """
    회원가입 API
    POST /api/v1/auth/users/
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        """이메일, 비밀번호, 닉네임으로 회원가입"""
        serializer = UserRegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response({
                'message': '회원가입 성공',
                'user_id': user.user_id,
                'email': user.email,
                'nickname': user.nickname
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    """
    로그인 API
    POST /api/v1/auth/tokens/
    이메일/비밀번호 검증 후 JWT 토큰(Access, Refresh) 발급
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        """로그인 처리 및 JWT 토큰 발급"""
        serializer = UserLoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        email = serializer.validated_data['email']
        password = serializer.validated_data['password']
        
        # 사용자 조회 (삭제되지 않은 사용자만)
        try:
            user = Users.objects.get(email=email, is_deleted=False)
        except Users.DoesNotExist:
            return Response(
                {'error': '이메일 또는 비밀번호가 올바르지 않습니다.'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # 비밀번호 검증
        if not check_password(password, user.password):
            return Response(
                {'error': '이메일 또는 비밀번호가 올바르지 않습니다.'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # JWT 토큰 생성 (Access + Refresh)
        refresh = RefreshToken()
        refresh['user_id'] = user.user_id
        refresh['email'] = user.email
        
        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user_id': user.user_id,
            'email': user.email,
            'nickname': user.nickname
        }, status=status.HTTP_200_OK)


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
        
        import re
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
            
            for item in parsed_results:
                item['in_db'] = item.get('itunes_id') in existing_set
                item['has_matching_tags'] = False  # 기본값
            
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
                        'album_name': music.album.album_name if music.album else '',
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


class MusicDetailView(APIView):
    """
    iTunes ID 기반 음악 상세 조회
    
    - DB에 있으면: DB 데이터 반환 (태그, 좋아요 포함)
    - DB에 없으면: iTunes Lookup API 호출 → DB에 저장 → 반환
    
    GET /api/v1/tracks/{itunes_id}
    """
    permission_classes = [AllowAny]
    
    @transaction.atomic
    def create_music_from_itunes(self, itunes_data):
        """
        iTunes 데이터로부터 Music 객체 생성
        Artist, Album도 함께 생성/조회
        """
        # Artist 생성 또는 조회
        artist_name = itunes_data.get('artist_name', '')
        artist = None
        if artist_name:
            artist, _ = Artists.objects.get_or_create(
                artist_name=artist_name,
                defaults={
                    'artist_image': itunes_data.get('artist_image', ''),
                    'created_at': timezone.now(),
                    'is_deleted': False,
                }
            )
        
        # Album 생성 또는 조회
        album_name = itunes_data.get('album_name', '')
        album = None
        if album_name and artist:
            album, _ = Albums.objects.get_or_create(
                album_name=album_name,
                artist=artist,
                defaults={
                    'album_image': itunes_data.get('album_image', ''),
                    'created_at': timezone.now(),
                    'is_deleted': False,
                }
            )
        
        # Music 생성
        music = Music.objects.create(
            itunes_id=itunes_data.get('itunes_id'),
            music_name=itunes_data.get('music_name', ''),
            artist=artist,
            album=album,
            genre=itunes_data.get('genre', ''),
            duration=itunes_data.get('duration'),
            audio_url=itunes_data.get('audio_url', ''),
            is_ai=False,  # iTunes 곡은 기성곡
            created_at=timezone.now(),
            is_deleted=False,
        )
        
        return music
    
    @extend_schema(
        summary="iTunes ID로 음악 상세 조회",
        description="""
        iTunes ID를 사용하여 음악 상세 정보 조회
        
        **동작:**
        - DB에 이미 있으면: DB 데이터 반환 (200 OK)
        - DB에 없으면: iTunes Lookup API 호출 → DB 저장 → 반환 (201 Created)
        
        **저장 내용:**
        - Artist, Album 자동 생성/조회
        - Music 정보 저장
        - 태그는 빈 상태로 저장 (추후 수동 추가 필요)
        """,
        parameters=[
            OpenApiParameter(
                name='itunes_id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description='iTunes Track ID (검색 결과에서 확인 가능)',
                required=True,
                examples=[
                    OpenApiExample(
                        name='아이유 - Never Ending Story',
                        value=1815869481,
                        description='아이유의 Never Ending Story iTunes ID'
                    )
                ]
            )
        ],
        responses={
            200: MusicDetailSerializer,
            201: MusicDetailSerializer,
            404: {'description': 'Not Found - iTunes에서 해당 ID를 찾을 수 없음'},
            500: {'description': 'Internal Server Error - 저장 중 오류 발생'}
        },
        tags=['음악 상세']
    )
    def get(self, request, itunes_id):
        """iTunes ID로 음악 상세 조회"""
        
        # 1. DB에서 조회
        try:
            music = Music.objects.select_related('artist', 'album').get(
                itunes_id=itunes_id,
                is_deleted=False
            )
            # DB에 있으면 바로 반환
            serializer = MusicDetailSerializer(music)
            return Response(serializer.data)
            
        except Music.DoesNotExist:
            # 2. DB에 없으면 iTunes API 호출
            itunes_data = iTunesService.lookup(itunes_id)
            
            if not itunes_data:
                return Response(
                    {'error': '해당 iTunes ID의 음악을 찾을 수 없습니다.'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # 3. iTunes 데이터 파싱
            parsed_data = iTunesService.parse_track_data(itunes_data)
            
            # 4. DB에 저장
            try:
                music = self.create_music_from_itunes(parsed_data)
                
                # 5. 저장된 데이터 반환
                serializer = MusicDetailSerializer(music)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
                
            except Exception as e:
                return Response(
                    {'error': f'음악 저장 중 오류 발생: {str(e)}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
