"""
음악 태그 관련 서비스
특정 음악의 태그 분석 및 그래프 데이터 제공
"""
import logging
from typing import List, Dict, Any
from django.db.models import Sum
from ...models import Music, MusicTags
from ...serializers.music import MusicPlaySerializer

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
        STATION_DATA에 있는 음악들을 DB에서 조회하여 반환
        
        Returns:
            [
                {
                    "theme": "느낌 별 스테이션", # or "Genre"
                    "station_data": [
                         { "category": "신나는 노래", "tracks": [...] },
                         ...
                    ]
                },
                ...
            ]
        """
        import random
        from django.db.models import Q
        from .station_data import STATION_DATA

        result = []
        
        # STATION_DATA = { "mood": {...}, "genre": {...} }
        theme_titles = {
            "mood": "느낌 별 스테이션",
            "genre": "장르 별 스테이션"
        }

        for theme_key, stations in STATION_DATA.items():
            
            theme_station_list = []
            
            for category, song_list in stations.items():
                # 1. 쿼리 구성
                q_objects = Q()
                for song in song_list:
                    # 정확도가 중요하므로 author, title 모두 체크 (부분일치 iexact 사용)
                    # DB에 저장된 아티스트명과 입력된 아티스트명이 다를 수 있음 (예: 세븐틴 vs SEVENTEEN)
                    # 지금은 정확한 매칭을 시도
                    q_objects |= Q(music_name__iexact=song['title'], artist__artist_name__icontains=song['artist'])
                    # OR 조건으로 유연하게 하고 싶다면:
                    # q_objects |= (Q(music_name__iexact=song['title']) & Q(artist__artist_name__icontains=song['artist']))
                
                if not q_objects:
                    continue

                # 2. DB 조회
                found_songs = Music.objects.filter(
                    q_objects,
                    is_deleted=False
                ).select_related('artist', 'album')

                # 3. 데이터 변환 (Serializer 사용)
                #    MusicPlaySerializer를 사용하여 재생에 필요한 모든 정보(audio_url 등)를 포함
                tracks = []
                for music in found_songs:
                    tracks.append(MusicPlaySerializer(music).data)
                
                # 4. 셔플
                random.shuffle(tracks)
                
                # 5. 결과 추가
                if tracks:
                    theme_station_list.append({
                        "category": category,
                        "keyword": category, 
                        "tracks": tracks
                    })
            
            if theme_station_list:
                result.append({
                    "theme": theme_titles.get(theme_key, theme_key),
                    "station_data": theme_station_list
                })
        
        return result
