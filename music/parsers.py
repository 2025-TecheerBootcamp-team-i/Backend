"""
커스텀 파서 (하위 호환성 유지를 위한 re-export)

실제 구현은 music_generate 모듈에 있습니다.
"""
from .music_generate.parsers import FlexibleJSONParser

__all__ = ['FlexibleJSONParser']
