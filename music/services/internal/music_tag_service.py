"""
음악 태그 관련 서비스
특정 음악의 태그 분석 및 그래프 데이터 제공
"""
import logging
from typing import List, Dict, Any
from django.db.models import Sum
from ...models import Music, MusicTags

logger = logging.getLogger(__name__)

class MusicTagService:
    """음악 태그 분석 서비스"""

    @classmethod
    def get_tag_graph_data(cls, music_id: int) -> List[Dict[str, Any]]:
        """
        특정 음악의 태그 밀접도(score)를 기반으로 트리맵용 데이터를 생성합니다.
        
        Args:
            music_id: 음악 ID
            
        Returns:
            Recharts Treemap 호환 데이터 구조
            [
                {
                    "name": "Tags",
                    "children": [
                        {"name": "태그1", "size": 0.64, "score": 0.8, "percentage": 45.5},
                        ...
                    ]
                }
            ]
        """
        # 1. 해당 곡의 태그와 score 가져오기
        # SoftDeleteManager가 자동으로 is_deleted=False인 레코드만 조회
        music_tags = MusicTags.objects.filter(
            music_id=music_id,
            tag__is_deleted=False
        ).select_related('tag').order_by('-score')[:6]
        
        if not music_tags.exists():
            return []
        
        # 2. 데이터 정규화 (Normalization)를 위한 전체 점수 합계 계산
        total_score = sum(mt.score for mt in music_tags if mt.score is not None)
        
        # 3. 트리맵 항목 생성
        children = []
        for mt in music_tags:
            score = mt.score or 0.0
            percentage = round((score / total_score * 100), 1) if total_score > 0 else 0.0
            
            # 시각적 구분을 위해 score를 세제곱하여 weight 계산 (값이 클수록 더 넓은 영역 차지)
            weight = score ** 3
            
            children.append({
                "tag": mt.tag, # Serializer에서 tag.tag_key를 꺼내도록 mt.tag 객체 전달
                "score": score,
                "weight": weight,
                "percentage": percentage
            })
            
        # 4. Recharts Treemap 구조로 반환
        return [
            {
                "name": "Tags",
                "children": children
            }
        ]

    @classmethod
    def get_curated_station_data(cls) -> List[Dict[str, Any]]:
        """
        DJ 스테이션용 큐레이션 음악 데이터 반환
        지정된 리스트(STATION_CURATION)에 있는 음악들을 DB에서 조회하여 반환
        """
        import random
        from django.db.models import Q
        from .station_data import STATION_CURATION

        station_data = []

        for category, song_list in STATION_CURATION.items():
            # 1. 쿼리 구성: (제목 AND 아티스트) OR (제목 AND 아티스트) ...
            # 정확한 매칭을 위해 제목과 아티스트를 모두 조건으로 사용
            q_objects = Q()
            for song in song_list:
                q_objects |= Q(music_name__iexact=song['title'], artist__artist_name__iexact=song['artist'])
            
            # 2. DB 조회
            found_songs = Music.objects.filter(
                q_objects,
                is_deleted=False
            ).select_related('artist', 'album')

            # 3. 데이터 변환
            tracks = []
            for music in found_songs:
                tracks.append({
                    "music_id": music.music_id,
                    "music_name": music.music_name,
                    "artist": music.artist.artist_name if music.artist else "Unknown",
                    "album_image": music.album.album_image if music.album else "",
                    "likes": 0  # 큐레이션이므로 좋아요 수는 표시용으로만 사용하거나 생략 가능 (필요시 조인)
                })
            
            # 4. 셔플 (장르 섞기)
            random.shuffle(tracks)
            
            # 5. 결과 추가 (곡이 하나라도 있는 경우만)
            if tracks:
                # 키워드는 카테고리 이름의 첫 단어 등을 사용하거나 별도 매핑 필요
                # 여기서는 카테고리 이름 그대로 사용
                station_data.append({
                    "category": category,
                    "keyword": category, 
                    "tracks": tracks
                })
        
        return station_data
