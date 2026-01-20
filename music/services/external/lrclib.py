"""
LRCLIB API 통합 서비스
음악 가사를 LRCLIB에서 가져옵니다.
"""
import requests
import re
import logging
from typing import Optional
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class LRCLIBService:
    """LRCLIB API를 통한 가사 조회 서비스"""
    
    API_URL = "https://lrclib.net/api/search"
    TIMEOUT = 20
    
    _session = None
    
    @classmethod
    def _get_session(cls) -> requests.Session:
        """재사용 가능한 HTTP 세션 생성 (retry 로직 포함)"""
        if cls._session is None:
            session = requests.Session()
            headers = {
                "User-Agent": "MusicBackendService/1.0 (https://github.com/musicbackend; admin@musicbackend.com)",
                "Accept": "application/json"
            }
            session.headers.update(headers)
            
            retries = Retry(
                total=3,
                backoff_factor=2,
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
    def fetch_lyrics(
        cls, 
        artist_name: str, 
        track_name: str, 
        duration: Optional[int] = None
    ) -> Optional[str]:
        """
        아티스트명과 곡명으로 가사 조회
        
        Args:
            artist_name: 아티스트 이름
            track_name: 곡 이름
            duration: 곡 길이 (초 단위, 정확도 향상에 사용)
            
        Returns:
            가사 문자열 또는 None (찾지 못한 경우)
            - syncedLyrics (동기화된 가사) 우선 반환
            - 없으면 plainLyrics (일반 가사) 반환
        """
        logger.info(f"LRCLIB 가사 조회 시작: {artist_name} - {track_name}")
        
        # duration이 None이면 0으로 설정
        if duration is None:
            duration = 0
        
        clean_artist = cls._clean_text(artist_name)
        clean_track = cls._clean_text(track_name)
        
        if not clean_artist or not clean_track:
            logger.warning(f"아티스트명 또는 곡명이 비어있음")
            return None
        
        session = cls._get_session()
        
        params = {
            "q": f"{clean_artist} {clean_track}",
            "track_name": clean_track,
            "artist_name": clean_artist
        }
        
        try:
            response = session.get(cls.API_URL, params=params, timeout=cls.TIMEOUT)
            
            if response.status_code == 429:
                logger.warning("LRCLIB 요청 제한 (429)")
                return None
            
            if response.status_code != 200:
                logger.warning(f"LRCLIB API 오류: {response.status_code}")
                return None
            
            results = response.json()
            
            if not results or not isinstance(results, list):
                logger.info(f"가사를 찾을 수 없음: {artist_name} - {track_name}")
                return None
            
            # duration 기준으로 가장 적합한 가사 찾기
            best_match = None
            
            for item in results:
                api_duration = item.get("duration") or 0
                
                # duration이 0이면 시간 체크 무시, 아니면 4초 이내 차이만 허용
                if duration == 0 or abs(api_duration - duration) <= 4:
                    # syncedLyrics (동기화된 가사) 우선
                    if item.get("syncedLyrics"):
                        logger.info(f"동기화된 가사 발견: {artist_name} - {track_name}")
                        return item["syncedLyrics"]
                    
                    # plainLyrics 백업으로 저장
                    if item.get("plainLyrics") and not best_match:
                        best_match = item["plainLyrics"]
            
            # duration 매칭 실패 시 첫 번째 결과 사용
            if not best_match and results:
                first_result = results[0]
                best_match = first_result.get("syncedLyrics") or first_result.get("plainLyrics")
            
            if best_match:
                logger.info(f"가사 조회 성공: {artist_name} - {track_name}")
            else:
                logger.info(f"가사를 찾을 수 없음: {artist_name} - {track_name}")
            
            return best_match
            
        except requests.exceptions.RequestException as e:
            logger.error(f"LRCLIB API 요청 실패: {e}")
            return None
