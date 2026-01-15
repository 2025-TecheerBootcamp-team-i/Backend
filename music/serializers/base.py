"""
기본 Serializers - 아티스트, 앨범, 태그, AI 정보
"""
from rest_framework import serializers
from ..models import Artists, Albums, Tags, AiInfo


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
