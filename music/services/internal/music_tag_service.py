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
        ).select_related('tag').order_by('-score')[:20]
        
        if not music_tags.exists():
            return []
        
        # 2. 데이터 정규화 (Normalization)를 위한 전체 점수 합계 계산
        total_score = sum(mt.score for mt in music_tags if mt.score is not None)
        
        # 3. 트리맵 항목 생성
        children = []
        for mt in music_tags:
            score = mt.score or 0.0
            percentage = round((score / total_score * 100), 1) if total_score > 0 else 0.0
            
            # 시각적 구분을 위해 score를 제곱하여 weight 계산 (값이 클수록 더 넓은 영역 차지)
            weight = score ** 2
            
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
