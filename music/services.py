"""
iTunes API 통합 서비스
iTunes Search API와 Lookup API를 사용하여 음악 정보를 조회합니다.
"""
import requests
from typing import Dict, List, Optional
from django.conf import settings


class iTunesService:
    """iTunes API 통합 서비스 클래스"""
    
    BASE_URL = "https://itunes.apple.com"
    SEARCH_ENDPOINT = f"{BASE_URL}/search"
    LOOKUP_ENDPOINT = f"{BASE_URL}/lookup"
    TIMEOUT = 3  # 3초 타임아웃
    
    @classmethod
    def search(cls, term: str, limit: int = 20, country: str = "KR") -> Dict:
        """
        iTunes Search API를 사용하여 음악 검색
        
        Args:
            term: 검색어 (아티스트명, 곡명 등)
            limit: 결과 개수 (기본 20개)
            country: 국가 코드 (기본 KR)
            
        Returns:
            {
                'resultCount': int,
                'results': [...]
            }
        """
        try:
            params = {
                'term': term,
                'entity': 'song',
                'limit': limit,
                'country': country,
            }
            
            response = requests.get(
                cls.SEARCH_ENDPOINT,
                params=params,
                timeout=cls.TIMEOUT
            )
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.Timeout:
            return {'resultCount': 0, 'results': [], 'error': 'iTunes API timeout'}
        except requests.exceptions.RequestException as e:
            return {'resultCount': 0, 'results': [], 'error': str(e)}
    
    @classmethod
    def lookup(cls, itunes_id: int) -> Optional[Dict]:
        """
        iTunes Lookup API를 사용하여 특정 곡의 상세 정보 조회
        
        Args:
            itunes_id: iTunes Track ID
            
        Returns:
            곡 상세 정보 딕셔너리 또는 None
        """
        try:
            params = {
                'id': itunes_id,
                'entity': 'song',
            }
            
            response = requests.get(
                cls.LOOKUP_ENDPOINT,
                params=params,
                timeout=cls.TIMEOUT
            )
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('resultCount', 0) > 0:
                return data['results'][0]
            
            return None
            
        except requests.exceptions.Timeout:
            return None
        except requests.exceptions.RequestException:
            return None
    
    @classmethod
    def parse_track_data(cls, raw_data: Dict) -> Dict:
        """
        iTunes API 응답 데이터를 Music 모델 형식으로 변환
        
        Args:
            raw_data: iTunes API 원본 응답
            
        Returns:
            Music 모델 형식의 딕셔너리
        """
        # 장르 추출 (primaryGenreName)
        genre = raw_data.get('primaryGenreName', '')
        
        # duration은 밀리초로 제공되므로 초 단위로 변환
        duration_ms = raw_data.get('trackTimeMillis', 0)
        duration = int(duration_ms / 1000) if duration_ms else None
        
        return {
            'itunes_id': raw_data.get('trackId'),
            'music_name': raw_data.get('trackName', ''),
            'artist_name': raw_data.get('artistName', ''),
            'artist_image': raw_data.get('artworkUrl100', ''),  # 100x100 아티스트 이미지
            'album_name': raw_data.get('collectionName', ''),
            'album_image': raw_data.get('artworkUrl100', ''),  # 100x100 앨범 아트
            'genre': genre,
            'duration': duration,
            'audio_url': raw_data.get('previewUrl', ''),  # 30초 미리듣기 URL
            'is_ai': False,  # iTunes 곡은 모두 기성곡
            'itunes_url': raw_data.get('trackViewUrl', ''),  # iTunes Store URL
            'release_date': raw_data.get('releaseDate', ''),
            'track_number': raw_data.get('trackNumber'),
            'country': raw_data.get('country', 'KR'),
        }
    
    @classmethod
    def parse_search_results(cls, raw_results: List[Dict]) -> List[Dict]:
        """
        iTunes 검색 결과 전체를 파싱
        
        Args:
            raw_results: iTunes API 검색 결과 리스트
            
        Returns:
            파싱된 결과 리스트
        """
        return [cls.parse_track_data(track) for track in raw_results]
