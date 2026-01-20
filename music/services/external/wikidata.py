"""
Wikidata API 통합 서비스
아티스트 이미지를 Wikidata/Wikimedia Commons에서 가져옵니다.
"""
import requests
import re
import logging
from typing import Optional
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class WikidataService:
    """Wikidata API를 통한 아티스트 이미지 조회 서비스"""
    
    WIKIDATA_SEARCH_URL = "https://www.wikidata.org/w/api.php"
    WIKIDATA_ENTITY_URL = "https://www.wikidata.org/wiki/Special:EntityData/{}.json"
    COMMONS_API_URL = "https://commons.wikimedia.org/w/api.php"
    TIMEOUT = 10
    
    _session = None
    
    @classmethod
    def _get_session(cls) -> requests.Session:
        """재사용 가능한 HTTP 세션 생성 (retry 로직 포함)"""
        if cls._session is None:
            session = requests.Session()
            headers = {
                "User-Agent": "MusicBackendService/1.0 (contact: admin@musicbackend.com)",
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
    def _fetch_qid(cls, artist_name: str) -> Optional[str]:
        """아티스트 이름으로 Wikidata QID 검색 (한국어 -> 영어 순)"""
        artist_name = cls._clean_text(artist_name)
        if not artist_name:
            return None
        
        session = cls._get_session()
        
        for lang in ["ko", "en"]:
            try:
                params = {
                    "action": "wbsearchentities",
                    "format": "json",
                    "language": lang,
                    "search": artist_name,
                    "limit": 1
                }
                response = session.get(
                    cls.WIKIDATA_SEARCH_URL, 
                    params=params, 
                    timeout=cls.TIMEOUT
                )
                
                if response.status_code != 200:
                    continue
                
                data = response.json()
                results = data.get("search") or []
                
                if results and results[0].get("id"):
                    return results[0]["id"]
                    
            except requests.exceptions.RequestException as e:
                logger.warning(f"Wikidata QID 검색 실패 ({lang}): {e}")
                continue
        
        return None
    
    @classmethod
    def _fetch_p18_filename(cls, qid: str) -> Optional[str]:
        """QID의 P18(대표 이미지) 파일명 가져오기"""
        if not qid:
            return None
        
        session = cls._get_session()
        url = cls.WIKIDATA_ENTITY_URL.format(qid)
        
        try:
            response = session.get(url, timeout=cls.TIMEOUT)
            
            if response.status_code != 200:
                return None
            
            data = response.json()
            entity = (data.get("entities") or {}).get(qid) or {}
            claims = entity.get("claims") or {}
            
            p18 = claims.get("P18")
            if not p18:
                return None
            
            return p18[0]["mainsnak"]["datavalue"]["value"]
            
        except (requests.exceptions.RequestException, KeyError, IndexError) as e:
            logger.warning(f"P18 파일명 조회 실패 (QID: {qid}): {e}")
            return None
    
    @classmethod
    def _fetch_commons_url(cls, filename: str) -> Optional[str]:
        """Commons API로 실제 이미지 URL 조회"""
        if not filename:
            return None
        
        session = cls._get_session()
        
        try:
            params = {
                "action": "query",
                "format": "json",
                "titles": f"File:{filename}",
                "prop": "imageinfo",
                "iiprop": "url"
            }
            response = session.get(
                cls.COMMONS_API_URL, 
                params=params, 
                timeout=cls.TIMEOUT
            )
            
            if response.status_code != 200:
                return None
            
            data = response.json()
            pages = (data.get("query") or {}).get("pages") or {}
            
            for _, page in pages.items():
                imageinfo = page.get("imageinfo")
                if imageinfo and len(imageinfo) > 0:
                    return imageinfo[0].get("url")
            
            return None
            
        except requests.exceptions.RequestException as e:
            logger.warning(f"Commons URL 조회 실패 (filename: {filename}): {e}")
            return None
    
    @classmethod
    def fetch_artist_image(cls, artist_name: str) -> Optional[str]:
        """
        아티스트 이름으로 이미지 URL 조회
        
        Args:
            artist_name: 아티스트 이름
            
        Returns:
            이미지 URL 또는 None (찾지 못한 경우)
        """
        logger.info(f"Wikidata 아티스트 이미지 조회 시작: {artist_name}")
        
        # 1. QID 검색
        qid = cls._fetch_qid(artist_name)
        if not qid:
            logger.info(f"QID를 찾을 수 없음: {artist_name}")
            return None
        
        logger.debug(f"QID 발견: {qid}")
        
        # 2. P18 파일명 조회
        filename = cls._fetch_p18_filename(qid)
        if not filename:
            logger.info(f"P18 이미지가 없음 (QID: {qid})")
            return None
        
        logger.debug(f"P18 파일명: {filename}")
        
        # 3. Commons URL 조회
        image_url = cls._fetch_commons_url(filename)
        
        if image_url:
            logger.info(f"이미지 URL 조회 성공: {artist_name} -> {image_url[:50]}...")
        else:
            logger.info(f"Commons URL 조회 실패: {artist_name}")
        
        return image_url
