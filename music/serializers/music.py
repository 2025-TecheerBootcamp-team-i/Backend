"""
음악 관련 Serializers - 음악 상세, 좋아요
"""
from rest_framework import serializers
from ..models import Music, MusicTags, AiInfo, Albums, AlbumLikes
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
    
    class Meta:
        model = Music
        fields = [
            'music_id', 'music_name', 'artist_name', 'album_name', 
            'album_image', 'audio_url', 'duration', 'genre', 
            'is_ai', 'lyrics', 'itunes_id'
        ]


class TagGraphItemSerializer(serializers.Serializer):
    """트리맵 항목용 시리얼라이저 (태그 개별 항목)"""
    name = serializers.CharField(source='tag.tag_key')
    size = serializers.FloatField(source='score')
    percentage = serializers.FloatField()


class MusicTagGraphSerializer(serializers.Serializer):
    """음악 태그 트리맵용 시리얼라이저 (Recharts 호환)"""
    name = serializers.CharField()
    children = TagGraphItemSerializer(many=True)


class UserLikedMusicSerializer(serializers.ModelSerializer):
    """사용자가 좋아요한 곡 목록용 Serializer"""
    artist_name = serializers.CharField(source='artist.artist_name', read_only=True, allow_null=True)
    album_image = serializers.SerializerMethodField()
    
    class Meta:
        model = Music
        fields = [
            'music_id', 'music_name', 'album_image', 
            'artist_name', 'duration'
        ]
    
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


class AlbumLikeSerializer(serializers.Serializer):
    """앨범 좋아요 응답용 Serializer"""
    message = serializers.CharField()
    album_id = serializers.IntegerField()
    is_liked = serializers.BooleanField()
    like_count = serializers.IntegerField(required=False)


class UserLikedAlbumSerializer(serializers.ModelSerializer):
    """사용자가 좋아요한 앨범 목록용 Serializer"""
    artist_name = serializers.CharField(source='artist.artist_name', read_only=True, allow_null=True)
    cover_image = serializers.SerializerMethodField()
    like_count = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()
    release_date = serializers.SerializerMethodField()
    
    class Meta:
        model = Albums
        fields = [
            'album_id', 'album_name', 'artist_name', 
            'cover_image', 'release_date',
            'like_count', 'is_liked'
        ]
    
    def get_cover_image(self, obj):
        """앨범 커버 이미지 반환"""
        if obj.image_square:
            return obj.image_square
        return obj.album_image
    
    def get_like_count(self, obj):
        """앨범 좋아요 개수"""
        return AlbumLikes.objects.filter(
            album=obj,
            is_deleted=False
        ).count()
    
    def get_is_liked(self, obj):
        """현재 사용자가 좋아요를 눌렀는지 여부"""
        request = self.context.get('request')
        if not request:
            return False
        
        # 인증된 사용자 확인
        user = request.user
        if not user or not hasattr(user, 'is_authenticated') or not user.is_authenticated:
            return False
        
        try:
            return AlbumLikes.objects.filter(
                album=obj,
                user=user,
                is_deleted=False
            ).exists()
        except Exception:
            return False
    
    def get_release_date(self, obj):
        """앨범 발매일 (created_at 사용)"""
        if obj.created_at:
            return obj.created_at.strftime('%Y-%m-%d')
        return None
