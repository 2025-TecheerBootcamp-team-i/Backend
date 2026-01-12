
"""
Music 앱의 Serializer 모듈
음악, 아티스트, 앨범, 태그 등의 데이터를 JSON으로 직렬화합니다.
"""
인증 관련 Serializer
사용자 회원가입 및 로그인 데이터 검증 및 변환
"""
from rest_framework import serializers
from .models import Music, Artists, Albums, Tags, MusicTags, MusicLikes, AiInfo
from django.contrib.auth.hashers import make_password
from .models import Users


class ArtistSerializer(serializers.ModelSerializer):
    """아티스트 정보 Serializer"""
    
    class Meta:
        model = Artists
        fields = ['artist_id', 'artist_name', 'artist_image']


class AlbumSerializer(serializers.ModelSerializer):
    """앨범 정보 Serializer"""
    
    class Meta:
        model = Albums
        fields = ['album_id', 'album_name', 'album_image']


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


class MusicListSerializer(serializers.ModelSerializer):
    """음악 목록 조회용 Serializer (간단한 정보만)"""
    artist = ArtistSerializer(read_only=True)
    album = AlbumSerializer(read_only=True)
    
    class Meta:
        model = Music
        fields = [
            'music_id', 'music_name', 'artist', 'album', 
            'genre', 'duration', 'is_ai', 'audio_url', 
            'created_at'
        ]


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
        # MusicTags를 통해 연결된 태그들 조회
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
    

class UserRegisterSerializer(serializers.ModelSerializer):
    """회원가입 Serializer - 이메일, 비밀번호, 닉네임 입력받아 사용자 생성"""
    password = serializers.CharField(write_only=True, min_length=4)
    
    class Meta:
        model = Users
        fields = ['email', 'password', 'nickname']
    
    def create(self, validated_data):
        """비밀번호 해싱 후 사용자 생성"""
        validated_data['password'] = make_password(validated_data['password'])
        return Users.objects.create(**validated_data)


class UserLoginSerializer(serializers.Serializer):
    """로그인 Serializer - 이메일, 비밀번호 입력 검증"""
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
