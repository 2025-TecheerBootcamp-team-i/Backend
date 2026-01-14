"""
음악 상세 관련 Views - iTunes ID 기반 상세 조회, 음악 재생
"""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from django.db import transaction
from django.utils import timezone
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes
from ..models import Music, Artists, Albums, PlayLogs
from ..serializers import MusicDetailSerializer, MusicPlaySerializer
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


class MusicPlayView(APIView):
    """
    음악 재생 API
    
    - 음악 재생에 필요한 정보 반환 (audio_url 포함)
    - 재생 로그 기록 (인증된 사용자인 경우)
    
    GET /api/v1/tracks/{music_id}/play
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
        
        **재생 로그:**
        - 인증된 사용자의 경우 play_logs 테이블에 재생 기록 저장
        - 비인증 사용자는 로그 저장하지 않음
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
            404: {'description': 'Not Found - 음악을 찾을 수 없음'},
        },
        tags=['음악 재생']
    )
    def get(self, request, music_id):
        """음악 재생 정보 조회"""
        
        # 1. 음악 정보 조회
        try:
            music = Music.objects.select_related('artist', 'album').get(
                music_id=music_id,
                is_deleted=False
            )
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
        
        # 3. 재생 로그 기록 (인증된 사용자만)
        if request.user.is_authenticated:
            try:
                # Users 모델에서 사용자 조회
                from ..models import Users
                user = Users.objects.get(email=request.user.email)
                
                # 재생 로그 저장
                PlayLogs.objects.create(
                    music=music,
                    user=user,
                    played_at=timezone.now(),
                    created_at=timezone.now(),
                    is_deleted=False
                )
            except Users.DoesNotExist:
                # Users 테이블에 없는 경우 (Django auth_user만 있는 경우) 로그 저장 안 함
                pass
            except Exception as e:
                # 로그 저장 실패해도 음악 재생은 가능하도록 처리
                print(f"재생 로그 저장 실패: {str(e)}")
        
        # 4. 음악 재생 정보 반환
        serializer = MusicPlaySerializer(music)
        return Response(serializer.data)
