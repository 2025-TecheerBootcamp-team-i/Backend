from rest_framework import serializers
from .models import Music, AiInfo


class MusicGenerateRequestSerializer(serializers.Serializer):
    """
    음악 생성 요청 직렬화
    """
    prompt = serializers.CharField(
        max_length=500,
        required=True,
        help_text="음악 생성을 위한 프롬프트 (예: '여름의 장미')"
    )
    user_id = serializers.IntegerField(
        required=False,
        help_text="사용자 ID (선택)"
    )
    make_instrumental = serializers.BooleanField(
        default=False,
        required=False,
        help_text="반주만 생성할지 여부"
    )
    
    def validate_prompt(self, value):
        """프롬프트 유효성 검사"""
        if not value.strip():
            raise serializers.ValidationError("프롬프트는 비어있을 수 없습니다.")
        return value.strip()


class AiInfoSerializer(serializers.ModelSerializer):
    """
    AI 정보 직렬화
    """
    class Meta:
        model = AiInfo
        fields = ['aiinfo_id', 'input_prompt', 'created_at']


class MusicGenerateResponseSerializer(serializers.ModelSerializer):
    """
    음악 생성 응답 직렬화
    """
    ai_info = AiInfoSerializer(source='aiinfo_set', many=True, read_only=True)
    artist_name = serializers.CharField(source='artist.artist_name', read_only=True, allow_null=True)
    album_name = serializers.CharField(source='album.album_name', read_only=True, allow_null=True)
    
    class Meta:
        model = Music
        fields = [
            'music_id',
            'music_name',
            'audio_url',
            'is_ai',
            'genre',
            'duration',
            'lyrics',
            'valence',
            'arousal',
            'artist_name',
            'album_name',
            'ai_info',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['music_id', 'created_at', 'updated_at']


class MusicSerializer(serializers.ModelSerializer):
    """
    일반 음악 직렬화
    """
    artist_name = serializers.CharField(source='artist.artist_name', read_only=True, allow_null=True)
    album_name = serializers.CharField(source='album.album_name', read_only=True, allow_null=True)
    
    class Meta:
        model = Music
        fields = [
            'music_id',
            'music_name',
            'audio_url',
            'is_ai',
            'genre',
            'duration',
            'lyrics',
            'valence',
            'arousal',
            'artist_name',
            'album_name',
            'created_at'
        ]


class TaskStatusSerializer(serializers.Serializer):
    """
    Celery 작업 상태 직렬화
    """
    task_id = serializers.CharField(read_only=True)
    status = serializers.CharField(read_only=True)
    result = serializers.JSONField(read_only=True, allow_null=True)
    error = serializers.CharField(read_only=True, allow_null=True)
