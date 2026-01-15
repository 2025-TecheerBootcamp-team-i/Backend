"""
아티스트 관련 API Views
"""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny

from ..models import Artists, Music, Albums
from ..serializers import ArtistSerializer


class ArtistDetailView(APIView):
    """
    단일 아티스트 상세 조회

    - GET /api/v1/artists/{artist_id}/
    """

    permission_classes = [AllowAny]

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

