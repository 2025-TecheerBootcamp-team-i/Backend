"""
아티스트 관련 API Views
"""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from drf_spectacular.utils import extend_schema

from ..models import Artists, Music, Albums, PlayLogs
from ..serializers import ArtistSerializer
from ..serializers.base import AlbumDetailSerializer
from ..serializers.artists import ArtistTrackSerializer, ArtistAlbumSerializer
from django.db.models import Count
from drf_spectacular.utils import OpenApiParameter
from drf_spectacular.types import OpenApiTypes


class ArtistDetailView(APIView):
    """
    단일 아티스트 상세 조회

    - GET /api/v1/artists/{artist_id}/
    """

    permission_classes = [AllowAny]
    
    @extend_schema(
        summary="아티스트 상세 조회",
        description="아티스트 ID로 단일 아티스트 정보 조회",
        tags=['아티스트']
    )

    def get(self, request, artist_id: int):
        """
        아티스트 ID(artist_id)로 단일 아티스트 정보를 조회합니다.
        """
        try:
            # SoftDeleteManager가 자동으로 is_deleted=False인 레코드만 조회
            artist = Artists.objects.get(artist_id=artist_id)
        except Artists.DoesNotExist:
            return Response(
                {"detail": "아티스트를 찾을 수 없습니다."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = ArtistSerializer(artist)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ArtistTracksView(APIView):
    """
    아티스트별 곡 목록 조회

    - GET /api/v1/artists/{artist_id}/tracks/
    """

    permission_classes = [AllowAny]
    
    @extend_schema(
        summary="아티스트별 곡 목록",
        description="아티스트 ID로 해당 아티스트의 곡 목록 조회",
        tags=['아티스트']
    )

    def get(self, request, artist_id: int):
        """
        아티스트 ID로 해당 아티스트의 곡 목록을 조회합니다.
        """
        # 아티스트 존재 여부 확인
        try:
            # SoftDeleteManager가 자동으로 is_deleted=False인 레코드만 조회
            artist = Artists.objects.get(artist_id=artist_id)
        except Artists.DoesNotExist:
            return Response(
                {"detail": "아티스트를 찾을 수 없습니다."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # 해당 아티스트의 곡 목록 조회 (앨범 정보 포함)
        # SoftDeleteManager가 자동으로 is_deleted=False인 레코드만 조회
        tracks = Music.objects.filter(artist_id=artist_id).select_related('album').order_by('-created_at')

        # Serializer를 사용하여 데이터 변환
        serializer = ArtistTrackSerializer(tracks, many=True)
        
        # id를 문자열로 변환 (기존 API 호환성 유지)
        tracks_data = serializer.data
        for track in tracks_data:
            track['id'] = str(track['id'])
        
        return Response(tracks_data, status=status.HTTP_200_OK)


class ArtistAlbumsView(APIView):
    """
    아티스트별 앨범 목록 조회

    - GET /api/v1/artists/{artist_id}/albums/
    """

    permission_classes = [AllowAny]
    
    @extend_schema(
        summary="아티스트별 앨범 목록",
        description="아티스트 ID로 해당 아티스트의 앨범 목록 조회",
        tags=['아티스트']
    )

    def get(self, request, artist_id: int):
        """
        아티스트 ID로 해당 아티스트의 앨범 목록을 조회합니다.
        """
        # 아티스트 존재 여부 확인
        try:
            # SoftDeleteManager가 자동으로 is_deleted=False인 레코드만 조회
            artist = Artists.objects.get(artist_id=artist_id)
        except Artists.DoesNotExist:
            return Response(
                {"detail": "아티스트를 찾을 수 없습니다."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # 해당 아티스트의 앨범 목록 조회
        # SoftDeleteManager가 자동으로 is_deleted=False인 레코드만 조회
        albums = Albums.objects.filter(artist_id=artist_id).order_by('-created_at')

        # Serializer를 사용하여 데이터 변환
        serializer = ArtistAlbumSerializer(albums, many=True)
        
        # id를 문자열로 변환 (기존 API 호환성 유지)
        albums_data = serializer.data
        for album in albums_data:
            album['id'] = str(album['id'])
        
        return Response(albums_data, status=status.HTTP_200_OK)


class AlbumDetailView(APIView):
    """
    앨범 상세 조회

    - GET /api/v1/albums/{album_id}/
    """

    permission_classes = [AllowAny]
    
    @extend_schema(
        summary="앨범 상세 조회",
        description="앨범 ID로 단일 앨범 정보 및 수록곡 목록 조회",
        tags=['아티스트']
    )

    def get(self, request, album_id: int):
        """
        앨범 ID(album_id)로 단일 앨범 정보 및 수록곡 목록을 조회합니다.
        """
        try:
            # SoftDeleteManager가 자동으로 is_deleted=False인 레코드만 조회
            album = Albums.objects.select_related('artist').get(album_id=album_id)
        except Albums.DoesNotExist:
            return Response(
                {"detail": "앨범을 찾을 수 없습니다."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = AlbumDetailSerializer(album)
        return Response(serializer.data, status=status.HTTP_200_OK)


class PopularArtistsView(APIView):
    """
    인기 아티스트 목록 조회

    - GET /api/v1/artists/popular?limit=7
    """

    permission_classes = [AllowAny]
    
    @extend_schema(
        summary="인기 아티스트 목록 조회",
        description="PlayLogs 기반 재생 횟수로 정렬된 인기 아티스트 목록 조회",
        parameters=[
            OpenApiParameter(
                name='limit',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='반환할 인기 아티스트 수 (기본값: 7)',
                required=False,
                default=7
            )
        ],
        tags=['아티스트']
    )

    def get(self, request):
        """
        PlayLogs의 재생 기록을 기반으로 인기 아티스트 목록을 조회합니다.
        
        - PlayLogs -> Music -> Artists 조인
        - 재생 횟수(play_count) 기준으로 정렬
        """
        limit = int(request.query_params.get('limit', 7))
        
        # PlayLogs에서 재생 기록을 기반으로 아티스트별 재생 횟수 집계
        # PlayLogs -> Music -> Artists 조인
        # SoftDeleteManager가 자동으로 각 모델의 is_deleted=False인 레코드만 조회
        popular_artists = PlayLogs.objects.filter(
            music__isnull=False,
            music__artist__isnull=False
        ).values(
            'music__artist__artist_id',
            'music__artist__artist_name',
            'music__artist__artist_image',
            'music__artist__image_small_circle',
            'music__artist__image_large_circle'
        ).annotate(
            play_count=Count('play_log_id')
        ).order_by('-play_count')[:limit]
        
        # 결과를 Serializer 형식으로 변환
        artists_data = []
        for idx, artist_stat in enumerate(popular_artists, 1):
            # RDS에서 이미지 우선순위: image_small_circle -> image_large_circle -> artist_image
            circle_image = artist_stat.get('music__artist__image_small_circle')
            if not circle_image or (isinstance(circle_image, str) and not circle_image.strip()):
                # image_small_circle이 없으면 image_large_circle 사용
                circle_image = artist_stat.get('music__artist__image_large_circle')
                if not circle_image or (isinstance(circle_image, str) and not circle_image.strip()):
                    # 둘 다 없으면 원본 artist_image 사용
                    circle_image = artist_stat.get('music__artist__artist_image')
            
            artists_data.append({
                'rank': idx,
                'artist_id': artist_stat['music__artist__artist_id'],
                'artist_name': artist_stat['music__artist__artist_name'],
                'image_small_circle': circle_image,
                'play_count': artist_stat['play_count']
            })
        
        return Response(artists_data, status=status.HTTP_200_OK)

