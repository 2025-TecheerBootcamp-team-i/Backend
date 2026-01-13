"""
검색 관련 Serializers - iTunes 검색 결과
"""
from rest_framework import serializers


class iTunesSearchResultSerializer(serializers.Serializer):
    """
    iTunes 검색 결과용 Serializer
    
    - iTunes API 결과는 기본적으로 is_ai=False
    - 프론트에서 is_ai 필드로 클라이언트 사이드 필터링 가능
    """
    itunes_id = serializers.IntegerField()
    music_name = serializers.CharField()
    artist_name = serializers.CharField()
    album_name = serializers.CharField()
    genre = serializers.CharField()
    duration = serializers.IntegerField(allow_null=True)  # 재생 시간 (초)
    audio_url = serializers.CharField(allow_null=True)  # 실제 재생용 오디오 URL (30초 preview)
    album_image = serializers.CharField(allow_null=True)  # 앨범 커버 이미지
    is_ai = serializers.BooleanField(default=False)  # AI 생성곡 여부 (클라이언트 필터링 가능)
    in_db = serializers.BooleanField(default=False)  # DB에 이미 저장되어 있는지 여부
    has_matching_tags = serializers.BooleanField(default=False)  # 태그 검색 시 매칭 여부
