"""
플레이리스트 관련 Serializers - 플레이리스트 CRUD, 곡 관리, 좋아요
"""
from rest_framework import serializers
from ..models import Playlists, PlaylistItems, PlaylistLikes, Music
from .music import MusicPlaySerializer


class PlaylistItemSerializer(serializers.ModelSerializer):
    """플레이리스트 항목 Serializer"""
    music = MusicPlaySerializer(read_only=True)
    
    class Meta:
        model = PlaylistItems
        fields = ['item_id', 'music', 'order', 'created_at']


class PlaylistSerializer(serializers.ModelSerializer):
    """플레이리스트 목록 조회용 Serializer (기본 정보만)"""
    user_id = serializers.IntegerField(source='user.user_id', read_only=True)
    item_count = serializers.SerializerMethodField()
    like_count = serializers.SerializerMethodField()

    class Meta:
        model = Playlists
        fields = [
            'playlist_id', 'title', 'visibility', 'user_id',
            'item_count', 'like_count', 'created_at', 'updated_at', 
        ]
    
    def get_item_count(self, obj):
        """플레이리스트의 곡 개수"""
        return PlaylistItems.objects.filter(
            playlist=obj,
            is_deleted=False
        ).count()
    
    def get_like_count(self, obj):
        """플레이리스트 좋아요 개수"""
        return PlaylistLikes.objects.filter(
            playlist=obj,
            is_deleted=False
        ).count()


class PlaylistDetailSerializer(serializers.ModelSerializer):
    """플레이리스트 상세 조회용 Serializer (곡 목록 포함)"""
    user_id = serializers.IntegerField(source='user.user_id', read_only=True)
    items = serializers.SerializerMethodField()
    item_count = serializers.SerializerMethodField()
    like_count = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()

    class Meta:
        model = Playlists
        fields = [
            'playlist_id', 'title', 'visibility', 'user_id',
            'items', 'item_count', 'like_count', 'is_liked',
            'created_at', 'updated_at'
        ]
    
    def get_items(self, obj):
        """플레이리스트의 곡 목록 (order 순서대로)"""
        items = PlaylistItems.objects.filter(
            playlist=obj,
            is_deleted=False
        ).select_related('music', 'music__artist', 'music__album').order_by('order')
        return PlaylistItemSerializer(items, many=True).data
    
    def get_item_count(self, obj):
        """플레이리스트의 곡 개수"""
        return PlaylistItems.objects.filter(
            playlist=obj,
            is_deleted=False
        ).count()
    
    def get_like_count(self, obj):
        """플레이리스트 좋아요 개수"""
        return PlaylistLikes.objects.filter(
            playlist=obj,
            is_deleted=False
        ).count()
    
    def get_is_liked(self, obj):
        """현재 사용자가 좋아요를 눌렀는지 여부"""
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        
        try:
            from ..models import Users
            user = Users.objects.get(email=request.user.email, is_deleted=False)
            return PlaylistLikes.objects.filter(
                playlist=obj,
                user=user,
                is_deleted=False
            ).exists()
        except Users.DoesNotExist:
            return False


class PlaylistCreateSerializer(serializers.ModelSerializer):
    """플레이리스트 생성용 Serializer"""
    
    class Meta:
        model = Playlists
        fields = ['title', 'visibility']
    
    def validate_title(self, value):
        """제목 유효성 검사"""
        if not value or not value.strip():
            raise serializers.ValidationError("플레이리스트 제목을 입력해주세요.")
        if len(value) > 100:
            raise serializers.ValidationError("플레이리스트 제목은 100자 이내로 입력해주세요.")
        return value.strip()
    
    def validate_visibility(self, value):
        """공개 범위 유효성 검사"""
        valid_values = ['public', 'private', 'system']
        if value not in valid_values:
            raise serializers.ValidationError(
                f"visibility는 {', '.join(valid_values)} 중 하나여야 합니다."
            )
        return value


class PlaylistUpdateSerializer(serializers.ModelSerializer):
    """플레이리스트 수정용 Serializer"""
    
    class Meta:
        model = Playlists
        fields = ['title', 'visibility']
        extra_kwargs = {
            'title': {'required': False},
            'visibility': {'required': False},
        }
    
    def validate_title(self, value):
        """제목 유효성 검사"""
        if value is not None:
            if not value.strip():
                raise serializers.ValidationError("플레이리스트 제목을 입력해주세요.")
            if len(value) > 100:
                raise serializers.ValidationError("플레이리스트 제목은 100자 이내로 입력해주세요.")
            return value.strip()
        return value
    
    def validate_visibility(self, value):
        """공개 범위 유효성 검사"""
        if value is not None:
            valid_values = ['public', 'private', 'system']
            if value not in valid_values:
                raise serializers.ValidationError(
                    f"visibility는 {', '.join(valid_values)} 중 하나여야 합니다."
                )
        return value


class PlaylistItemAddSerializer(serializers.Serializer):
    """플레이리스트 곡 추가용 Serializer"""
    music_id = serializers.IntegerField()
    order = serializers.IntegerField(required=False)
    
    def validate_music_id(self, value):
        """음악 존재 여부 확인"""
        try:
            Music.objects.get(music_id=value, is_deleted=False)
        except Music.DoesNotExist:
            raise serializers.ValidationError("존재하지 않는 음악입니다.")
        return value


class PlaylistLikeSerializer(serializers.Serializer):
    """플레이리스트 좋아요 응답용 Serializer"""
    message = serializers.CharField()
    playlist_id = serializers.IntegerField()
    is_liked = serializers.BooleanField()
