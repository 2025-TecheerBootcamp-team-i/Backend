"""
Music 앱의 Services 패키지
외부 API 통합 및 비즈니스 로직을 제공합니다.
"""

from .itunes import iTunesService
from .wikidata import WikidataService
from .lrclib import LRCLIBService
from .deezer import DeezerService
from .lyrics_ovh import LyricsOvhService

__all__ = [
    'iTunesService',
    'WikidataService',
    'LRCLIBService',
    'DeezerService',       # Wikidata fallback (아티스트 이미지)
    'LyricsOvhService',    # LRCLIB fallback (가사)
]
