"""
외부 API 연동 서비스 패키지

- iTunes, Wikidata, Deezer, LRCLIB, lyrics.ovh 등
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
