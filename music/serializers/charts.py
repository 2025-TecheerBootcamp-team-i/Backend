"""
차트 관련 Serializers - 재생 기록, 차트 조회
"""
from rest_framework import serializers
from ..models import PlayLogs, Charts, Music
from .base import ArtistSerializer, AlbumSerializer


class PlayLogCreateSerializer(serializers.Serializer):
    """재생 기록 생성용 Serializer (요청)"""
    # music_id는 URL에서 받으므로 별도 필드 없음
    pass


class PlayLogResponseSerializer(serializers.Serializer):
    """재생 기록 생성 응답 Serializer"""
    message = serializers.CharField()
    play_log_id = serializers.IntegerField()
    music_id = serializers.IntegerField()
    played_at = serializers.DateTimeField()


class PlayLogListItemSerializer(serializers.ModelSerializer):
    """재생 로그 목록 항목 Serializer"""
    user_id = serializers.IntegerField(source='user.user_id', read_only=True)
    played_at = serializers.SerializerMethodField()
    
    class Meta:
        model = PlayLogs
        fields = ['user_id', 'played_at']
    
    def get_played_at(self, obj):
        """played_at에서 소수점(마이크로초) 제거"""
        if obj.played_at:
            return obj.played_at.replace(microsecond=0)
        return None


class ChartMusicSerializer(serializers.ModelSerializer):
    """차트 항목에 표시할 음악 정보 (간략화)"""
    artist = ArtistSerializer(read_only=True)
    album = AlbumSerializer(read_only=True)
    
    class Meta:
        model = Music
        fields = [
            'music_id', 'music_name', 'artist', 'album',
            'genre', 'duration', 'is_ai', 'audio_url', 'itunes_id'
        ]


class ChartItemSerializer(serializers.ModelSerializer):
    """차트 개별 항목 Serializer (순위 포함)"""
    music = ChartMusicSerializer(read_only=True)
    rank_change = serializers.IntegerField(required=False, allow_null=True, help_text="순위 변동폭 (이전 순위 - 현재 순위, null=NEW)")
    
    class Meta:
        model = Charts
        fields = ['rank', 'play_count', 'rank_change', 'music']


class ChartResponseSerializer(serializers.Serializer):
    """차트 조회 응답 Serializer"""
    type = serializers.CharField(help_text="차트 유형 (realtime|daily|ai)")
    generated_at = serializers.DateTimeField(help_text="차트 생성 시점")
    total_count = serializers.IntegerField(help_text="차트 항목 수")
    items = ChartItemSerializer(many=True, help_text="차트 항목 목록")
