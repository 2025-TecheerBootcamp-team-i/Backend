"""
AWS OpenSearch 서비스

음악 검색을 위한 OpenSearch 클라이언트 및 인덱싱 기능
"""
import logging
from typing import List, Dict, Any, Optional
from opensearchpy import OpenSearch, RequestsHttpConnection
from opensearchpy.exceptions import OpenSearchException, NotFoundError
from django.conf import settings


logger = logging.getLogger(__name__)


class OpenSearchService:
    """
    AWS OpenSearch 서비스 클래스
    
    음악 데이터를 인덱싱하고 검색하는 기능 제공
    """
    
    def __init__(self):
        """OpenSearch 클라이언트 초기화"""
        self.client = None
        self.index_name = f"{settings.OPENSEARCH_INDEX_PREFIX}_index"
        
        if settings.OPENSEARCH_HOST:
            try:
                self.client = OpenSearch(
                    hosts=[{
                        'host': settings.OPENSEARCH_HOST,
                        'port': settings.OPENSEARCH_PORT
                    }],
                    http_auth=(
                        settings.OPENSEARCH_USERNAME,
                        settings.OPENSEARCH_PASSWORD
                    ),
                    use_ssl=settings.OPENSEARCH_USE_SSL,
                    verify_certs=settings.OPENSEARCH_VERIFY_CERTS,
                    connection_class=RequestsHttpConnection,
                    timeout=30,
                )
                logger.info(f"OpenSearch 클라이언트 초기화 완료: {settings.OPENSEARCH_HOST}")
            except Exception as e:
                logger.error(f"OpenSearch 클라이언트 초기화 실패: {e}")
                self.client = None
        else:
            logger.warning("OPENSEARCH_HOST가 설정되지 않았습니다.")
    
    def is_available(self) -> bool:
        """OpenSearch 사용 가능 여부 확인"""
        if not self.client:
            return False
        try:
            return self.client.ping()
        except Exception as e:
            logger.error(f"OpenSearch 연결 실패: {e}")
            return False
    
    def create_index(self) -> bool:
        """
        음악 검색용 인덱스 생성
        
        Returns:
            bool: 인덱스 생성 성공 여부
        """
        if not self.client:
            logger.error("OpenSearch 클라이언트가 초기화되지 않았습니다.")
            return False
        
        # 인덱스 매핑 정의
        index_body = {
            "settings": {
                "number_of_shards": 2,
                "number_of_replicas": 1,
                "analysis": {
                    "analyzer": {
                        "korean_analyzer": {
                            "type": "custom",
                            "tokenizer": "standard",
                            "filter": ["lowercase", "trim"]
                        },
                        "ngram_analyzer": {
                            "type": "custom",
                            "tokenizer": "standard",
                            "filter": ["lowercase", "ngram_filter"]
                        },
                        "synonym_analyzer": {
                            "type": "custom",
                            "tokenizer": "standard",
                            "filter": ["lowercase", "artist_synonym_filter", "trim"]
                        }
                    },
                    "filter": {
                        "ngram_filter": {
                            "type": "ngram",
                            "min_gram": 2,
                            "max_gram": 10
                        },
                        "artist_synonym_filter": {
                            "type": "synonym",
                            "synonyms_path": "analyzers/F114268915"  # AWS 패키지 ID
                        }
                    }
                }
            },
            "mappings": {
                "properties": {
                    "music_id": {"type": "integer"},
                    "itunes_id": {"type": "long"},
                    "music_name": {
                        "type": "text",
                        "analyzer": "korean_analyzer",
                        "fields": {
                            "ngram": {
                                "type": "text",
                                "analyzer": "ngram_analyzer"
                            },
                            "keyword": {
                                "type": "keyword"
                            }
                        }
                    },
                    "artist_name": {
                        "type": "text",
                        "analyzer": "korean_analyzer",
                        "fields": {
                            "ngram": {
                                "type": "text",
                                "analyzer": "ngram_analyzer"
                            },
                            "keyword": {
                                "type": "keyword"
                            },
                            "synonym": {
                                "type": "text",
                                "analyzer": "synonym_analyzer"
                            }
                        }
                    },
                    "artist_id": {"type": "integer"},
                    "album_name": {
                        "type": "text",
                        "analyzer": "korean_analyzer",
                        "fields": {
                            "ngram": {
                                "type": "text",
                                "analyzer": "ngram_analyzer"
                            }
                        }
                    },
                    "album_id": {"type": "integer"},
                    "genre": {"type": "keyword"},
                    "duration": {"type": "integer"},
                    "is_ai": {"type": "boolean"},
                    "tags": {"type": "keyword"},
                    "lyrics": {
                        "type": "text",
                        "analyzer": "korean_analyzer",
                        "fields": {
                            "ngram": {
                                "type": "text",
                                "analyzer": "ngram_analyzer"
                            }
                        }
                    },
                    "created_at": {"type": "date"},
                    "play_count": {"type": "integer"},
                    "like_count": {"type": "integer"}
                }
            }
        }
        
        try:
            # 인덱스가 이미 존재하는지 확인
            if self.client.indices.exists(index=self.index_name):
                logger.info(f"인덱스 '{self.index_name}'이(가) 이미 존재합니다.")
                return True
            
            # 인덱스 생성
            response = self.client.indices.create(
                index=self.index_name,
                body=index_body
            )
            logger.info(f"인덱스 '{self.index_name}' 생성 완료: {response}")
            return True
            
        except Exception as e:
            logger.error(f"인덱스 생성 실패: {e}")
            return False
    
    def delete_index(self) -> bool:
        """
        인덱스 삭제
        
        Returns:
            bool: 삭제 성공 여부
        """
        if not self.client:
            return False
        
        try:
            if self.client.indices.exists(index=self.index_name):
                self.client.indices.delete(index=self.index_name)
                logger.info(f"인덱스 '{self.index_name}' 삭제 완료")
                return True
            return False
        except Exception as e:
            logger.error(f"인덱스 삭제 실패: {e}")
            return False
    
    def index_music(self, music_data: Dict[str, Any]) -> bool:
        """
        음악 데이터 인덱싱
        
        Args:
            music_data: 인덱싱할 음악 데이터
            
        Returns:
            bool: 인덱싱 성공 여부
        """
        if not self.client:
            return False
        
        try:
            # 필수 필드 확인
            if 'itunes_id' not in music_data:
                logger.error("itunes_id가 없습니다.")
                return False
            
            doc_id = music_data['itunes_id']
            
            response = self.client.index(
                index=self.index_name,
                id=doc_id,
                body=music_data,
                refresh=True
            )
            
            logger.debug(f"음악 인덱싱 완료: {doc_id} - {response['result']}")
            return True
            
        except Exception as e:
            logger.error(f"음악 인덱싱 실패: {e}")
            return False
    
    def bulk_index_music(self, music_list: List[Dict[str, Any]]) -> int:
        """
        여러 음악 데이터 일괄 인덱싱
        
        Args:
            music_list: 인덱싱할 음악 데이터 리스트
            
        Returns:
            int: 성공적으로 인덱싱된 문서 수
        """
        if not self.client or not music_list:
            return 0
        
        try:
            from opensearchpy.helpers import bulk
            
            actions = []
            for music in music_list:
                if 'itunes_id' not in music:
                    continue
                
                action = {
                    '_index': self.index_name,
                    '_id': music['itunes_id'],
                    '_source': music
                }
                actions.append(action)
            
            if not actions:
                return 0
            
            success, failed = bulk(
                self.client,
                actions,
                refresh=True,
                raise_on_error=False
            )
            
            logger.info(f"일괄 인덱싱 완료: 성공 {success}개, 실패 {len(failed)}개")
            return success
            
        except Exception as e:
            logger.error(f"일괄 인덱싱 실패: {e}")
            return 0
    
    def delete_music(self, itunes_id: int) -> bool:
        """
        음악 문서 삭제
        
        Args:
            itunes_id: iTunes ID
            
        Returns:
            bool: 삭제 성공 여부
        """
        if not self.client:
            return False
        
        try:
            self.client.delete(
                index=self.index_name,
                id=itunes_id,
                refresh=True
            )
            logger.info(f"음악 문서 삭제 완료: {itunes_id}")
            return True
            
        except NotFoundError:
            logger.warning(f"삭제할 문서를 찾을 수 없음: {itunes_id}")
            return False
        except Exception as e:
            logger.error(f"음악 문서 삭제 실패: {e}")
            return False
    
    def search(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        size: int = 20,
        from_: int = 0,
        sort_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        음악 검색
        
        Args:
            query: 검색어
            filters: 필터 조건 (예: {"is_ai": False, "genre": "Pop"})
            size: 결과 개수
            from_: 시작 위치 (페이지네이션)
            sort_by: 정렬 기준 ("relevance", "popularity", "recent")
            
        Returns:
            dict: 검색 결과
        """
        if not self.client:
            return {
                'total': 0,
                'hits': [],
                'error': 'OpenSearch 클라이언트가 초기화되지 않았습니다.'
            }
        
        try:
            # 검색 쿼리 구성
            search_body = {
                "query": self._build_search_query(query, filters),
                "size": size,
                "from": from_
            }
            
            # 정렬 추가
            if sort_by:
                search_body["sort"] = self._build_sort(sort_by)
            
            # 하이라이트 추가
            search_body["highlight"] = {
                "fields": {
                    "music_name": {},
                    "artist_name": {},
                    "album_name": {},
                    "lyrics": {
                        "fragment_size": 150,  # 가사는 150자까지만 표시
                        "number_of_fragments": 3  # 최대 3개 조각
                    }
                }
            }
            
            # 검색 실행
            response = self.client.search(
                index=self.index_name,
                body=search_body
            )
            
            # 결과 파싱
            total = response['hits']['total']['value']
            hits = []
            
            for hit in response['hits']['hits']:
                source = hit['_source']
                source['_score'] = hit['_score']
                
                # 하이라이트 추가
                if 'highlight' in hit:
                    source['_highlight'] = hit['highlight']
                
                hits.append(source)
            
            return {
                'total': total,
                'hits': hits
            }
            
        except Exception as e:
            logger.error(f"검색 실패: {e}")
            return {
                'total': 0,
                'hits': [],
                'error': str(e)
            }
    
    def _build_search_query(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        검색 쿼리 구성
        
        Args:
            query: 검색어
            filters: 필터 조건
            
        Returns:
            dict: OpenSearch 쿼리 DSL
        """
        must_clauses = []
        filter_clauses = []
        
        # 텍스트 검색 쿼리
        if query and query.strip():
            must_clauses.append({
                "multi_match": {
                    "query": query,
                    "fields": [
                        "artist_name^5",          # 아티스트명에 가중치 5 (최우선)
                        "artist_name.synonym^5",  # 아티스트 동의어에 가중치 5
                        "artist_name.ngram^4",    # 아티스트명 ngram에 가중치 4
                        "music_name^3",           # 곡명에 가중치 3
                        "music_name.ngram^2",     # 곡명 ngram에 가중치 2
                        "lyrics^2",               # 가사에 가중치 2
                        "lyrics.ngram",           # 가사 ngram
                        "album_name^0.5",         # 앨범명 (낮은 가중치)
                        "album_name.ngram^0.5"    # 앨범명 ngram (낮은 가중치)
                    ],
                    "type": "best_fields",
                    "fuzziness": "AUTO"
                }
            })
        else:
            # 검색어가 없으면 모든 문서 반환
            must_clauses.append({"match_all": {}})
        
        # 필터 조건 추가
        if filters:
            for key, value in filters.items():
                if value is not None:
                    if isinstance(value, list):
                        # 리스트는 terms 쿼리
                        filter_clauses.append({"terms": {key: value}})
                    elif isinstance(value, bool):
                        # 불린은 term 쿼리
                        filter_clauses.append({"term": {key: value}})
                    else:
                        # 그 외는 match 쿼리
                        filter_clauses.append({"term": {key: value}})
        
        # bool 쿼리 구성
        bool_query = {
            "bool": {
                "must": must_clauses
            }
        }
        
        if filter_clauses:
            bool_query["bool"]["filter"] = filter_clauses
        
        return bool_query
    
    def _build_sort(self, sort_by: str) -> List[Dict[str, Any]]:
        """
        정렬 조건 구성
        
        Args:
            sort_by: 정렬 기준
            
        Returns:
            list: OpenSearch 정렬 조건
        """
        if sort_by == "popularity":
            return [
                {"play_count": {"order": "desc"}},
                {"like_count": {"order": "desc"}},
                "_score"
            ]
        elif sort_by == "recent":
            return [
                {"created_at": {"order": "desc"}},
                "_score"
            ]
        else:  # relevance (기본값)
            return ["_score"]
    
    def suggest(self, prefix: str, size: int = 10) -> List[str]:
        """
        자동완성 제안
        
        Args:
            prefix: 입력 프리픽스
            size: 제안 개수
            
        Returns:
            list: 제안 목록
        """
        if not self.client or not prefix:
            return []
        
        try:
            search_body = {
                "suggest": {
                    "music-suggest": {
                        "prefix": prefix,
                        "completion": {
                            "field": "music_name.keyword",
                            "size": size,
                            "skip_duplicates": True
                        }
                    },
                    "artist-suggest": {
                        "prefix": prefix,
                        "completion": {
                            "field": "artist_name.keyword",
                            "size": size,
                            "skip_duplicates": True
                        }
                    }
                }
            }
            
            response = self.client.search(
                index=self.index_name,
                body=search_body
            )
            
            suggestions = []
            
            # 음악 제안
            for option in response['suggest']['music-suggest'][0]['options']:
                suggestions.append(option['text'])
            
            # 아티스트 제안
            for option in response['suggest']['artist-suggest'][0]['options']:
                suggestions.append(option['text'])
            
            # 중복 제거 및 정렬
            return list(set(suggestions))[:size]
            
        except Exception as e:
            logger.error(f"자동완성 제안 실패: {e}")
            return []


# 싱글톤 인스턴스
opensearch_service = OpenSearchService()
