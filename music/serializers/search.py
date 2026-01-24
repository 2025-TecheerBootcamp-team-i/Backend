"""
검색 관련 Serializers - iTunes 검색 결과 및 AI 음악 검색
"""
from rest_framework import serializers
from ..serializers.base import ArtistSerializer, AlbumSerializer, AiInfoSerializer


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


class AiMusicSearchResultSerializer(serializers.Serializer):
    """
    AI 음악 검색 결과용 Serializer
    
    - Music과 AiInfo를 조인하여 AI 음악 정보를 제공
    - 노래 제목과 input_prompt 필드에서 검색
    """
    music_id = serializers.IntegerField()
    music_name = serializers.CharField()
    artist = ArtistSerializer(read_only=True)
    album = AlbumSerializer(read_only=True)
    genre = serializers.CharField(allow_null=True)
    duration = serializers.IntegerField(allow_null=True)
    audio_url = serializers.CharField(allow_null=True)
    is_ai = serializers.BooleanField(default=True)
    ai_info = AiInfoSerializer(read_only=True, source='aiinfo_set.first')
    created_at = serializers.DateTimeField()
    
    # 포맷된 재생 시간
    duration_formatted = serializers.SerializerMethodField()
    
    def get_duration_formatted(self, obj):
        """재생 시간을 mm:ss 형식으로 변환"""
        if obj.duration:
            minutes = obj.duration // 60
            seconds = obj.duration % 60
            return f"{minutes}:{seconds:02d}"
        return None


class TagMusicSearchSerializer(serializers.Serializer):
    """
    태그로 음악 검색 결과용 Serializer
    
    - 특정 태그를 가진 모든 음악 반환
    - music_id, album_name, artist_name, 앨범 이미지 정보 포함
    """
    music_id = serializers.IntegerField()
    album_name = serializers.CharField(allow_null=True)
    artist_name = serializers.CharField(allow_null=True)
    image_large_square = serializers.CharField(allow_null=True)  # 360x360 사각형 이미지
    image_square = serializers.CharField(allow_null=True)  # 220x220 사각형 이미지
    album_image = serializers.CharField(allow_null=True)  # 원본 앨범 이미지
