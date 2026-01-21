"""
Music 앱의 Services 패키지
외부 API 통합 및 비즈니스 로직을 제공합니다.

외부 서비스:
- iTunes, Wikidata, Deezer, LRCLIB, lyrics.ovh 등

내부 서비스:
- UserStatisticsService 등 도메인 비즈니스 로직
"""

# 외부 API 서비스들
from .external.itunes import iTunesService
from .external.wikidata import WikidataService
from .external.lrclib import LRCLIBService
from .external.deezer import DeezerService
from .external.lyrics_ovh import LyricsOvhService

# 내부 비즈니스 로직 서비스들
from .internal.ai_music_service import AiMusicGenerationService
from .internal.user_statistics import UserStatisticsService

__all__ = [
    # 외부 API 서비스들
    'iTunesService',
    'WikidataService',
    'LRCLIBService',
    'DeezerService',       # Wikidata fallback (아티스트 이미지)
    'LyricsOvhService',    # LRCLIB fallback (가사)
    
    # 내부 비즈니스 로직
    'AiMusicGenerationService',  # AI 음악 생성
    'UserStatisticsService',     # 사용자 음악 통계
]
