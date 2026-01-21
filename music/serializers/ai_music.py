"""
AI 음악 생성 Serializers

이 모듈은 AI 음악 생성 API의 요청/응답 데이터 검증 및 변환을 담당합니다.
기존 legacy_serializers.py의 로직을 개선하고 재사용 가능하게 구성했습니다.
"""
from rest_framework import serializers
from ..models import Music, AiInfo, Artists, Albums
from .base import ArtistSerializer, AlbumSerializer, AiInfoSerializer, TagSerializer


class MusicGenerateRequestSerializer(serializers.Serializer):
    """
    AI 음악 생성 요청 직렬화
    
    사용 예시:
    {
        "prompt": "여름의 장미",
        "user_id": 1,
        "make_instrumental": false
    }
    """
    prompt = serializers.CharField(
        max_length=500,
        required=True,
        help_text="음악 생성을 위한 프롬프트 (예: '여름의 장미')"
    )
    user_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="사용자 ID (선택, 로그인한 경우)"
    )
    make_instrumental = serializers.BooleanField(
        default=False,
        required=False,
        help_text="반주만 생성할지 여부 (기본: false)"
    )
    
    def validate_prompt(self, value):
        """프롬프트 유효성 검사"""
        if not value or not value.strip():
            raise serializers.ValidationError("프롬프트는 비어있을 수 없습니다.")
        
        # 앞뒤 공백 제거
        value = value.strip()
        
        # 최소 길이 체크
        if len(value) < 2:
            raise serializers.ValidationError("프롬프트는 최소 2자 이상이어야 합니다.")
        
        return value
    
    def validate_user_id(self, value):
        """사용자 ID 유효성 검사"""
        if value is not None and value <= 0:
            raise serializers.ValidationError("유효하지 않은 사용자 ID입니다.")
        return value


class MusicGenerateResponseSerializer(serializers.ModelSerializer):
    """
    AI 음악 생성 응답 직렬화
    
    Music 모델을 기반으로 하되, 관련 정보(artist, album, ai_info)를 포함합니다.
    """
    artist_name = serializers.CharField(
        source='artist.artist_name', 
        read_only=True, 
        allow_null=True,
        help_text="아티스트 이름"
    )
    album_name = serializers.CharField(
        source='album.album_name', 
        read_only=True, 
        allow_null=True,
        help_text="앨범 이름"
    )
    image_square = serializers.SerializerMethodField(
        help_text="앨범 사각형 이미지 URL (220x220)"
    )
    image_large_square = serializers.SerializerMethodField(
        help_text="앨범 큰 사각형 이미지 URL (360x360)"
    )
    album_image = serializers.SerializerMethodField(
        help_text="앨범 원본 이미지 URL"
    )
    ai_info = serializers.SerializerMethodField(
        help_text="AI 생성 정보 (프롬프트 등)"
    )
    
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
            'image_square',
            'image_large_square',
            'album_image',
            'ai_info',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['music_id', 'created_at', 'updated_at']
    
    def get_image_square(self, obj):
        """앨범 사각형 이미지 URL 반환 (220x220)"""
        if not obj.album:
            return None
        return obj.album.image_square
    
    def get_image_large_square(self, obj):
        """앨범 큰 사각형 이미지 URL 반환 (360x360)"""
        if not obj.album:
            return None
        return obj.album.image_large_square
    
    def get_album_image(self, obj):
        """앨범 원본 이미지 URL 반환"""
        if not obj.album:
            return None
        return obj.album.album_image
    
    def get_ai_info(self, obj):
        """AI 생성 정보 조회"""
        try:
            ai_info = AiInfo.objects.get(music=obj, is_deleted=False)
            
            # input_prompt에서 "Converted: " 부분만 추출
            input_prompt = ai_info.input_prompt
            if input_prompt and "Converted: " in input_prompt:
                # "Converted: " 이후의 내용만 추출
                converted_part = input_prompt.split("Converted: ", 1)
                if len(converted_part) > 1:
                    input_prompt = converted_part[1].strip()
            
            return {
                'aiinfo_id': ai_info.aiinfo_id,
                'task_id': ai_info.task_id,
                'input_prompt': input_prompt,
                'created_at': ai_info.created_at.isoformat() if ai_info.created_at else None
            }
        except AiInfo.DoesNotExist:
            return None


class MusicGenerateSimpleResponseSerializer(serializers.Serializer):
    """
    AI 음악 생성 간단한 응답 직렬화 (기존 legacy 응답 형식 호환)
    
    이 Serializer는 기존 legacy.py의 응답 형식과 동일하게 유지하여
    프론트엔드 호환성을 보장합니다.
    """
    music_id = serializers.IntegerField(help_text="생성된 음악 ID")
    music_name = serializers.CharField(help_text="음악 제목")
    audio_url = serializers.CharField(allow_null=True, help_text="오디오 파일 URL")
    is_ai = serializers.BooleanField(help_text="AI 생성 여부")
    genre = serializers.CharField(allow_null=True, help_text="장르")
    duration = serializers.IntegerField(allow_null=True, help_text="재생 시간 (초)")
    lyrics = serializers.CharField(allow_null=True, help_text="가사")
    valence = serializers.DecimalField(
        max_digits=10, 
        decimal_places=6, 
        allow_null=True,
        help_text="감정 긍정도"
    )
    arousal = serializers.DecimalField(
        max_digits=10, 
        decimal_places=6, 
        allow_null=True,
        help_text="감정 각성도"
    )
    artist_name = serializers.CharField(help_text="아티스트 이름")
    album_name = serializers.CharField(allow_null=True, help_text="앨범 이름")
    created_at = serializers.DateTimeField(help_text="생성 시각")
    
    @classmethod
    def from_music_model(cls, music: Music, artist: Artists, album: Albums):
        """
        Music 모델 인스턴스로부터 Serializer 데이터 생성
        
        Args:
            music: Music 모델 인스턴스
            artist: Artists 모델 인스턴스
            album: Albums 모델 인스턴스
            
        Returns:
            직렬화된 데이터 딕셔너리
        """
        return {
            'music_id': music.music_id,
            'music_name': music.music_name,
            'audio_url': music.audio_url,
            'is_ai': music.is_ai,
            'genre': music.genre,
            'duration': music.duration,
            'lyrics': music.lyrics,
            'valence': None,  # 항상 null
            'arousal': None,  # 항상 null
            'artist_name': artist.artist_name if artist else "AI Artist",
            'album_name': album.album_name if album else None,
            'created_at': music.created_at.isoformat() if music.created_at else None
        }


class TaskStatusSerializer(serializers.Serializer):
    """
    Celery 작업 상태 직렬화 (비동기 작업용)
    """
    task_id = serializers.CharField(read_only=True, help_text="Celery Task ID")
    status = serializers.CharField(read_only=True, help_text="작업 상태 (PENDING, SUCCESS, FAILURE 등)")
    result = serializers.JSONField(read_only=True, allow_null=True, help_text="작업 결과")
    error = serializers.CharField(read_only=True, allow_null=True, help_text="에러 메시지")


class MusicListSerializer(serializers.ModelSerializer):
    """
    음악 목록 조회용 Serializer
    
    기존 legacy의 list_music에서 사용하던 형식을 개선했습니다.
    """
    artist_name = serializers.CharField(
        source='artist.artist_name', 
        read_only=True, 
        allow_null=True
    )
    album_name = serializers.CharField(
        source='album.album_name', 
        read_only=True, 
        allow_null=True
    )
    album_image = serializers.SerializerMethodField()
    
    class Meta:
        model = Music
        fields = [
            'music_id',
            'music_name',
            'audio_url',
            'is_ai',
            'genre',
            'duration',
            'artist_name',
            'album_name',
            'album_image',
            'created_at'
        ]
    
    def get_album_image(self, obj):
        """
        앨범 이미지 URL 반환
        
        우선순위:
        1. image_square (220x220 리사이징된 이미지)
        2. album_image (원본 이미지)
        """
        if not obj.album:
            return None
        
        if obj.album.image_square:
            return obj.album.image_square
        
        return obj.album.album_image


class UserAiMusicListSerializer(serializers.ModelSerializer):
    """
    특정 사용자가 생성한 AI 음악 목록 응답용 Serializer
    """
    album_image_square = serializers.SerializerMethodField()
    like_count = serializers.SerializerMethodField()
    tags = serializers.SerializerMethodField()
    
    class Meta:
        model = Music
        fields = [
            'music_id',
            'music_name',
            'audio_url',
            'lyrics',
            'album_image_square',
            'like_count',
            'tags',
        ]
    
    def get_album_image_square(self, obj):
        """
        사각형 앨범 이미지 URL 반환 (없으면 기본 앨범 이미지로 폴백)
        """
        if not obj.album:
            return None
        
        if obj.album.image_square:
            return obj.album.image_square
        
        return obj.album.album_image

    def get_like_count(self, obj):
        """해당 음악의 좋아요 개수"""
        from ..models import MusicLikes
        return MusicLikes.objects.filter(music=obj, is_deleted__in=[False, None]).count()
    
    def get_tags(self, obj):
        """해당 음악에 연결된 태그 목록"""
        from ..models import MusicTags
        music_tags = MusicTags.objects.filter(
            music=obj,
            is_deleted__in=[False, None]
        ).select_related('tag')
        
        tags = [mt.tag for mt in music_tags if mt.tag and mt.tag.is_deleted in [False, None]]
        return TagSerializer(tags, many=True).data


class SunoTaskStatusRequestSerializer(serializers.Serializer):
    """
    Suno API 작업 상태 조회 요청
    """
    task_id = serializers.CharField(
        max_length=100,
        required=True,
        help_text="Suno API TaskID"
    )


class SunoTaskStatusResponseSerializer(serializers.Serializer):
    """
    Suno API 작업 상태 조회 응답
    """
    task_id = serializers.CharField(help_text="Suno API TaskID")
    status = serializers.CharField(help_text="작업 상태 (completed, pending, failed 등)")
    data = serializers.JSONField(allow_null=True, help_text="작업 데이터")


class ConvertPromptRequestSerializer(serializers.Serializer):
    """
    프롬프트 변환 요청 직렬화
    
    사용 예시:
    {
        "prompt": "놀이동산",
        "make_instrumental": false
    }
    """
    prompt = serializers.CharField(
        max_length=500,
        required=True,
        help_text="변환할 프롬프트 (예: '놀이동산')"
    )
    make_instrumental = serializers.BooleanField(
        default=False,
        required=False,
        help_text="반주만 생성할지 여부 (기본: false)"
    )
    
    def validate_prompt(self, value):
        """프롬프트 유효성 검사"""
        if not value or not value.strip():
            raise serializers.ValidationError("프롬프트는 비어있을 수 없습니다.")
        
        # 앞뒤 공백 제거
        value = value.strip()
        
        # 최소 길이 체크
        if len(value) < 2:
            raise serializers.ValidationError("프롬프트는 최소 2자 이상이어야 합니다.")
        
        return value


class ConvertPromptResponseSerializer(serializers.Serializer):
    """
    프롬프트 변환 응답 직렬화
    
    사용 예시:
    {
        "converted_prompt": "amusement park, fun upbeat Pop, 100 BPM, synthesizer drums bass, energetic Korean lyrics and Korean male vocals"
    }
    """
    converted_prompt = serializers.CharField(
        help_text="변환된 프롬프트 (영어)"
    )
