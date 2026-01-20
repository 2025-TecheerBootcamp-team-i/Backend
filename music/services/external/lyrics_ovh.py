"""
lyrics.ovh API 통합 서비스
가사를 lyrics.ovh에서 가져옵니다.
LRCLIB API의 보조(fallback) API로 사용됩니다.
"""
import requests
import re
import logging
from typing import Optional
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from urllib.parse import quote

logger = logging.getLogger(__name__)


class LyricsOvhService:
    """lyrics.ovh API를 통한 가사 조회 서비스 (LRCLIB fallback)"""
    
    # API 엔드포인트: https://api.lyrics.ovh/v1/{artist}/{title}
    BASE_URL = "https://api.lyrics.ovh/v1"
    TIMEOUT = 15
    
    _session = None
    
    @classmethod
    def _get_session(cls) -> requests.Session:
        """재사용 가능한 HTTP 세션 생성"""
        if cls._session is None:
            session = requests.Session()
            headers = {
                "User-Agent": "MusicBackendService/1.0",
                "Accept": "application/json"
            }
            session.headers.update(headers)
            
            retries = Retry(
                total=3,
                backoff_factor=1,
                status_forcelist=[429, 500, 502, 503, 504],
                allowed_methods=frozenset(["GET"])
            )
            adapter = HTTPAdapter(max_retries=retries)
            session.mount("https://", adapter)
            session.mount("http://", adapter)
            cls._session = session
        
        return cls._session
    
    @classmethod
    def _clean_text(cls, text: str) -> str:
        """검색 정확도를 위해 괄호 안 내용 제거 및 특수문자 처리"""
        if not text:
            return ""
        # 괄호 안 내용 제거
        text = re.sub(r"\([^)]*\)", "", text)
        text = re.sub(r"\[[^]]*\]", "", text)
        # 앞뒤 공백 제거
        return text.strip()
    
    @classmethod
    def fetch_lyrics(cls, artist_name: str, track_name: str) -> Optional[str]:
        """
        아티스트명과 곡명으로 가사 조회 (lyrics.ovh)
        
        Args:
            artist_name: 아티스트 이름
            track_name: 곡 이름
            
        Returns:
            가사 문자열 또는 None
            
        Note:
            lyrics.ovh는 일반 텍스트 가사만 제공 (동기화된 LRC 미지원)
        """
        logger.info(f"lyrics.ovh 가사 조회 시작: {artist_name} - {track_name}")
        
        clean_artist = cls._clean_text(artist_name)
        clean_track = cls._clean_text(track_name)
        
        if not clean_artist or not clean_track:
            logger.warning("아티스트명 또는 곡명이 비어있음")
            return None
        
        session = cls._get_session()
        
        # URL 인코딩하여 API 호출
        url = f"{cls.BASE_URL}/{quote(clean_artist)}/{quote(clean_track)}"
        
        try:
            response = session.get(url, timeout=cls.TIMEOUT)
            
            if response.status_code == 404:
                logger.info(f"lyrics.ovh에서 가사를 찾지 못함: {artist_name} - {track_name}")
                return None
            
            if response.status_code != 200:
                logger.warning(f"lyrics.ovh API 오류: {response.status_code}")
                return None
            
            data = response.json()
            lyrics = data.get("lyrics")
            
            if lyrics and lyrics.strip():
                logger.info(f"lyrics.ovh 가사 조회 성공: {artist_name} - {track_name}, 길이={len(lyrics)}")
                return lyrics.strip()
            
            logger.info(f"lyrics.ovh에서 가사 없음: {artist_name} - {track_name}")
            return None
            
        except requests.exceptions.RequestException as e:
            logger.error(f"lyrics.ovh API 요청 실패: {e}")
            return None
