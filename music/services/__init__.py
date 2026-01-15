"""
Music 앱의 Services 패키지
외부 API 통합 및 비즈니스 로직을 제공합니다.
"""

from .itunes import iTunesService

__all__ = [
    'iTunesService',
]
