"""
음악 추천 관련 Views
"""
import random
import math
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
    
    GET /api/v1/recommendations/?music_id={music_id}&limit=10
    태그, 장르, 감정 3가지 요소를 모두 고려하여 추천합니다.
    """
    
    @extend_schema(
        summary="음악 추천",
        description="""
        태그, 장르, 감정 3가지 요소를 모두 고려하여 음악을 추천합니다:
        1. 태그: 공통 태그 개수에 따라 점수 부여
        2. 장르: 같은 장르면 점수 부여
        3. 감정: arousal-valence 거리에 따라 점수 부여
        각 요소의 점수를 합산하여 최종 추천 곡을 선정합니다.
        """,
        parameters=[
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
        music_id = request.query_params.get('music_id')
        limit = int(request.query_params.get('limit', 10))
        
        if not music_id:
            return Response(
                {'error': 'music_id 파라미터가 필요합니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            base_music = Music.objects.get(music_id=music_id, is_deleted=False)
        except Music.DoesNotExist:
            return Response(
                {'error': '음악을 찾을 수 없습니다.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # 3가지 요소를 모두 고려한 통합 추천
        recommended_with_scores = self._recommend_combined(base_music, limit)
        
        # 점수 정보와 함께 응답 구성
        results = []
        for item in recommended_with_scores:
            music = item['music']
            serializer = MusicDetailSerializer(music)
            music_data = serializer.data
            music_data['scores'] = {
                'tag_score': round(item['tag_score'], 2),
                'genre_score': round(item['genre_score'], 2),
                'emotion_score': round(item['emotion_score'], 2),
                'total_score': round(item['total_score'], 2)
            }
            results.append(music_data)
        
        return Response({
            'base_music_id': music_id,
            'count': len(results),
            'results': results
        })
    
    def _recommend_combined(self, base_music, limit):
        """태그, 장르, 감정 3가지 요소를 모두 고려한 통합 추천"""
        # 후보 곡들을 가져오기 (충분히 많이)
        candidate_limit = limit * 5
        
        # 1. 태그 기반 후보 가져오기
        tag_candidates = self._get_tag_candidates(base_music, candidate_limit)
        
        # 2. 장르 기반 후보 가져오기
        genre_candidates = self._get_genre_candidates(base_music, candidate_limit)
        
        # 3. 감정 기반 후보 가져오기
        emotion_candidates = self._get_emotion_candidates(base_music, candidate_limit)
        
        # 모든 후보를 합치기 (music_id 기준으로 중복 제거)
        all_candidates = {}
        for music in tag_candidates + genre_candidates + emotion_candidates:
            if music.music_id not in all_candidates:
                all_candidates[music.music_id] = music
        
        if not all_candidates:
            return []
        
        # 각 곡에 대해 점수 계산
        base_tags = set(MusicTags.objects.filter(
            music=base_music,
            is_deleted=False
        ).values_list('tag__tag_id', flat=True))
        
        base_valence = float(base_music.valence) if base_music.valence is not None else None
        base_arousal = float(base_music.arousal) if base_music.arousal is not None else None
        
        scored_music = []
        for music_id, music in all_candidates.items():
            tag_score = 0.0
            genre_score = 0.0
            emotion_score = 0.0
            
            # 태그 점수 계산 (공통 태그 개수, 최대 30점)
            if base_tags:
                music_tags = set(MusicTags.objects.filter(
                    music=music,
                    is_deleted=False
                ).values_list('tag__tag_id', flat=True))
                common_tags = base_tags & music_tags
                # 태그당 점수를 낮추고 최대 30점으로 제한
                tag_score = min(len(common_tags) * 5.0, 30.0)  # 태그당 5점, 최대 30점
            
            # 장르 점수 계산 (같은 장르면 점수 부여)
            if base_music.genre and music.genre and base_music.genre == music.genre:
                genre_score = 10.0  # 같은 장르면 10점
            
            # 감정 점수 계산 (거리가 가까울수록 높은 점수)
            if base_valence is not None and base_arousal is not None:
                if music.valence is not None and music.arousal is not None:
                    distance = math.sqrt(
                        (float(music.valence) - base_valence) ** 2 +
                        (float(music.arousal) - base_arousal) ** 2
                    )
                    # 거리가 0이면 20점, 거리가 멀수록 점수 감소 (최대 거리 4.0 기준)
                    if distance < 4.0:
                        emotion_score = max(0, 20.0 * (1 - distance / 4.0))
            
            total_score = tag_score + genre_score + emotion_score
            
            scored_music.append({
                'music': music,
                'tag_score': tag_score,
                'genre_score': genre_score,
                'emotion_score': emotion_score,
                'total_score': total_score
            })
        
        # 점수 순으로 정렬 (내림차순)
        scored_music.sort(key=lambda x: x['total_score'], reverse=True)
        
        # 점수가 같은 경우 랜덤으로 섞기
        # 점수별로 그룹화
        score_groups = defaultdict(list)
        for item in scored_music:
            score_groups[round(item['total_score'], 2)].append(item)
        
        # 점수가 높은 순서대로, 같은 점수 내에서는 랜덤으로 선택
        final_recommended = []
        for score in sorted(score_groups.keys(), reverse=True):
            group_items = score_groups[score]
            random.shuffle(group_items)
            final_recommended.extend(group_items)
            if len(final_recommended) >= limit:
                break
        
        return final_recommended[:limit]
    
    def _get_tag_candidates(self, base_music, limit):
        """태그 기반 후보 곡들 가져오기"""
        base_tags = MusicTags.objects.filter(
            music=base_music,
            is_deleted=False
        ).values_list('tag__tag_id', flat=True)
        
        if not base_tags:
            return []
        
        similar_music_ids = MusicTags.objects.filter(
            tag__tag_id__in=base_tags,
            is_deleted=False
        ).exclude(
            music=base_music
        ).values('music_id').annotate(
            tag_count=Count('tag_id')
        ).order_by('-tag_count')[:limit]
        
        music_ids = [item['music_id'] for item in similar_music_ids]
        
        candidates = []
        seen = set()
        for music_id in music_ids:
            if music_id not in seen:
                try:
                    music = Music.objects.select_related('artist', 'album').get(
                        music_id=music_id,
                        is_deleted=False
                    )
                    candidates.append(music)
                    seen.add(music_id)
                except Music.DoesNotExist:
                    continue
        
        return candidates
    
    def _get_genre_candidates(self, base_music, limit):
        """장르 기반 후보 곡들 가져오기"""
        if not base_music.genre:
            return []
        
        candidates = list(Music.objects.filter(
            genre=base_music.genre,
            is_deleted=False
        ).exclude(
            music_id=base_music.music_id
        ).select_related('artist', 'album').order_by('?')[:limit])
        
        return candidates
    
    def _get_emotion_candidates(self, base_music, limit):
        """감정 기반 후보 곡들 가져오기"""
        if base_music.valence is None or base_music.arousal is None:
            return []
        
        base_valence = float(base_music.valence)
        base_arousal = float(base_music.arousal)
        
        candidates = list(Music.objects.filter(
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
        ).select_related('artist', 'album')[:limit])
        
        return candidates
    
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
