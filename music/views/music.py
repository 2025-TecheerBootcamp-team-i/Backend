"""
음악 상세 관련 Views - iTunes ID 기반 상세 조회, 음악 재생, 태그 조회
"""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from django.db import transaction
from django.utils import timezone
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample, OpenApiResponse
from drf_spectacular.types import OpenApiTypes
from ..models import Music, Artists, Albums, MusicTags
from ..serializers import MusicDetailSerializer, MusicPlaySerializer, MusicTagGraphSerializer
from ..serializers.base import TagSerializer
from ..services import iTunesService
from ..services.internal.music_tag_service import MusicTagService
from ..tasks import fetch_artist_image_task, fetch_album_image_task, fetch_lyrics_task, save_itunes_track_to_db_task


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
        
        추가로 Celery 비동기 태스크를 호출하여:
        - Wikidata에서 아티스트 이미지 조회
        - LRCLIB에서 가사 조회
        """
        artist_name = itunes_data.get('artist_name', '')
        artist = None
        artist_created = False
        
        if artist_name:
            # Artist 생성/조회 (이미지는 비동기로 수집하므로 빈 값으로 저장)
            # TrackableMixin이 자동으로 created_at, is_deleted 설정
            artist, artist_created = Artists.objects.get_or_create(
                artist_name=artist_name,
                defaults={
                    'artist_image': '',  # Wikidata에서 비동기로 수집
                }
            )
        
        # Album 생성 또는 조회
        album_name = itunes_data.get('album_name', '')
        album = None
        album_created = False
        if album_name and artist:
            # TrackableMixin이 자동으로 created_at, is_deleted 설정
            album, album_created = Albums.objects.get_or_create(
                album_name=album_name,
                artist=artist,
                defaults={
                    'album_image': '',  # 비동기로 수집
                }
            )
            
            # 앨범 이미지 비동기 수집 (새로 생성되었거나 이미지가 없는 경우)
            album_image_url = itunes_data.get('album_image', '')
            if album_image_url and (album_created or not album.album_image):
                try:
                    # artist_name 전달하여 YouTube Music 검색 정확도 향상
                    fetch_album_image_task.delay(
                        album.album_id, 
                        album_name, 
                        album_image_url,  # iTunes fallback용
                        artist_name  # YouTube Music 검색용
                    )
                except Exception as e:
                    # 태스크 호출 실패해도 기본 저장은 완료되도록 함
                    import logging
                    logging.getLogger(__name__).warning(f"앨범 이미지 태스크 호출 실패: {e}")
        
        # Music 생성 (가사는 비동기로 수집하므로 빈 값으로 저장)
        # TrackableMixin이 자동으로 created_at, is_deleted 설정
        music = Music.objects.create(
            itunes_id=itunes_data.get('itunes_id'),
            music_name=itunes_data.get('music_name', ''),
            artist=artist,
            album=album,
            genre=itunes_data.get('genre', ''),
            duration=itunes_data.get('duration'),
            audio_url=itunes_data.get('audio_url', ''),
            lyrics=None,  # LRCLIB에서 비동기로 수집
            is_ai=False,
        )
        
        # 비동기 태스크 호출: 아티스트 이미지 수집 (새로 생성되었거나 이미지가 없는 경우)
        if artist and (artist_created or not artist.artist_image):
            try:
                fetch_artist_image_task.delay(artist.artist_id, artist.artist_name)
            except Exception as e:
                # 태스크 호출 실패해도 기본 저장은 완료되도록 함
                import logging
                logging.getLogger(__name__).warning(f"아티스트 이미지 태스크 호출 실패: {e}")
        
        # 비동기 태스크 호출: 가사 수집
        if artist_name and itunes_data.get('music_name'):
            try:
                fetch_lyrics_task.delay(
                    music.music_id,
                    artist_name,
                    itunes_data.get('music_name', ''),
                    itunes_data.get('duration')
                )
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"가사 태스크 호출 실패: {e}")
        
        return music
    
    @extend_schema(
        summary="iTunes ID로 음악 상세 조회",
        description="""
        iTunes ID를 사용하여 음악 상세 정보 조회
        
        **동작 (성능 최적화):**
        - DB에 이미 있으면: DB 데이터 반환 (200 OK)
        - DB에 없으면: iTunes Lookup API 호출 → 즉시 응답 (202 Accepted)
          - DB 저장은 백그라운드로 비동기 처리 (50-200ms 절약)
        
        **저장 내용 (백그라운드):**
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
            202: {'description': 'Accepted - iTunes 데이터 반환 (DB 저장은 백그라운드 처리 중)'},
            404: {'description': 'Not Found - iTunes에서 해당 ID를 찾을 수 없음'}
        },
        tags=['음악 상세']
    )
    def get(self, request, itunes_id):
        """iTunes ID로 음악 상세 조회 (방안 2: DB 저장 비동기 처리)"""
        
        # 1. DB에서 조회 (이미 저장된 곡인지 확인)
        # SoftDeleteManager가 자동으로 is_deleted=False인 레코드만 조회
        try:
            music = Music.objects.select_related('artist', 'album').get(itunes_id=itunes_id)
            # DB에 이미 있으면 바로 반환 (빠른 응답)
            serializer = MusicDetailSerializer(music)
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Music.DoesNotExist:
            # 2. DB에 없으면 iTunes API 호출 (외부 API 호출, 500ms~2초 소요)
            itunes_data = iTunesService.lookup(itunes_id)
            
            if not itunes_data:
                return Response(
                    {'error': '해당 iTunes ID의 음악을 찾을 수 없습니다.'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # 3. iTunes 데이터 파싱 (약 5-10ms)
            parsed_data = iTunesService.parse_track_data(itunes_data)
            
            # 4. 🚀 핵심: DB 저장은 Celery 백그라운드로 비동기 처리
            #    - DB 저장 시간(50-200ms) 절약
            #    - 사용자는 즉시 응답 받음
            #    - Celery 워커가 백그라운드에서 DB에 저장 처리
            save_itunes_track_to_db_task.delay(parsed_data)
            
            # 5. 파싱된 데이터를 즉시 응답 반환 (DB 저장 완료를 기다리지 않음)
            #    - 프론트엔드는 이 데이터로 바로 음악 재생 가능
            #    - DB 저장은 백그라운드에서 진행 중
            response_data = {
                'itunes_id': parsed_data.get('itunes_id'),
                'music_name': parsed_data.get('music_name'),
                'artist': {
                    'artist_name': parsed_data.get('artist_name'),
                    'artist_image': parsed_data.get('artist_image'),
                },
                'album': {
                    'album_name': parsed_data.get('album_name'),
                    'album_image': parsed_data.get('album_image'),
                },
                'genre': parsed_data.get('genre'),
                'duration': parsed_data.get('duration'),
                'audio_url': parsed_data.get('audio_url'),  # 30초 미리듣기 URL
                'is_ai': False,  # iTunes 곡은 AI 생성곡이 아님
                'tags': [],  # 새로 저장되는 곡은 태그 없음
                'created_at': timezone.now().isoformat(),
            }
            
            # 202 Accepted: 요청을 수락했지만 처리가 완료되지 않음 (비동기 처리 중)
            return Response(response_data, status=status.HTTP_202_ACCEPTED)


class MusicPlayView(APIView):
    """
    음악 재생 정보 조회 (Music 도메인)
    - GET: 음악 재생에 필요한 정보 반환 (audio_url, 가사 등)
    - 로그는 저장하지 않음 (PlayLog 도메인과 분리)
    """
    permission_classes = [AllowAny]
    
    @extend_schema(
        summary="음악 재생 정보 조회",
        description="""
        음악 재생에 필요한 정보를 조회합니다.
        
        **반환 정보:**
        - music_id, music_name, artist_name, album_name
        - audio_url (스트리밍 URL)
        - duration (재생 시간, 초 단위)
        - album_image (앨범 커버 이미지)
        - lyrics (가사, 있는 경우)
        
        **주의:**
        - GET 요청은 로그를 저장하지 않습니다
        - 실제 재생 시에는 POST 요청으로 로그를 기록해야 합니다
        """,
        parameters=[
            OpenApiParameter(
                name='music_id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description='음악 ID',
                required=True,
                examples=[
                    OpenApiExample(
                        name='예시',
                        value=1,
                        description='음악 ID 예시'
                    )
                ]
            )
        ],
        responses={
            200: MusicPlaySerializer,
            404: OpenApiResponse(description='Not Found - 음악을 찾을 수 없음'),
        },
        tags=['음악 재생']
    )
    def get(self, request, music_id):
        """음악 재생 정보 조회 (로그 저장 안 함)"""
        
        # 1. 음악 정보 조회
        # SoftDeleteManager가 자동으로 is_deleted=False인 레코드만 조회
        try:
            music = Music.objects.select_related('artist', 'album').get(music_id=music_id)
        except Music.DoesNotExist:
            return Response(
                {'error': '음악을 찾을 수 없습니다.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # 2. audio_url 검증
        if not music.audio_url:
            return Response(
                {'error': '이 음악은 재생할 수 없습니다. (audio_url 없음)'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # 3. 음악 재생 정보 반환 (로그 저장 안 함)
        serializer = MusicPlaySerializer(music)
        return Response(serializer.data)


class MusicTagsView(APIView):
    """
    음악 태그 조회
    - GET: music_id로 음악에 연결된 태그 목록 조회
    
    GET /api/v1/tracks/{music_id}/tags
    """
    permission_classes = [AllowAny]
    
    @extend_schema(
        summary="음악 태그 조회",
        description="""
        music_id를 사용하여 해당 음악에 연결된 태그 목록을 조회합니다.
        
        **반환 정보:**
        - tag_id: 태그 고유 ID
        - tag_key: 태그 이름 (예: "신나는", "슬픈", "발라드" 등)
        
        **주의사항:**
        - 삭제되지 않은 태그만 반환됩니다
        - 태그가 없는 경우 빈 배열을 반환합니다
        """,
        parameters=[
            OpenApiParameter(
                name='music_id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description='음악 ID (DB의 music_id)',
                required=True,
                examples=[
                    OpenApiExample(
                        name='예시',
                        value=1,
                        description='음악 ID 예시'
                    )
                ]
            )
        ],
        responses={
            200: TagSerializer(many=True),
            404: OpenApiResponse(description='Not Found - 음악을 찾을 수 없음'),
        },
        tags=['음악 상세']
    )
    def get(self, request, music_id):
        """music_id로 태그 목록 조회"""
        
        # 1. 음악 존재 여부 확인
        try:
            music = Music.objects.get(music_id=music_id)
        except Music.DoesNotExist:
            return Response(
                {'error': '음악을 찾을 수 없습니다.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # 2. 음악에 연결된 태그 조회
        music_tags = MusicTags.objects.filter(
            music=music,
            is_deleted=False
        ).select_related('tag')
        
        # 3. 삭제되지 않은 태그만 필터링
        tags = [mt.tag for mt in music_tags if not mt.tag.is_deleted]
        
        # 4. 태그 목록 반환
        serializer = TagSerializer(tags, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class MusicTagGraphView(APIView):
    """
    음악 태그 그래프 데이터 조회 (Treemap용)
    - GET: music_id로 태그별 score 및 비율(percentage) 조회
    
    GET /api/v1/tracks/{music_id}/tag-graph
    """
    permission_classes = [AllowAny]
    
    @extend_schema(
        summary="음악 태그 그래프 데이터 조회",
        description="""
        특정 음악의 태그 밀접도(score)를 분석하여 Recharts Treemap 형식으로 반환합니다.
        
        **반환 데이터:**
        - name: "Tags" (루트 노드)
        - children: 각 태그 정보 배열
          - name: 태그명
          - size: 시각적 가중치 (score의 세제곱)
          - score: 실제 밀접도 점수
          - percentage: 전체 점수 중 차지하는 비율 (%)
        
        **특징:**
        - dataKey="size"를 사용하여 시각적으로 점수 차이를 강조 (세제곱 비례)
        - percentage는 원본 점수 비율 유지
        """,
        parameters=[
            OpenApiParameter(
                name='music_id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description='음악 ID',
                required=True
            )
        ],
        responses={
            200: MusicTagGraphSerializer(many=True),
            404: OpenApiResponse(description='Not Found - 음악을 찾을 수 없음'),
        },
        tags=['음악 상세']
    )
    def get(self, request, music_id):
        """음악 태그 그래프 데이터 조회"""
        
        # 1. 음악 존재 여부 확인
        try:
            Music.objects.get(music_id=music_id)
        except Music.DoesNotExist:
            return Response(
                {'error': '음악을 찾을 수 없습니다.'},
                status=status.HTTP_404_NOT_FOUND
            )
            
        # 2. 그래프 데이터 생성
        graph_data = MusicTagService.get_tag_graph_data(music_id)
        
        # 3. 데이터 반환
        serializer = MusicTagGraphSerializer(graph_data, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
