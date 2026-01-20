"""
사용자 음악 통계 서비스

PlayLogs 테이블을 기반으로 사용자별 음악 청취 통계를 제공합니다.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from django.db.models import Sum, Count, F, Q
from django.db.models.functions import Coalesce
from django.utils import timezone

from music.models import PlayLogs, Music, MusicTags, Tags, Artists, AiInfo

logger = logging.getLogger(__name__)


class UserStatisticsService:
    """사용자 음악 통계 서비스"""

    @classmethod
    def get_listening_time(
        cls,
        user_id: int,
        period: str = 'month'
    ) -> Dict[str, Any]:
        """
        사용자의 총 청취 시간을 계산합니다.
        
        Args:
            user_id: 사용자 ID
            period: 기간 ('month' = 이번 달, 'all' = 전체)
        
        Returns:
            {
                'total_seconds': int,  # 총 청취 시간 (초)
                'total_hours': float,  # 총 청취 시간 (시간)
                'play_count': int,     # 재생 횟수
                'previous_period_hours': float,  # 이전 기간 청취 시간
                'change_percent': float  # 변화율 (%)
            }
        """
        now = timezone.now()
        
        # 기간 설정
        if period == 'month':
            # 이번 달 시작
            start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            # 지난 달 시작/끝
            prev_month_end = start_date - timedelta(days=1)
            prev_month_start = prev_month_end.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            start_date = None
            prev_month_start = None
            prev_month_end = None
        
        # 현재 기간 쿼리
        # SoftDeleteManager가 자동으로 is_deleted=False인 레코드만 조회
        query = PlayLogs.objects.filter(user_id=user_id).select_related('music')
        
        if start_date:
            query = query.filter(played_at__gte=start_date)
        
        # 재생 로그에서 음악의 duration 합산
        # PlayLogs -> Music -> duration
        result = query.aggregate(
            total_seconds=Coalesce(Sum('music__duration'), 0),
            play_count=Count('play_log_id')
        )
        
        total_seconds = result['total_seconds'] or 0
        play_count = result['play_count'] or 0
        total_hours = round(total_seconds / 3600, 1)
        
        # 이전 기간 계산 (월별 비교용)
        previous_hours = 0.0
        change_percent = 0.0
        
        if period == 'month' and prev_month_start and prev_month_end:
            # SoftDeleteManager가 자동으로 is_deleted=False인 레코드만 조회
            prev_query = PlayLogs.objects.filter(
                user_id=user_id,
                played_at__gte=prev_month_start,
                played_at__lt=start_date
            )
            prev_result = prev_query.aggregate(
                total_seconds=Coalesce(Sum('music__duration'), 0)
            )
            prev_seconds = prev_result['total_seconds'] or 0
            previous_hours = round(prev_seconds / 3600, 1)
            
            # 변화율 계산
            if previous_hours > 0:
                change_percent = round(((total_hours - previous_hours) / previous_hours) * 100, 1)
            elif total_hours > 0:
                change_percent = 100.0
        
        return {
            'total_seconds': total_seconds,
            'total_hours': total_hours,
            'play_count': play_count,
            'previous_period_hours': previous_hours,
            'change_percent': change_percent
        }

    @classmethod
    def get_top_genres(
        cls,
        user_id: int,
        period: str = 'month',
        limit: int = 3
    ) -> List[Dict[str, Any]]:
        """
        사용자가 가장 많이 들은 장르를 반환합니다.
        
        Args:
            user_id: 사용자 ID
            period: 기간 ('month' = 이번 달, 'all' = 전체)
            limit: 반환할 장르 수
        
        Returns:
            [
                {'genre': str, 'play_count': int, 'percentage': float},
                ...
            ]
        """
        now = timezone.now()
        
        # SoftDeleteManager가 자동으로 is_deleted=False인 레코드만 조회
        query = PlayLogs.objects.filter(
            user_id=user_id,
            music__genre__isnull=False
        ).exclude(music__genre='')
        
        if period == 'month':
            start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            query = query.filter(played_at__gte=start_date)
        
        # 장르별 재생 횟수 집계
        genre_stats = query.values('music__genre').annotate(
            play_count=Count('play_log_id')
        ).order_by('-play_count')[:limit]
        
        # 전체 재생 횟수
        total_plays = query.count()
        
        result = []
        for idx, stat in enumerate(genre_stats, 1):
            percentage = round((stat['play_count'] / total_plays * 100), 1) if total_plays > 0 else 0
            result.append({
                'rank': idx,
                'genre': stat['music__genre'],
                'play_count': stat['play_count'],
                'percentage': percentage
            })
        
        return result

    @classmethod
    def get_top_artists(
        cls,
        user_id: int,
        period: str = 'month',
        limit: int = 3
    ) -> List[Dict[str, Any]]:
        """
        사용자가 가장 많이 들은 아티스트를 반환합니다.
        
        Args:
            user_id: 사용자 ID
            period: 기간 ('month' = 이번 달, 'all' = 전체)
            limit: 반환할 아티스트 수
        
        Returns:
            [
                {
                    'rank': int,
                    'artist_id': int,
                    'artist_name': str,
                    'artist_image': str,
                    'play_count': int,
                    'percentage': float
                },
                ...
            ]
        """
        now = timezone.now()
        
        # SoftDeleteManager가 자동으로 is_deleted=False인 레코드만 조회
        query = PlayLogs.objects.filter(
            user_id=user_id,
            music__artist__isnull=False
        )
        
        if period == 'month':
            start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            query = query.filter(played_at__gte=start_date)
        
        # 아티스트별 재생 횟수 집계 (image_square와 artist_image 모두 가져오기)
        artist_stats = query.values(
            'music__artist__artist_id',
            'music__artist__artist_name',
            'music__artist__artist_image',
            'music__artist__image_square'
        ).annotate(
            play_count=Count('play_log_id')
        ).order_by('-play_count')[:limit]
        
        # 전체 재생 횟수
        total_plays = query.count()
        
        result = []
        for idx, stat in enumerate(artist_stats, 1):
            percentage = round((stat['play_count'] / total_plays * 100), 1) if total_plays > 0 else 0
            # image_square가 있으면 사용, 없으면 artist_image 사용
            artist_image = stat.get('music__artist__image_square') or stat.get('music__artist__artist_image')
            result.append({
                'rank': idx,
                'artist_id': stat['music__artist__artist_id'],
                'artist_name': stat['music__artist__artist_name'],
                'artist_image': artist_image,
                'play_count': stat['play_count'],
                'percentage': percentage
            })
        
        return result

    @classmethod
    def get_top_tags(
        cls,
        user_id: int,
        period: str = 'month',
        limit: int = 6
    ) -> List[Dict[str, Any]]:
        """
        사용자가 가장 많이 들은 음악의 태그(분위기/키워드)를 반환합니다.
        
        Args:
            user_id: 사용자 ID
            period: 기간 ('month' = 이번 달, 'all' = 전체)
            limit: 반환할 태그 수
        
        Returns:
            [
                {'tag_id': int, 'tag_key': str, 'play_count': int},
                ...
            ]
        """
        now = timezone.now()
        
        # PlayLogs에서 사용자가 들은 music_id 목록 추출
        # SoftDeleteManager가 자동으로 is_deleted=False인 레코드만 조회
        play_query = PlayLogs.objects.filter(user_id=user_id)
        
        if period == 'month':
            start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            play_query = play_query.filter(played_at__gte=start_date)
        
        # 들은 음악 ID 목록
        played_music_ids = play_query.values_list('music_id', flat=True)
        
        # 해당 음악들의 태그 집계
        # SoftDeleteManager가 자동으로 is_deleted=False인 레코드만 조회
        tag_stats = MusicTags.objects.filter(
            music_id__in=played_music_ids
        ).values(
            'tag__tag_id',
            'tag__tag_key'
        ).annotate(
            play_count=Count('music_id')
        ).order_by('-play_count')[:limit]
        
        result = []
        for stat in tag_stats:
            result.append({
                'tag_id': stat['tag__tag_id'],
                'tag_key': stat['tag__tag_key'],
                'play_count': stat['play_count']
            })
        
        return result

    @classmethod
    def get_ai_generation_stats(
        cls,
        user_id: int,
        period: str = 'month'
    ) -> Dict[str, Any]:
        """
        사용자의 AI 음악 생성 활동 통계를 반환합니다.
        
        Args:
            user_id: 사용자 ID
            period: 기간 ('month' = 이번 달, 'all' = 전체)
        
        Returns:
            {
                'total_generated': int,  # 생성한 AI 곡 수
                'last_generated_at': datetime,  # 마지막 생성 일시
                'last_generated_days_ago': int  # 마지막 생성 며칠 전
            }
        """
        now = timezone.now()
        
        # AI 생성 음악은 Music 테이블에서 is_ai=True, user_id로 필터
        # SoftDeleteManager가 자동으로 is_deleted=False인 레코드만 조회
        query = Music.objects.filter(
            user_id=user_id,
            is_ai=True
        )
        
        if period == 'month':
            start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            query = query.filter(created_at__gte=start_date)
        
        total_generated = query.count()
        
        # 마지막 생성 일시
        last_music = query.order_by('-created_at').first()
        last_generated_at = last_music.created_at if last_music else None
        last_generated_days_ago = None
        
        if last_generated_at:
            delta = now - last_generated_at
            last_generated_days_ago = delta.days
        
        return {
            'total_generated': total_generated,
            'last_generated_at': last_generated_at,
            'last_generated_days_ago': last_generated_days_ago
        }

    @classmethod
    def get_full_statistics(
        cls,
        user_id: int,
        period: str = 'month'
    ) -> Dict[str, Any]:
        """
        사용자의 전체 음악 분석 데이터를 반환합니다.
        
        Args:
            user_id: 사용자 ID
            period: 기간 ('month' = 이번 달, 'all' = 전체)
        
        Returns:
            {
                'listening_time': {...},
                'top_genres': [...],
                'top_artists': [...],
                'top_tags': [...],
                'ai_generation': {...}
            }
        """
        return {
            'listening_time': cls.get_listening_time(user_id, period),
            'top_genres': cls.get_top_genres(user_id, period),
            'top_artists': cls.get_top_artists(user_id, period),
            'top_tags': cls.get_top_tags(user_id, period),
            'ai_generation': cls.get_ai_generation_stats(user_id, period)
        }
