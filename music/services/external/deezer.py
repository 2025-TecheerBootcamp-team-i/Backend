"""
Deezer API 통합 서비스
아티스트 이미지를 Deezer에서 가져옵니다.
Wikidata API의 보조(fallback) API로 사용됩니다.
"""
import requests
import re
import logging
from typing import Optional
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class DeezerService:
    """Deezer API를 통한 아티스트 이미지 조회 서비스 (Wikidata fallback)"""
    
    SEARCH_URL = "https://api.deezer.com/search/artist"
    TIMEOUT = 10
    
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
        """검색 정확도를 위해 괄호 안 내용 제거"""
        if not text:
            return ""
        text = re.sub(r"\([^)]*\)", "", text)
        text = re.sub(r"\[[^]]*\]", "", text)
        return text.strip()
    
    @classmethod
    def fetch_artist_image(cls, artist_name: str) -> Optional[str]:
        """
        아티스트 이름으로 이미지 URL 조회 (Deezer)
        
        Args:
            artist_name: 아티스트 이름
            
        Returns:
            이미지 URL 또는 None
        """
        logger.info(f"Deezer 아티스트 이미지 조회 시작: {artist_name}")
        
        clean_name = cls._clean_text(artist_name)
        if not clean_name:
            return None
        
        session = cls._get_session()
        
        try:
            params = {"q": clean_name}
            response = session.get(cls.SEARCH_URL, params=params, timeout=cls.TIMEOUT)
            
            if response.status_code != 200:
                logger.warning(f"Deezer API 오류: {response.status_code}")
                return None
            
            data = response.json()
            artists = data.get("data", [])
            
            if not artists:
                logger.info(f"Deezer에서 아티스트를 찾지 못함: {artist_name}")
                return None
            
            # 첫 번째 결과에서 이미지 추출 (picture_xl > picture_big > picture_medium)
            first_artist = artists[0]
            
            # xl (500x500), big (250x250), medium (56x56) 순으로 시도
            image_url = (
                first_artist.get("picture_xl") or
                first_artist.get("picture_big") or
                first_artist.get("picture_medium") or
                first_artist.get("picture")
            )
            
            if image_url:
                logger.info(f"Deezer 이미지 조회 성공: {artist_name} -> {image_url[:50]}...")
                return image_url
            
            logger.info(f"Deezer에서 이미지 없음: {artist_name}")
            return None
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Deezer API 요청 실패: {e}")
            return None
