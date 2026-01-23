"""
음악 추천 관련 Views
"""
import random
from collections import defaultdict
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Count
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from ..models import Music, MusicTags
from ..serializers.music import MusicDetailSerializer


class MusicRecommendationView(APIView):
    """
    음악 추천 API
    
    GET /api/v1/recommendations/?type=tag|genre|emotion&music_id={music_id}&limit=10
    """
    
    @extend_schema(
        summary="음악 추천",
        description="""
        3가지 방식으로 음악을 추천합니다:
        1. tag: 태그 기반 추천 (현재 곡과 같은 태그를 가진 곡)
        2. genre: 장르 기반 추천 (현재 곡과 같은 장르의 곡)
        3. emotion: arousal-valence 기반 추천 (유사한 감정 특성의 곡)
        """,
        parameters=[
            OpenApiParameter(
                name='type',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='추천 방식 (tag|genre|emotion)',
                required=True,
            ),
            OpenApiParameter(
                name='music_id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='기준이 되는 음악 ID',
                required=True,
            ),
            OpenApiParameter(
                name='limit',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='추천 곡 개수 (기본값: 10)',
                required=False,
            ),
        ],
        tags=['음악 추천']
    )
    def get(self, request):
        rec_type = request.query_params.get('type')
        music_id = request.query_params.get('music_id')
        limit = int(request.query_params.get('limit', 10))
        
        if not rec_type or not music_id:
            return Response(
                {'error': 'type과 music_id 파라미터가 필요합니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            base_music = Music.objects.get(music_id=music_id, is_deleted=False)
        except Music.DoesNotExist:
            return Response(
                {'error': '음악을 찾을 수 없습니다.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if rec_type == 'tag':
            recommended = self._recommend_by_tags(base_music, limit)
        elif rec_type == 'genre':
            recommended = self._recommend_by_genre(base_music, limit)
        elif rec_type == 'emotion':
            recommended = self._recommend_by_emotion(base_music, limit)
        else:
            return Response(
                {'error': 'type은 tag, genre, emotion 중 하나여야 합니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = MusicDetailSerializer(recommended, many=True)
        return Response({
            'type': rec_type,
            'base_music_id': music_id,
            'count': len(recommended),
            'results': serializer.data
        })
    
    def _recommend_by_tags(self, base_music, limit):
        """태그 기반 추천"""
        # 현재 곡의 태그 가져오기
        base_tags = MusicTags.objects.filter(
            music=base_music,
            is_deleted=False
        ).select_related('tag').values_list('tag__tag_id', flat=True)
        
        if not base_tags:
            # 태그가 없으면 빈 리스트 반환
            return []
        
        # 같은 태그를 가진 다른 곡들 찾기 (태그 개수로 정렬)
        similar_music_ids = MusicTags.objects.filter(
            tag__tag_id__in=base_tags,
            is_deleted=False
        ).exclude(
            music=base_music
        ).values('music_id').annotate(
            tag_count=Count('tag_id')
        ).order_by('-tag_count')[:limit * 3]  # 더 많이 가져와서 랜덤 선택
        
        # 태그 개수별로 그룹화 (중복 제거)
        tag_count_groups = defaultdict(list)
        seen_music_ids = set()
        for item in similar_music_ids:
            music_id = item['music_id']
            if music_id not in seen_music_ids:
                tag_count_groups[item['tag_count']].append(music_id)
                seen_music_ids.add(music_id)
        
        # 태그 개수가 많은 순서대로, 같은 개수 내에서는 랜덤으로 선택
        music_ids = []
        for tag_count in sorted(tag_count_groups.keys(), reverse=True):
            group_music_ids = tag_count_groups[tag_count]
            random.shuffle(group_music_ids)  # 같은 태그 개수 내에서 랜덤
            music_ids.extend(group_music_ids)
            if len(music_ids) >= limit * 2:
                break
        
        # 최종 추천 곡 조회 (중복 제거, 순서 유지)
        seen = set()
        recommended = []
        for music_id in music_ids:
            if music_id not in seen:
                try:
                    music = Music.objects.select_related('artist', 'album').get(
                        music_id=music_id,
                        is_deleted=False
                    )
                    recommended.append(music)
                    seen.add(music_id)
                    if len(recommended) >= limit:
                        break
                except Music.DoesNotExist:
                    continue
        
        return recommended
    
    def _recommend_by_genre(self, base_music, limit):
        """장르 기반 추천"""
        if not base_music.genre:
            return []
        
        # 같은 장르의 다른 곡들 찾기 (랜덤 정렬, 중복 방지)
        # 더 많이 가져와서 중복 제거 후 limit만큼 반환
        all_music = Music.objects.filter(
            genre=base_music.genre,
            is_deleted=False
        ).exclude(
            music_id=base_music.music_id
        ).select_related('artist', 'album').order_by('?')
        
        # 중복 제거 (music_id 기준)
        seen = set()
        recommended = []
        for music in all_music:
            if music.music_id not in seen:
                recommended.append(music)
                seen.add(music.music_id)
                if len(recommended) >= limit:
                    break
        
        return recommended
    
    def _recommend_by_emotion(self, base_music, limit):
        """Arousal-Valence 기반 추천"""
        if base_music.valence is None or base_music.arousal is None:
            return []
        
        # 유클리드 거리 계산을 위한 SQL 쿼리
        # (valence - base_valence)^2 + (arousal - base_arousal)^2 가 작은 순서로 정렬
        base_valence = float(base_music.valence)
        base_arousal = float(base_music.arousal)
        
        # 유사도 계산: 거리가 가까울수록 유사함
        # 거리 범위를 설정하여 너무 먼 곡은 제외 (예: 거리 < 2.0)
        # 더 많이 가져와서 중복 제거 후 limit만큼 반환
        all_music = Music.objects.filter(
            is_deleted=False,
            valence__isnull=False,
            arousal__isnull=False
        ).exclude(
            music_id=base_music.music_id
        ).extra(
            select={
                'distance': f"""
                    POWER(CAST(valence AS DECIMAL) - {base_valence}, 2) + 
                    POWER(CAST(arousal AS DECIMAL) - {base_arousal}, 2)
                """
            },
            where=[
                f"""
                POWER(CAST(valence AS DECIMAL) - {base_valence}, 2) + 
                POWER(CAST(arousal AS DECIMAL) - {base_arousal}, 2) < 4.0
                """
            ],
            order_by=['distance']
        ).select_related('artist', 'album')[:limit * 2]
        
        # 중복 제거 (music_id 기준)
        seen = set()
        recommended = []
        for music in all_music:
            if music.music_id not in seen:
                recommended.append(music)
                seen.add(music.music_id)
                if len(recommended) >= limit:
                    break
        
        return recommended
