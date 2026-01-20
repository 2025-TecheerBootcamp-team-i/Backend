"""
음악 관련 Serializers - 음악 상세, 좋아요
"""
from rest_framework import serializers
from ..models import Music, MusicTags, AiInfo
from .base import ArtistSerializer, AlbumSerializer, TagSerializer, AiInfoSerializer


class MusicDetailSerializer(serializers.ModelSerializer):
    """음악 상세 조회용 Serializer (모든 정보 포함)"""
    artist = ArtistSerializer(read_only=True)
    album = AlbumSerializer(read_only=True)
    tags = serializers.SerializerMethodField()
    ai_info = serializers.SerializerMethodField()
    
    class Meta:
        model = Music
        fields = [
            'music_id', 'music_name', 'artist', 'album', 
            'genre', 'duration', 'is_ai', 'audio_url', 
            'lyrics', 'valence', 'arousal', 'itunes_id',
            'tags', 'ai_info', 'created_at', 'updated_at'
        ]
    
    def get_tags(self, obj):
        """음악에 연결된 태그 목록 조회"""
        music_tags = MusicTags.objects.filter(
            music=obj, 
            is_deleted=False
        ).select_related('tag')
        
        tags = [mt.tag for mt in music_tags if not mt.tag.is_deleted]
        return TagSerializer(tags, many=True).data
    
    def get_ai_info(self, obj):
        """AI 생성 정보 조회 (있는 경우만)"""
        if not obj.is_ai:
            return None
        
        try:
            ai_info = AiInfo.objects.get(music=obj, is_deleted=False)
            return AiInfoSerializer(ai_info).data
        except AiInfo.DoesNotExist:
            return None


class MusicLikeSerializer(serializers.Serializer):
    """좋아요 응답용 Serializer"""
    message = serializers.CharField()
    music_id = serializers.IntegerField()
    is_liked = serializers.BooleanField()


class MusicPlaySerializer(serializers.ModelSerializer):
    """음악 재생용 Serializer (재생에 필요한 정보만)"""
    artist_name = serializers.CharField(source='artist.artist_name', read_only=True)
    album_name = serializers.CharField(source='album.album_name', read_only=True)
    album_image = serializers.CharField(source='album.album_image', read_only=True)
    album_image_large_square = serializers.CharField(
        source='album.image_large_square',
        read_only=True,
        allow_null=True,
        help_text='앨범의 360x360 정사각형 커버 이미지 URL (없을 수 있음)',
    )
    
    class Meta:
        model = Music
        fields = [
            'music_id',
            'music_name',
            'artist_name',
            'album_name',
            'album_image',
            'album_image_large_square',
            'audio_url',
            'duration',
            'genre',
            'is_ai',
            'lyrics',
            'itunes_id',
        ]
