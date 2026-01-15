"""
플레이리스트 관련 Serializer
"""
from rest_framework import serializers
from django.utils import timezone
from ..models import Playlists, PlaylistItems, Music, Artists, Albums


class PlaylistMusicSerializer(serializers.ModelSerializer):
    """플레이리스트 내 음악 정보 (간단 버전)"""
    artist_name = serializers.CharField(source='artist.artist_name', read_only=True)
    album_name = serializers.CharField(source='album.album_name', read_only=True)
    album_image = serializers.CharField(source='album.album_image', read_only=True)
    
    class Meta:
        model = Music
        fields = [
            'music_id', 'music_name', 'artist_name', 'album_name',
            'album_image', 'duration', 'is_ai', 'audio_url'
        ]


class PlaylistItemSerializer(serializers.ModelSerializer):
    """플레이리스트 아이템 (곡 정보 포함)"""
    music = PlaylistMusicSerializer(read_only=True)
    
    class Meta:
        model = PlaylistItems
        fields = ['item_id', 'music', 'order', 'created_at']


class PlaylistListSerializer(serializers.ModelSerializer):
    """플레이리스트 목록용 Serializer (곡 개수만 표시)"""
    track_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Playlists
        fields = [
            'playlist_id', 'title', 'visibility', 
            'track_count', 'created_at', 'updated_at'
        ]
    
    def get_track_count(self, obj):
        """플레이리스트의 곡 개수"""
        return PlaylistItems.objects.filter(
            playlist=obj,
            is_deleted=False
        ).count()


class PlaylistDetailSerializer(serializers.ModelSerializer):
    """플레이리스트 상세 Serializer (전체 곡 목록 포함)"""
    items = serializers.SerializerMethodField()
    track_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Playlists
        fields = [
            'playlist_id', 'title', 'visibility',
            'track_count', 'items', 'created_at', 'updated_at'
        ]
    
    def get_items(self, obj):
        """플레이리스트의 곡 목록 (order 순서대로)"""
        items = PlaylistItems.objects.filter(
            playlist=obj,
            is_deleted=False
        ).select_related('music__artist', 'music__album').order_by('order')
        
        return PlaylistItemSerializer(items, many=True).data
    
    def get_track_count(self, obj):
        """플레이리스트의 곡 개수"""
        return PlaylistItems.objects.filter(
            playlist=obj,
            is_deleted=False
        ).count()


class PlaylistCreateSerializer(serializers.ModelSerializer):
    """플레이리스트 생성/수정용 Serializer"""
    
    class Meta:
        model = Playlists
        fields = ['title', 'visibility']
    
    def validate_title(self, value):
        """제목 검증"""
        if not value or not value.strip():
            raise serializers.ValidationError("플레이리스트 제목은 필수입니다.")
        if len(value) > 100:
            raise serializers.ValidationError("플레이리스트 제목은 100자 이내로 입력해주세요.")
        return value.strip()
    
    def validate_visibility(self, value):
        """공개 설정 검증"""
        valid_values = ['public', 'private']
        if value not in valid_values:
            raise serializers.ValidationError(f"visibility는 {', '.join(valid_values)} 중 하나여야 합니다.")
        return value


class PlaylistItemCreateSerializer(serializers.Serializer):
    """플레이리스트에 곡 추가용 Serializer"""
    music_id = serializers.IntegerField()
    
    def validate_music_id(self, value):
        """음악 ID 검증"""
        try:
            Music.objects.get(music_id=value, is_deleted=False)
        except Music.DoesNotExist:
            raise serializers.ValidationError("존재하지 않는 음악입니다.")
        return value
