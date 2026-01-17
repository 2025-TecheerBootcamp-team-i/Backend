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
            # is_deleted가 False이거나 NULL인 아티스트만 조회
            artist = Artists.objects.get(
                artist_id=artist_id,
                is_deleted__in=[False, None],
            )
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
            artist = Artists.objects.get(
                artist_id=artist_id,
                is_deleted__in=[False, None],
            )
        except Artists.DoesNotExist:
            return Response(
                {"detail": "아티스트를 찾을 수 없습니다."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # 해당 아티스트의 곡 목록 조회 (앨범 정보 포함)
        tracks = Music.objects.filter(
            artist_id=artist_id,
            is_deleted__in=[False, None],
        ).select_related('album').order_by('-created_at')

        # Serializer로 변환
        tracks_data = []
        for track in tracks:
            # duration을 "mm:ss" 형식으로 변환
            duration_str = "-"
            if track.duration:
                minutes = track.duration // 60
                seconds = track.duration % 60
                duration_str = f"{minutes}:{seconds:02d}"

            tracks_data.append({
                "id": str(track.music_id),
                "title": track.music_name,
                "album": track.album.album_name if track.album else "-",
                "duration": duration_str,
                "album_image": track.album.album_image if track.album and track.album.album_image else None,
            })

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
            artist = Artists.objects.get(
                artist_id=artist_id,
                is_deleted__in=[False, None],
            )
        except Artists.DoesNotExist:
            return Response(
                {"detail": "아티스트를 찾을 수 없습니다."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # 해당 아티스트의 앨범 목록 조회
        albums = Albums.objects.filter(
            artist_id=artist_id,
            is_deleted__in=[False, None],
        ).order_by('-created_at')

        # Serializer로 변환
        albums_data = []
        for album in albums:
            # created_at에서 연도 추출 (없으면 None)
            year = None
            if album.created_at:
                year = str(album.created_at.year)

            albums_data.append({
                "id": str(album.album_id),
                "title": album.album_name or "-",
                "year": year or "-",
                "album_image": album.album_image if album.album_image else None,
            })

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
        tags=['앨범']
    )

    def get(self, request, album_id: int):
        """
        앨범 ID(album_id)로 단일 앨범 정보 및 수록곡 목록을 조회합니다.
        """
        try:
            # is_deleted가 False이거나 NULL인 앨범만 조회
            album = Albums.objects.select_related('artist').get(
                album_id=album_id,
                is_deleted__in=[False, None],
            )
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
        popular_artists = PlayLogs.objects.filter(
            is_deleted__in=[False, None],
            music__is_deleted__in=[False, None],
            music__artist__is_deleted__in=[False, None]
        ).values(
            'music__artist__artist_id',
            'music__artist__artist_name',
            'music__artist__artist_image'
        ).annotate(
            play_count=Count('play_log_id')
        ).order_by('-play_count')[:limit]
        
        # 결과를 Serializer 형식으로 변환
        artists_data = []
        for idx, artist_stat in enumerate(popular_artists, 1):
            artists_data.append({
                'rank': idx,
                'artist_id': artist_stat['music__artist__artist_id'],
                'artist_name': artist_stat['music__artist__artist_name'],
                'image_small_circle': artist_stat['music__artist__artist_image'],
                'play_count': artist_stat['play_count']
            })
        
        return Response(artists_data, status=status.HTTP_200_OK)

