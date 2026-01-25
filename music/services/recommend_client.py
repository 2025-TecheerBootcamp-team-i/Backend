"""
OpenSearch 기반 분위기(Valence/Arousal) 아티스트 추천 시스템

Ghost Artist 문제 해결을 위해 iTunes API 대신
OpenSearch 내부의 valence, arousal, genre 데이터를 활용한
콘텐츠 기반 추천 시스템
"""
import logging
from typing import List, Dict, Any, Optional
from opensearchpy.exceptions import OpenSearchException
from django.conf import settings
from .opensearch import opensearch_service


logger = logging.getLogger(__name__)


class RecommendationClient:
    """
    분위기 기반 아티스트 추천 클라이언트
    
    Valence(감정가), Arousal(각성도), Genre를 활용하여
    유사한 분위기의 아티스트를 추천합니다.
    """
    
    def __init__(self):
        """OpenSearch 서비스 초기화"""
        self.opensearch = opensearch_service
        self.index_name = self.opensearch.index_name
    
    def get_recommendations_by_mood(
        self,
        artist_name: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        분위기 기반 아티스트 추천
        
        Args:
            artist_name: 기준 아티스트 이름
            limit: 추천할 아티스트 수 (기본값: 10, 검색한 아티스트 포함)
            
        Returns:
            list: 추천된 아티스트 정보 리스트
                [
                    {
                        'artist_id': int,
                        'artist_name': str,
                        'artist_image': str  # 아티스트 프로필 이미지
                    },
                    ...
                ]
        """
        if not self.opensearch.is_available():
            logger.warning("OpenSearch를 사용할 수 없어 추천을 건너뜁니다.")
            return []
        
        try:
            # Step 1: 기준 아티스트 정보 가져오기
            base_artist = self._get_base_artist(artist_name)
            
            if not base_artist:
                logger.info(f"아티스트 '{artist_name}'를 찾을 수 없습니다.")
                return []
            
            # Step 2: 기준 아티스트의 평균 Valence, Arousal, Main Genre 추출
            artist_stats = self._get_artist_stats(artist_name)
            
            if not artist_stats:
                logger.info(f"아티스트 '{artist_name}'의 통계 정보를 찾을 수 없습니다.")
                # 통계가 없어도 기준 아티스트는 반환
                return [base_artist]
            
            # Step 3: 유사 아티스트 검색 (limit - 1개, 기준 아티스트 제외)
            similar_artists = self._search_similar_artists(
                artist_name=artist_name,
                avg_valence=artist_stats['avg_valence'],
                avg_arousal=artist_stats['avg_arousal'],
                main_genre=artist_stats['main_genre'],
                limit=limit - 1  # 기준 아티스트를 위한 공간 확보
            )
            
            # Step 4: 기준 아티스트를 첫 번째에 추가
            result = [base_artist] + similar_artists
            
            return result
            
        except Exception as e:
            logger.error(f"아티스트 추천 중 오류 발생: {e}")
            return []
    
    def _get_base_artist(self, artist_name: str) -> Optional[Dict[str, Any]]:
        """
        기준 아티스트 정보 가져오기 (DB에서 조회)
        
        Args:
            artist_name: 아티스트 이름
            
        Returns:
            dict: {
                'artist_id': int,
                'artist_name': str,
                'artist_image': str
            } 또는 None
        """
        try:
            from ..models import Artists
            
            # DB에서 아티스트 조회
            artist = Artists.objects.filter(
                artist_name=artist_name,
                is_deleted=False
            ).first()
            
            if not artist:
                return None
            
            return {
                'artist_id': artist.artist_id,
                'artist_name': artist.artist_name,
                'artist_image': artist.artist_image or ''
            }
            
        except Exception as e:
            logger.error(f"기준 아티스트 조회 실패: {e}")
            return None
    
    def _get_artist_stats(self, artist_name: str) -> Optional[Dict[str, Any]]:
        """
        아티스트의 평균 Valence, Arousal, Main Genre 추출
        
        Args:
            artist_name: 아티스트 이름
            
        Returns:
            dict: {
                'avg_valence': float,
                'avg_arousal': float,
                'main_genre': str
            } 또는 None
        """
        try:
            # 아티스트명으로 검색하여 통계 추출
            query = {
                "size": 0,  # 문서는 필요 없고 집계만
                "query": {
                    "bool": {
                        "must": [
                            {
                                "term": {
                                    "artist_name.keyword": artist_name
                                }
                            }
                        ],
                        "filter": [
                            {
                                "exists": {
                                    "field": "valence"
                                }
                            },
                            {
                                "exists": {
                                    "field": "arousal"
                                }
                            }
                        ]
                    }
                },
                "aggs": {
                    "avg_valence": {
                        "avg": {
                            "field": "valence"
                        }
                    },
                    "avg_arousal": {
                        "avg": {
                            "field": "arousal"
                        }
                    },
                    "main_genre": {
                        "terms": {
                            "field": "genre",
                            "size": 1  # 가장 빈도 높은 장르 1개
                        }
                    }
                }
            }
            
            response = self.opensearch.client.search(
                index=self.index_name,
                body=query
            )
            
            # 결과 파싱
            aggs = response.get('aggregations', {})
            
            avg_valence = aggs.get('avg_valence', {}).get('value')
            avg_arousal = aggs.get('avg_arousal', {}).get('value')
            
            # Main Genre 추출
            genre_buckets = aggs.get('main_genre', {}).get('buckets', [])
            main_genre = genre_buckets[0]['key'] if genre_buckets else None
            
            # 유효성 검사
            if avg_valence is None or avg_arousal is None:
                logger.warning(f"아티스트 '{artist_name}'의 valence/arousal 정보가 없습니다.")
                return None
            
            return {
                'avg_valence': avg_valence,
                'avg_arousal': avg_arousal,
                'main_genre': main_genre
            }
            
        except Exception as e:
            logger.error(f"아티스트 통계 추출 실패: {e}")
            return None
    
    def _search_similar_artists(
        self,
        artist_name: str,
        avg_valence: float,
        avg_arousal: float,
        main_genre: Optional[str],
        limit: int
    ) -> List[Dict[str, Any]]:
        """
        유사 아티스트 검색 (function_score 사용)
        
        Args:
            artist_name: 제외할 아티스트 이름 (본인)
            avg_valence: 기준 Valence
            avg_arousal: 기준 Arousal
            main_genre: 메인 장르 (선택사항)
            limit: 결과 수
            
        Returns:
            list: 추천 아티스트 리스트
        """
        try:
            # Function Score 쿼리 구성
            query = {
                "size": limit * 3,  # 충분히 많이 가져와서 중복 제거 후 반환
                "query": {
                    "function_score": {
                        "query": {
                            "bool": {
                                "must": [
                                    {
                                        "exists": {
                                            "field": "valence"
                                        }
                                    },
                                    {
                                        "exists": {
                                            "field": "arousal"
                                        }
                                    }
                                ],
                                "must_not": [
                                    {
                                        "term": {
                                            "artist_name.keyword": artist_name
                                        }
                                    }
                                ],
                                "should": []  # 장르 매칭 (선택사항)
                            }
                        },
                        "functions": [
                            {
                                # Valence 유사도 (Gauss Decay)
                                "gauss": {
                                    "valence": {
                                        "origin": avg_valence,
                                        "scale": 0.2,  # 거리 0.2 이내는 높은 점수
                                        "decay": 0.5  # 감쇠 정도
                                    }
                                },
                                "weight": 1.0
                            },
                            {
                                # Arousal 유사도 (Gauss Decay)
                                "gauss": {
                                    "arousal": {
                                        "origin": avg_arousal,
                                        "scale": 0.2,
                                        "decay": 0.5
                                    }
                                },
                                "weight": 1.0
                            }
                        ],
                        "score_mode": "sum",  # 점수 합산
                        "boost_mode": "replace"  # 기존 점수 무시
                    }
                },
                "collapse": {
                    # 아티스트명으로 그룹핑 (중복 제거)
                    "field": "artist_name.keyword"
                },
                "_source": [
                    "artist_id",
                    "artist_name"
                ]
            }
            
            # 장르 매칭 추가 (선택사항)
            if main_genre:
                query["query"]["function_score"]["query"]["bool"]["should"].append({
                    "term": {
                        "genre": {
                            "value": main_genre,
                            "boost": 1.5  # 같은 장르면 가중치 부여
                        }
                    }
                })
            
            # 검색 실행
            response = self.opensearch.client.search(
                index=self.index_name,
                body=query
            )
            
            # 결과 파싱
            results = []
            seen_artists = set()  # 중복 방지
            artist_ids = []  # DB 조회용 artist_id 리스트
            
            for hit in response['hits']['hits']:
                source = hit['_source']
                artist_name = source.get('artist_name')
                artist_id = source.get('artist_id')
                
                # 이미 추가된 아티스트는 건너뛰기
                if artist_name in seen_artists:
                    continue
                
                seen_artists.add(artist_name)
                
                if artist_id:
                    artist_ids.append(artist_id)
                    results.append({
                        'artist_id': artist_id,
                        'artist_name': artist_name,
                        'artist_image': ''  # DB에서 조회하여 추가
                    })
                
                # limit 만큼만 반환
                if len(results) >= limit:
                    break
            
            # 아티스트 이미지 추가 (DB에서 조회)
            results = self._add_artist_images(results, artist_ids)
            
            logger.info(
                f"아티스트 '{artist_name}' 기반 유사 아티스트 {len(results)}개 검색 완료 "
                f"(Valence: {avg_valence:.2f}, Arousal: {avg_arousal:.2f}, Genre: {main_genre})"
            )
            
            return results
            
        except Exception as e:
            logger.error(f"유사 아티스트 검색 실패: {e}")
            return []
    
    def _add_artist_images(
        self,
        results: List[Dict[str, Any]],
        artist_ids: List[int]
    ) -> List[Dict[str, Any]]:
        """
        추천 결과에 아티스트 이미지 추가 (DB에서 조회)
        
        Args:
            results: 추천 결과 리스트
            artist_ids: 조회할 artist_id 리스트
            
        Returns:
            list: 아티스트 이미지가 추가된 추천 결과
        """
        try:
            from ..models import Artists
            
            # DB에서 한 번에 조회
            if artist_ids:
                artists = Artists.objects.filter(
                    artist_id__in=artist_ids,
                    is_deleted=False
                ).only('artist_id', 'artist_image')
                
                # artist_id를 키로 하는 딕셔너리 생성
                artist_dict = {
                    artist.artist_id: artist.artist_image or ''
                    for artist in artists
                }
                
                # 결과에 이미지 추가
                for result in results:
                    artist_id = result.get('artist_id')
                    if artist_id in artist_dict:
                        result['artist_image'] = artist_dict[artist_id]
            
            return results
            
        except Exception as e:
            logger.error(f"아티스트 이미지 추가 실패: {e}")
            # 실패해도 원본 결과는 반환
            return results


# 싱글톤 인스턴스
recommendation_client = RecommendationClient()
