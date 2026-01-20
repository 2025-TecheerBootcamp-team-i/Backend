"""
외부 API 연동 서비스 패키지
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
    'DeezerService',
    'LyricsOvhService',
]
