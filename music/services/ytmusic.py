"""
YouTube Music API 통합 서비스
아티스트 이미지를 YouTube Music에서 가져옵니다.
"""
import logging
import warnings
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ytmusicapi import YTMusic

# 불필요한 경고 메시지 필터링
warnings.filterwarnings('ignore', category=UserWarning)
warnings.filterwarnings('ignore', category=DeprecationWarning)

logger = logging.getLogger(__name__)

try:
    from ytmusicapi import YTMusic
    YTMUSIC_AVAILABLE = True
except ImportError:
    YTMUSIC_AVAILABLE = False
    YTMusic = None  # 타입 힌트를 위한 더미 값
    logger.warning("ytmusicapi가 설치되지 않았습니다. pip install ytmusicapi를 실행하세요.")


class YTMusicService:
    """YouTube Music API를 통한 아티스트 이미지 조회 서비스"""
    
    _ytmusic = None
    
    @classmethod
    def _get_ytmusic(cls) -> Optional['YTMusic']:
        """YTMusic 인스턴스 생성 (싱글톤 패턴)"""
        if not YTMUSIC_AVAILABLE:
            return None
            
        if cls._ytmusic is None:
            try:
                # 인증 없이 사용 가능 (제한적이지만 기본 검색은 가능)
                cls._ytmusic = YTMusic()
            except Exception as e:
                logger.error(f"YTMusic 인스턴스 생성 실패: {e}")
                return None
        
        return cls._ytmusic
    
    @classmethod
    def _clean_text(cls, text: str) -> str:
        """검색 정확도를 위해 괄호를 공백으로 치환 (내용은 유지)"""
        if not text:
            return ""
        import re
        # 괄호를 공백으로 치환 (내용은 유지)
        text = re.sub(r"[()<>\[\]{}]", " ", text)
        # 연속된 공백을 하나로
        text = re.sub(r"\s+", " ", text)
        return text.strip()
    
    @classmethod
    def _clean_album_name(cls, album_name: str) -> str:
        """
        앨범명 정규화
        
        규칙:
        1. 괄호를 공백으로 치환 (내용은 유지)
        2. 하이픈(-)이 한 번이라도 나오면, 그 앞 부분만 사용
           예) "SUPER REAL ME - EP"  -> "SUPER REAL ME"
               "I'LL LIKE YOU - Single" -> "I'LL LIKE YOU"
        3. 특수 문자 제거 (알파벳, 숫자, 한글, 공백만 남김)
        """
        if not album_name:
            return ""
        
        # 1. 괄호를 공백으로 치환
        text = cls._clean_text(album_name)

        if not text:
            return ""

        # 2. 하이픈 기준으로 앞부분만 사용
        # 일반 하이픈(-)과 en dash(–) 모두 처리
        for sep in ['-', '–']:
            if sep in text:
                text = text.split(sep, 1)[0]
                break

        text = text.strip()
        
        # 3. 특수 문자 제거 (알파벳, 숫자, 한글, 공백, 작은따옴표만 남김)
        import re
        text = re.sub(r"[^\w\s가-힣']", "", text, flags=re.UNICODE)
        text = re.sub(r"\s+", " ", text)  # 연속된 공백을 하나로
        
        return text.strip()
    
    @classmethod
    def _normalize_name(cls, name: str) -> str:
        """이름 정규화 (비교를 위해 소문자 변환 및 공백 제거)"""
        if not name:
            return ""
        return name.lower().strip()

    # 아티스트 이름 별칭 매핑 (한글명 ↔ 영문 공식 표기 등)
    # 필요할 때마다 여기에 수동으로 추가
    ARTIST_NAME_ALIASES = {
        # 예: "아일릿" → "ILLIT"
        "아일릿": ["ILLIT"],
        # 예: "아이유" → "IU"
        "아이유": ["IU"],
    }

    @classmethod
    def _apply_artist_aliases(cls, artist_name: str) -> str:
        """
        아티스트 이름에 별칭 매핑을 적용.
        
        - 입력이 한글인 경우, 미리 정의한 영문 공식 표기로 치환하여
          YouTube Music 쪽 아티스트명과 매칭이 잘 되도록 돕습니다.
        """
        if not artist_name:
            return ""

        base = cls._clean_text(artist_name)
        base_norm = cls._normalize_name(base)

        # 별칭 사전에 있는 경우, 첫 번째 별칭으로 치환
        for key, aliases in cls.ARTIST_NAME_ALIASES.items():
            key_norm = cls._normalize_name(key)
            if base_norm == key_norm:
                # 대표 별칭 하나만 사용 (예: "ILLIT")
                return aliases[0]

        return base
    
    @classmethod
    def _name_similarity(cls, name1: str, name2: str) -> float:
        """두 이름의 유사도 계산 (간단한 문자열 매칭)"""
        norm1 = cls._normalize_name(name1)
        norm2 = cls._normalize_name(name2)
        
        if norm1 == norm2:
            return 1.0
        
        # 한쪽이 다른 쪽을 포함하는 경우
        if norm1 in norm2 or norm2 in norm1:
            return 0.8
        
        # 공통 부분 계산
        common_chars = set(norm1) & set(norm2)
        if not common_chars:
            return 0.0
        
        return len(common_chars) / max(len(set(norm1)), len(set(norm2)))
    
    @classmethod
    def _find_best_match(cls, artist_name: str, search_results: list) -> Optional[dict]:
        """검색 결과에서 가장 정확한 아티스트 찾기"""
        if not search_results:
            return None
        
        # 아티스트 이름에 별칭 매핑 적용 (예: "아일릿" → "ILLIT")
        aliased_name = cls._apply_artist_aliases(artist_name)
        clean_name = cls._normalize_name(cls._clean_text(aliased_name))
        best_match = None
        best_score = 0.0
        
        for result in search_results:
            result_artist = result.get("artist", "")
            result_artist_norm = cls._normalize_name(result_artist)
            
            # 이름 유사도 계산
            score = cls._name_similarity(clean_name, result_artist_norm)
            
            # thumbnails가 있는지 확인 (이미지가 있는 아티스트 우선)
            has_thumbnails = bool(result.get("thumbnails"))
            if has_thumbnails:
                score += 0.2  # thumbnails가 있으면 보너스 점수
            
            if score > best_score:
                best_score = score
                best_match = result
        
        # 최소 유사도 임계값 (너무 다른 결과는 제외)
        if best_score < 0.3:
            logger.debug(f"유사도가 너무 낮음: {artist_name} (최고 점수: {best_score:.2f})")
            return None
        
        return best_match
    
    @classmethod
    def fetch_artist_image(cls, artist_name: str) -> Optional[str]:
        """
        아티스트 이름으로 이미지 URL 조회 (YouTube Music)
        
        Args:
            artist_name: 아티스트 이름
            
        Returns:
            이미지 URL 또는 None
        """
        logger.info(f"YouTube Music 아티스트 이미지 조회 시작: {artist_name}")
        
        if not YTMUSIC_AVAILABLE:
            logger.warning("ytmusicapi가 설치되지 않아 YouTube Music 조회를 건너뜁니다.")
            return None
        
        ytmusic = cls._get_ytmusic()
        if not ytmusic:
            return None
        
        clean_name = cls._clean_text(artist_name)
        if not clean_name:
            return None
        
        try:
            # 1. 아티스트 검색 (더 많은 결과 가져오기)
            search_results = ytmusic.search(query=clean_name, filter="artists", limit=10)
            
            if not search_results:
                logger.info(f"YouTube Music에서 아티스트를 찾지 못함: {artist_name}")
                return None
            
            # 2. 검색 결과에서 가장 정확한 매칭 찾기
            best_match = cls._find_best_match(artist_name, search_results)
            
            if not best_match:
                logger.info(f"적절한 아티스트 매칭을 찾지 못함: {artist_name}")
                return None
            
            # 3. browseId 또는 channelId 추출
            browse_id = best_match.get("browseId") or best_match.get("channelId")
            
            if not browse_id:
                logger.info(f"browseId/channelId를 찾을 수 없음: {artist_name}")
                return None
            
            logger.debug(f"browseId 발견: {browse_id} (매칭 아티스트: {best_match.get('artist', 'N/A')})")
            
            # 4. 아티스트 상세 정보 조회
            artist_info = ytmusic.get_artist(browse_id)
            
            if not artist_info:
                logger.info(f"아티스트 정보를 가져올 수 없음: {browse_id}")
                return None
            
            # 5. thumbnails에서 가장 큰 이미지 URL 추출
            thumbnails = artist_info.get("thumbnails", [])
            
            if not thumbnails:
                logger.info(f"thumbnails가 없음: {artist_name}")
                return None
            
            # 가장 큰 이미지 선택 (width 기준)
            largest_thumbnail = max(
                thumbnails, 
                key=lambda t: t.get("width", 0) or t.get("height", 0)
            )
            
            image_url = largest_thumbnail.get("url")
            
            if image_url:
                logger.info(f"YouTube Music 이미지 조회 성공: {artist_name} -> {image_url[:50]}...")
                return image_url
            
            logger.info(f"YouTube Music에서 이미지 URL을 추출할 수 없음: {artist_name}")
            return None
            
        except Exception as e:
            logger.error(f"YouTube Music API 요청 실패: {e}", exc_info=True)
            return None
    
    @classmethod
    def fetch_album_image(cls, album_name: str, artist_name: str = None) -> Optional[str]:
        """
        앨범 이름으로 이미지 URL 조회 (YouTube Music)
        
        여러 번 시도하여 검색 정확도를 높입니다:
        1. 원본 이름으로 검색
        2. 접미사 제거한 이름으로 검색
        
        Args:
            album_name: 앨범 이름
            artist_name: 아티스트 이름 (선택사항, 검색 정확도 향상)
            
        Returns:
            이미지 URL 또는 None
        """
        logger.info(f"YouTube Music 앨범 이미지 조회 시작: {album_name} (아티스트: {artist_name or 'N/A'})")
        
        if not YTMUSIC_AVAILABLE:
            logger.warning("ytmusicapi가 설치되지 않아 YouTube Music 조회를 건너뜁니다.")
            return None
        
        ytmusic = cls._get_ytmusic()
        if not ytmusic:
            return None
        
        # 여러 번 시도할 검색어 목록 생성
        search_queries = []
        
        # 1. 원본 이름 (괄호만 제거)
        if artist_name:
            clean_artist = cls._clean_text(artist_name)
            clean_album = cls._clean_text(album_name)
            if clean_artist and clean_album:
                search_queries.append(f"{clean_artist} {clean_album}")
        else:
            clean_album = cls._clean_text(album_name)
            if clean_album:
                search_queries.append(clean_album)
        
        # 2. 특수문자까지 제거한 이름 (가장 깨끗한 버전)
        cleaned_album = cls._clean_album_name(album_name)
        if cleaned_album and cleaned_album != cls._clean_text(album_name):
            if artist_name:
                clean_artist = cls._clean_text(artist_name)
                if clean_artist:
                    search_queries.append(f"{clean_artist} {cleaned_album}")
            else:
                search_queries.append(cleaned_album)
        
        # 3. 아티스트 이름만으로 검색 (최후의 수단)
        if artist_name and len(search_queries) < 3:
            clean_artist = cls._clean_text(artist_name)
            if clean_artist:
                search_queries.append(clean_artist)
        
        # 중복 제거
        search_queries = list(dict.fromkeys(search_queries))
        
        # 각 검색어로 시도
        for search_query in search_queries:
            if not search_query:
                continue
            
            try:
                logger.debug(f"앨범 검색 시도: {search_query}")
                
                # 1. 앨범 검색 (더 많은 결과 가져오기)
                search_results = ytmusic.search(query=search_query, filter="albums", limit=10)
                
                if not search_results:
                    logger.debug(f"검색 결과 없음: {search_query}")
                    continue
                
                # 2. 검색 결과에서 가장 정확한 매칭 찾기
                best_match = cls._find_best_album_match(album_name, artist_name, search_results)
                
                if not best_match:
                    logger.debug(f"적절한 앨범 매칭을 찾지 못함: {search_query}")
                    continue
                
                # 3. browseId 추출
                browse_id = best_match.get("browseId")
                
                if not browse_id:
                    logger.debug(f"browseId를 찾을 수 없음: {search_query}")
                    continue
                
                logger.debug(f"browseId 발견: {browse_id} (매칭 앨범: {best_match.get('title', 'N/A')}, 검색어: {search_query})")
                
                # 4. 앨범 상세 정보 조회
                album_info = ytmusic.get_album(browse_id)
                
                if not album_info:
                    logger.debug(f"앨범 정보를 가져올 수 없음: {browse_id}")
                    continue
                
                # 5. thumbnails에서 가장 큰 이미지 URL 추출
                thumbnails = album_info.get("thumbnails", [])
                
                if not thumbnails:
                    logger.debug(f"thumbnails가 없음: {search_query}")
                    continue
                
                # 가장 큰 이미지 선택 (width 기준)
                largest_thumbnail = max(
                    thumbnails, 
                    key=lambda t: t.get("width", 0) or t.get("height", 0)
                )
                
                image_url = largest_thumbnail.get("url")
                
                if image_url:
                    logger.info(f"YouTube Music 앨범 이미지 조회 성공: {album_name} -> {image_url[:50]}... (검색어: {search_query})")
                    return image_url
                
            except Exception as e:
                logger.debug(f"검색 시도 실패 ({search_query}): {e}")
                continue
        
        # 모든 시도 실패
        logger.info(f"YouTube Music에서 앨범을 찾지 못함: {album_name} (시도한 검색어: {search_queries})")
        return None

    # ==========================
    #  트랙(곡) 기반 이미지 조회
    # ==========================

    @classmethod
    def _find_best_track_match(cls, track_name: str, artist_name: Optional[str], search_results: list) -> Optional[dict]:
        """
        검색 결과에서 가장 정확한 트랙 찾기
        
        - 아티스트 이름이 있는 경우:
          - 곡 제목 유사도와 아티스트명 유사도가 모두 일정 기준 이상일 때만 허용
        - 아티스트 이름이 없는 경우:
          - 곡 제목 유사도 기준만 사용
        """
        if not search_results:
            return None
        
        clean_track = cls._normalize_name(cls._clean_text(track_name))

        aliased_artist = cls._apply_artist_aliases(artist_name) if artist_name else ""
        clean_artist = cls._normalize_name(cls._clean_text(aliased_artist)) if aliased_artist else ""

        best_match = None
        best_score = 0.0
        
        for result in search_results:
            result_title = result.get("title", "")
            result_artists = result.get("artists", [])
            result_artist_names = [a.get("name", "") for a in result_artists] if isinstance(result_artists, list) else []
            
            result_title_norm = cls._normalize_name(result_title)
            
            # 곡 제목 유사도 계산
            title_score = cls._name_similarity(clean_track, result_title_norm)
            
            # 아티스트 이름이 있으면 매칭 확인
            artist_score = 0.0
            if clean_artist:
                for result_artist in result_artist_names:
                    result_artist_norm = cls._normalize_name(result_artist)
                    artist_match = cls._name_similarity(clean_artist, result_artist_norm)
                    artist_score = max(artist_score, artist_match)
            
            # 아티스트 정보가 있는 경우: 곡/아티스트 둘 다 일정 기준 이상이어야 함
            if clean_artist:
                # 곡 제목은 0.5, 아티스트는 0.4 정도만 맞아도 허용 (조금 관대)
                if title_score < 0.5 or artist_score < 0.4:
                    continue
            else:
                # 아티스트 정보가 없으면 곡 제목만으로 0.6 이상 요구
                if title_score < 0.6:
                    continue
            
            # 전체 점수 계산 (제목 70%, 아티스트 30%)
            if clean_artist:
                total_score = title_score * 0.7 + artist_score * 0.3
            else:
                total_score = title_score
            
            # thumbnails가 있는지 확인 (이미지가 있는 결과 우선)
            has_thumbnails = bool(result.get("thumbnails"))
            if has_thumbnails:
                total_score += 0.2
            
            if total_score > best_score:
                best_score = total_score
                best_match = result
        
        if not best_match:
            logger.debug(f"트랙 매칭 실패: {track_name} (아티스트: {artist_name or 'N/A'})")
            return None
        
        logger.debug(
            f"트랙 매칭 성공: 원본='{track_name}', "
            f"선택된 타이틀='{best_match.get('title', '')}', "
            f"최종 점수={best_score:.2f}"
        )
        return best_match

    @classmethod
    def fetch_track_image(cls, track_name: str, artist_name: Optional[str] = None) -> Optional[str]:
        """
        곡(트랙) 이름으로 이미지 URL 조회 (YouTube Music)
        
        - 주로 앨범 이미지를 곡 단위로 추론할 때 사용
        """
        logger.info(f"YouTube Music 트랙 이미지 조회 시작: {track_name} (아티스트: {artist_name or 'N/A'})")
        
        if not YTMUSIC_AVAILABLE:
            logger.warning("ytmusicapi가 설치되지 않아 YouTube Music 조회를 건너뜁니다.")
            return None
        
        ytmusic = cls._get_ytmusic()
        if not ytmusic:
            return None
        
        # 여러 번 시도할 검색어 목록 생성
        search_queries = []
        
        # 1. 아티스트 + 곡 이름
        if artist_name:
            clean_artist = cls._clean_text(artist_name)
            clean_track = cls._clean_text(track_name)
            search_queries.append(f"{clean_artist} {clean_track}")
        else:
            search_queries.append(cls._clean_text(track_name))
        
        # 2. 괄호/하이픈 제거한 곡 이름
        # (예: "Magnetic (Sped Up Ver.)" → "Magnetic")
        base_clean = cls._clean_text(track_name)
        simplified = base_clean.split('-', 1)[0].strip()
        if simplified and simplified != base_clean:
            if artist_name:
                clean_artist = cls._clean_text(artist_name)
                search_queries.append(f"{clean_artist} {simplified}")
            else:
                search_queries.append(simplified)
        
        # 중복 제거
        search_queries = list(dict.fromkeys(search_queries))
        
        for search_query in search_queries:
            if not search_query:
                continue
            
            try:
                logger.debug(f"트랙 검색 시도: {search_query}")
                
                # 곡 검색
                search_results = ytmusic.search(query=search_query, filter="songs", limit=10)
                
                if not search_results:
                    logger.debug(f"트랙 검색 결과 없음: {search_query}")
                    continue
                
                best_match = cls._find_best_track_match(track_name, artist_name, search_results)
                if not best_match:
                    logger.debug(f"적절한 트랙 매칭을 찾지 못함: {search_query}")
                    continue
                
                thumbnails = best_match.get("thumbnails", [])
                if not thumbnails:
                    logger.debug(f"트랙 검색 결과에 thumbnails 없음: {search_query}")
                    continue
                
                largest_thumbnail = max(
                    thumbnails,
                    key=lambda t: t.get("width", 0) or t.get("height", 0)
                )
                image_url = largest_thumbnail.get("url")
                
                if image_url:
                    logger.info(
                        f"YouTube Music 트랙 이미지 조회 성공: {track_name} -> "
                        f"{image_url[:50]}... (검색어: {search_query})"
                    )
                    return image_url
            
            except Exception as e:
                logger.debug(f"트랙 검색 시도 실패 ({search_query}): {e}")
                continue
        
        logger.info(
            f"YouTube Music에서 트랙 이미지를 찾지 못함: {track_name} "
            f"(아티스트: {artist_name or 'N/A'}, 시도한 검색어: {search_queries})"
        )
        return None
    
    @classmethod
    def _find_best_album_match(cls, album_name: str, artist_name: str, search_results: list) -> Optional[dict]:
        """
        검색 결과에서 가장 정확한 앨범 찾기
        
        - 아티스트 이름이 있는 경우:
          - 앨범명 유사도와 아티스트명 유사도가 모두 일정 기준 이상일 때만 허용
        - 아티스트 이름이 없는 경우:
          - 앨범명 유사도 기준만 사용
        """
        if not search_results:
            return None
        
        clean_album = cls._normalize_name(cls._clean_text(album_name))

        # 아티스트 이름에 별칭 매핑 적용 (예: "아일릿" → "ILLIT")
        aliased_artist = cls._apply_artist_aliases(artist_name) if artist_name else ""
        clean_artist = cls._normalize_name(cls._clean_text(aliased_artist)) if aliased_artist else ""
        best_match = None
        best_score = 0.0
        
        for result in search_results:
            result_title = result.get("title", "")
            result_artists = result.get("artists", [])
            result_artist_names = [a.get("name", "") for a in result_artists] if isinstance(result_artists, list) else []
            
            result_title_norm = cls._normalize_name(result_title)
            
            # 앨범 이름 유사도 계산
            album_score = cls._name_similarity(clean_album, result_title_norm)
            
            # 아티스트 이름이 있으면 매칭 확인
            artist_score = 0.0
            if clean_artist:
                for result_artist in result_artist_names:
                    result_artist_norm = cls._normalize_name(result_artist)
                    artist_match = cls._name_similarity(clean_artist, result_artist_norm)
                    artist_score = max(artist_score, artist_match)
            
            # 아티스트 정보가 있는 경우에는 앨범/아티스트 둘 다 일정 기준 이상이어야 함
            if clean_artist:
                # 앨범명과 아티스트명이 모두 어느 정도 맞을 때만 후보로 인정
                # (더 관대하게 0.4 기준으로 완화)
                if album_score < 0.4 or artist_score < 0.4:
                    continue
            else:
                # 아티스트 정보가 없으면 앨범명 일치도를 더 높게 요구
                # (0.5로 완화)
                if album_score < 0.5:
                    continue
            
            # 전체 점수 계산 (앨범 이름 70%, 아티스트 이름 30%)
            if clean_artist:
                total_score = album_score * 0.7 + artist_score * 0.3
            else:
                total_score = album_score
            
            # thumbnails가 있는지 확인 (이미지가 있는 앨범 우선)
            has_thumbnails = bool(result.get("thumbnails"))
            if has_thumbnails:
                total_score += 0.2  # thumbnails가 있으면 보너스 점수
            
            if total_score > best_score:
                best_score = total_score
                best_match = result
        
        if not best_match:
            logger.debug(f"앨범 매칭 실패: {album_name} (아티스트: {artist_name or 'N/A'})")
            return None
        
        logger.debug(
            f"앨범 매칭 성공: 원본='{album_name}', "
            f"선택된 타이틀='{best_match.get('title', '')}', "
            f"최종 점수={best_score:.2f}"
        )
        return best_match
