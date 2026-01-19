"""
아티스트 및 앨범 관련 Serializers

기존 artists.py의 수동 데이터 가공 로직을 Serializer로 캡슐화합니다.
"""
from rest_framework import serializers
from ..models import Music, Albums
from .base import ArtistSerializer


class ArtistTrackSerializer(serializers.ModelSerializer):
    """
    아티스트별 곡 목록 Serializer
    
    기존 artists.py의 ArtistTracksView에서 수동으로 처리하던 로직을 Serializer로 이동했습니다.
    """
    id = serializers.IntegerField(source='music_id', read_only=True)
    title = serializers.CharField(source='music_name', read_only=True)
    album = serializers.CharField(source='album.album_name', read_only=True)
    duration = serializers.SerializerMethodField()
    album_image = serializers.SerializerMethodField()
    
    class Meta:
        model = Music
        fields = ['id', 'title', 'album', 'duration', 'album_image']
    
    def get_duration(self, obj):
        """
        duration을 "mm:ss" 형식으로 변환
        
        Args:
            obj: Music 인스턴스
            
        Returns:
            "mm:ss" 형식의 문자열 (예: "3:45")
        """
        if not obj.duration:
            return "-"
        
        minutes = obj.duration // 60
        seconds = obj.duration % 60
        return f"{minutes}:{seconds:02d}"
    
    def get_album_image(self, obj):
        """
        앨범 이미지 URL 반환
        
        우선순위:
        1. image_square (220x220 리사이징된 이미지)
        2. album_image를 리사이징 URL로 변환
        3. album_image (원본)
        """
        if not obj.album:
            return None
        
        # RDS에서 image_square 필드 값을 직접 가져옴
        if obj.album.image_square:
            return obj.album.image_square
        
        # 원본 이미지를 리사이징 URL로 변환
        if obj.album.album_image:
            original_url = obj.album.album_image
            
            # media/images/albums/original/xxx.jpg -> media/images/albums/square/220x220/xxx.jpg
            if '/original/' in original_url:
                # 파일명 추출 및 확장자 변경
                filename = original_url.split('/')[-1]
                filename_without_ext = filename.rsplit('.', 1)[0]
                square_filename = f"{filename_without_ext}.jpg"
                
                # 경로 변환
                return original_url.replace('/original/', '/square/220x220/').replace(filename, square_filename)
            
            return original_url
        
        return None


class ArtistAlbumSerializer(serializers.ModelSerializer):
    """
    아티스트별 앨범 목록 Serializer
    
    기존 artists.py의 ArtistAlbumsView에서 수동으로 처리하던 로직을 Serializer로 이동했습니다.
    """
    id = serializers.IntegerField(source='album_id', read_only=True)
    title = serializers.CharField(source='album_name', read_only=True)
    year = serializers.SerializerMethodField()
    album_image = serializers.SerializerMethodField()
    
    class Meta:
        model = Albums
        fields = ['id', 'title', 'year', 'album_image']
    
    def get_year(self, obj):
        """created_at에서 연도 추출"""
        if not obj.created_at:
            return "-"
        return str(obj.created_at.year)
    
    def get_album_image(self, obj):
        """
        앨범 이미지 URL 반환
        
        우선순위:
        1. image_square (220x220 리사이징된 이미지)
        2. album_image를 리사이징 URL로 변환
        3. album_image (원본)
        """
        # RDS에서 image_square 필드 값을 직접 가져옴
        if obj.image_square:
            return obj.image_square
        
        # 원본 이미지를 리사이징 URL로 변환
        if obj.album_image:
            original_url = obj.album_image
            
            # media/images/albums/original/xxx.jpg -> media/images/albums/square/220x220/xxx.jpg
            if '/original/' in original_url:
                # 파일명 추출 및 확장자 변경
                filename = original_url.split('/')[-1]
                filename_without_ext = filename.rsplit('.', 1)[0]
                square_filename = f"{filename_without_ext}.jpg"
                
                # 경로 변환
                return original_url.replace('/original/', '/square/220x220/').replace(filename, square_filename)
            
            return original_url
        
        return None
