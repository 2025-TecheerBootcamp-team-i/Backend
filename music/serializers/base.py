"""
기본 Serializers - 아티스트, 앨범, 태그, AI 정보
"""
from rest_framework import serializers
from ..models import Artists, Albums, Tags, AiInfo
from ..utils.s3_upload import is_s3_url


class ArtistSerializer(serializers.ModelSerializer):
    """아티스트 정보 Serializer"""
    artist_image = serializers.SerializerMethodField()
    
    class Meta:
        model = Artists
        fields = ['artist_id', 'artist_name', 'artist_image']
    
    def get_artist_image(self, obj):
        """image_large_circle이 있으면 사용, 없으면 원본 artist_image 사용"""
        # RDS에서 image_large_circle 필드 값을 직접 가져옴
        if obj.image_large_circle:
            return obj.image_large_circle
        # 없으면 원본 artist_image 사용
        return obj.artist_image


class AlbumSerializer(serializers.ModelSerializer):
    """앨범 정보 Serializer"""
    
    class Meta:
        model = Albums
        # 기본 앨범 정보에 더해, 360x360 정사각형 이미지 URL도 함께 내려준다.
        # 프론트에서는 image_large_square를 우선 사용하고,
        # 필요 시 기존 album_image(iTunes 원본 등)를 폴백으로 사용할 수 있다.
        fields = ['album_id', 'album_name', 'album_image', 'image_large_square']


class AlbumDetailSerializer(serializers.ModelSerializer):
    """앨범 상세 조회용 Serializer (수록곡 목록 포함)"""
    artist = ArtistSerializer(read_only=True)
    album_image = serializers.SerializerMethodField()
    image_large_square = serializers.SerializerMethodField()
    tracks = serializers.SerializerMethodField()
    track_count = serializers.SerializerMethodField()
    total_duration = serializers.SerializerMethodField()
    total_duration_formatted = serializers.SerializerMethodField()
    like_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Albums
        fields = [
            'album_id', 'album_name', 'album_image', 'image_large_square', 'artist',
            'track_count', 'total_duration', 'total_duration_formatted',
            'like_count', 'tracks', 'created_at', 'updated_at'
        ]
    
    def get_album_image(self, obj):
        """
        앨범 이미지 반환 우선순위:
        1. image_square (S3 URL 우선)
        2. image_large_square (S3 URL 우선)
        3. album_image (S3 URL 우선)
        4. 외부 URL은 최후의 수단으로만 사용
        """
        # 1순위: image_square가 있고 S3 URL이면 사용
        if obj.image_square and is_s3_url(obj.image_square):
            return obj.image_square
        
        # 2순위: image_large_square가 있고 S3 URL이면 사용
        if obj.image_large_square and is_s3_url(obj.image_large_square):
            return obj.image_large_square
        
        # 3순위: album_image가 있고 S3 URL이면 사용
        if obj.album_image and is_s3_url(obj.album_image):
            return obj.album_image
        
        # 4순위: image_square가 있으면 사용 (외부 URL이어도)
        if obj.image_square:
            return obj.image_square
        
        # 5순위: image_large_square가 있으면 사용 (외부 URL이어도)
        if obj.image_large_square:
            return obj.image_large_square
        
        # 최후: album_image 반환 (외부 URL이어도)
        return obj.album_image
    
    def get_image_large_square(self, obj):
        """image_large_square 필드 값 반환"""
        return obj.image_large_square if obj.image_large_square else None
    
    def get_tracks(self, obj):
        """앨범의 수록곡 목록 조회"""
        from ..models import Music
        tracks = Music.objects.filter(
            album=obj,
            is_deleted__in=[False, None]
        ).select_related('artist').order_by('created_at')
        
        tracks_data = []
        for track in tracks:
            # duration을 "mm:ss" 형식으로 변환
            duration_str = "-"
            if track.duration:
                minutes = track.duration // 60
                seconds = track.duration % 60
                duration_str = f"{minutes}:{seconds:02d}"
            
            tracks_data.append({
                'music_id': track.music_id,
                'music_name': track.music_name,
                'artist_name': track.artist.artist_name if track.artist else None,
                'duration': duration_str,
                'duration_seconds': track.duration,
                'is_ai': track.is_ai,
            })
        
        return tracks_data
    
    def get_track_count(self, obj):
        """앨범의 곡 개수"""
        from ..models import Music
        return Music.objects.filter(
            album=obj,
            is_deleted__in=[False, None]
        ).count()
    
    def get_total_duration(self, obj):
        """앨범의 총 재생 시간 (초)"""
        from ..models import Music
        from django.db.models import Sum
        result = Music.objects.filter(
            album=obj,
            is_deleted__in=[False, None]
        ).aggregate(total=Sum('duration'))
        return result['total'] or 0
    
    def get_total_duration_formatted(self, obj):
        """앨범의 총 재생 시간 (포맷팅: mm:ss)"""
        total_seconds = self.get_total_duration(obj)
        if total_seconds:
            minutes = total_seconds // 60
            seconds = total_seconds % 60
            return f"{minutes}:{seconds:02d}"
        return "0:00"
    
    def get_like_count(self, obj):
        """앨범의 곡들에 대한 총 좋아요 수"""
        from ..models import Music, MusicLikes
        album_music_ids = Music.objects.filter(
            album=obj,
            is_deleted__in=[False, None]
        ).values_list('music_id', flat=True)
        
        return MusicLikes.objects.filter(
            music_id__in=album_music_ids,
            is_deleted__in=[False, None]
        ).count()


class TagSerializer(serializers.ModelSerializer):
    """태그 정보 Serializer"""
    
    class Meta:
        model = Tags
        fields = ['tag_id', 'tag_key']


class AiInfoSerializer(serializers.ModelSerializer):
    """AI 생성 정보 Serializer"""
    
    class Meta:
        model = AiInfo
        fields = ['aiinfo_id', 'input_prompt', 'created_at']
