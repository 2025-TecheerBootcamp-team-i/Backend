"""
음악 상세 관련 Views - iTunes ID 기반 상세 조회
"""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from django.db import transaction
from django.utils import timezone
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes
from ..models import Music, Artists, Albums
from ..serializers import MusicDetailSerializer
from ..services import iTunesService


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
