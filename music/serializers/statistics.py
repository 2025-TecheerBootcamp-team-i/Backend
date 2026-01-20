"""
사용자 통계 Serializer
"""
from rest_framework import serializers


class ListeningTimeSerializer(serializers.Serializer):
    """청취 시간 통계"""
    total_seconds = serializers.IntegerField(help_text="총 청취 시간 (초)")
    total_hours = serializers.FloatField(help_text="총 청취 시간 (시간)")
    play_count = serializers.IntegerField(help_text="총 재생 횟수")
    previous_period_hours = serializers.FloatField(help_text="이전 기간 청취 시간 (시간)")
    change_percent = serializers.FloatField(help_text="전월 대비 변화율 (%)")


class GenreStatSerializer(serializers.Serializer):
    """장르 통계"""
    rank = serializers.IntegerField(help_text="순위")
    genre = serializers.CharField(help_text="장르명")
    play_count = serializers.IntegerField(help_text="재생 횟수")
    percentage = serializers.FloatField(help_text="비율 (%)")


class ArtistStatSerializer(serializers.Serializer):
    """아티스트 통계"""
    rank = serializers.IntegerField(help_text="순위")
    artist_id = serializers.IntegerField(help_text="아티스트 ID")
    artist_name = serializers.CharField(help_text="아티스트명")
    artist_image = serializers.CharField(allow_null=True, help_text="아티스트 이미지 URL")
    play_count = serializers.IntegerField(help_text="재생 횟수")
    percentage = serializers.FloatField(help_text="비율 (%)")


class TagStatSerializer(serializers.Serializer):
    """태그(분위기/키워드) 통계"""
    tag_id = serializers.IntegerField(help_text="태그 ID")
    tag_key = serializers.CharField(help_text="태그명")
    play_count = serializers.IntegerField(help_text="재생 횟수")


class TrackStatSerializer(serializers.Serializer):
    """음악 통계"""
    rank = serializers.IntegerField(help_text="순위")
    music_id = serializers.IntegerField(help_text="음악 ID")
    music_name = serializers.CharField(help_text="음악명")
    artist_id = serializers.IntegerField(allow_null=True, help_text="아티스트 ID")
    artist_name = serializers.CharField(allow_null=True, help_text="아티스트명")
    album_id = serializers.IntegerField(allow_null=True, help_text="앨범 ID")
    album_name = serializers.CharField(allow_null=True, help_text="앨범명")
    album_image = serializers.CharField(allow_null=True, help_text="앨범 이미지 URL")
    play_count = serializers.IntegerField(help_text="재생 횟수")
    percentage = serializers.FloatField(help_text="비율 (%)")


class AIGenerationStatSerializer(serializers.Serializer):
    """AI 생성 활동 통계"""
    total_generated = serializers.IntegerField(help_text="생성한 AI 곡 수")
    last_generated_at = serializers.DateTimeField(allow_null=True, help_text="마지막 생성 일시")
    last_generated_days_ago = serializers.IntegerField(allow_null=True, help_text="마지막 생성 며칠 전")


class UserStatisticsSerializer(serializers.Serializer):
    """사용자 전체 통계"""
    listening_time = ListeningTimeSerializer(help_text="청취 시간 통계")
    top_genres = GenreStatSerializer(many=True, help_text="Top 장르")
    top_artists = ArtistStatSerializer(many=True, help_text="Top 아티스트")
    top_tags = TagStatSerializer(many=True, help_text="분위기/키워드")
    ai_generation = AIGenerationStatSerializer(help_text="AI 생성 활동")
