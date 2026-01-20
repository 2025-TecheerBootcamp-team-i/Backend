"""
검색 관련 Serializers - iTunes 검색 결과
"""
from rest_framework import serializers


class iTunesSearchResultSerializer(serializers.Serializer):
    """
    iTunes 검색 결과용 Serializer

    - artist_id, album_id는 DB에 해당 데이터가 있을 때만 포함 (없으면 null)
    """
    itunes_id = serializers.IntegerField()
    music_name = serializers.CharField()
    artist_name = serializers.CharField()
    artist_id = serializers.IntegerField(allow_null=True)  # 아티스트 ID (DB에 있을 때만)
    album_name = serializers.CharField()
    album_id = serializers.IntegerField(allow_null=True)  # 앨범 ID (DB에 있을 때만)
    genre = serializers.CharField()
    duration = serializers.IntegerField(allow_null=True)  # 재생 시간 (초)
    audio_url = serializers.CharField(allow_null=True)  # 실제 재생용 오디오 URL (30초 preview)
    album_image = serializers.CharField(allow_null=True)  # 앨범 커버 이미지
    in_db = serializers.BooleanField(default=False)  # DB에 이미 저장되어 있는지 여부
    has_matching_tags = serializers.BooleanField(default=False)  # 태그 검색 시 매칭 여부
