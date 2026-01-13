"""
Celery 비동기 작업 - 차트 계산 및 데이터 정리
"""
import logging
from datetime import timedelta
from celery import shared_task
from django.utils import timezone
from django.utils.timezone import localtime
from django.db.models import Count
from django.db import transaction

from .models import PlayLogs, Charts, Music

logger = logging.getLogger(__name__)


# ============================================================
# 차트 계산 작업
# ============================================================

@shared_task(name='music.tasks.update_realtime_chart')
def update_realtime_chart():
    """
    실시간 차트 갱신 (10분마다 실행)
    - 최근 3시간 동안의 재생 횟수 집계
    - 상위 100곡 저장
    """
    now = timezone.now()
    start_time = now - timedelta(hours=3)
    
    logger.info(f"[실시간 차트] 집계 시작: {start_time} ~ {now}")
    
    try:
        with transaction.atomic():
            # 1. 최근 3시간 재생 집계
            results = PlayLogs.objects.filter(
                played_at__gte=start_time,
                played_at__lt=now,
                is_deleted=False
            ).values('music_id').annotate(
                play_count=Count('play_log_id')
            ).order_by('-play_count')[:100]
            
            if not results:
                logger.info("[실시간 차트] 집계 데이터 없음")
                return {"status": "no_data", "count": 0}
            
            # 2. 기존 동일 시점 차트 삭제 (중복 방지)
            # chart_date를 분 단위로 정규화 (timezone 제거 - DB가 timestamp 타입)
            chart_date = localtime(now).replace(second=0, microsecond=0, tzinfo=None)
            
            # 3. 순위별 차트 저장
            created_count = 0
            for rank, item in enumerate(results, start=1):
                Charts.objects.create(
                    music_id=item['music_id'],
                    play_count=item['play_count'],
                    chart_date=chart_date,
                    rank=rank,
                    type='realtime',
                    created_at=now,
                    updated_at=now,
                    is_deleted=False
                )
                created_count += 1
            
            logger.info(f"[실시간 차트] 갱신 완료: {created_count}개 항목")
            return {"status": "success", "count": created_count}
            
    except Exception as e:
        logger.error(f"[실시간 차트] 오류: {str(e)}")
        raise


@shared_task(name='music.tasks.update_daily_chart')
def update_daily_chart():
    """
    일일 차트 갱신 (매일 자정 실행)
    - 어제 하루 동안의 재생 횟수 집계
    - 전체 곡 상위 100곡 저장
    """
    now = timezone.now()
    yesterday = now - timedelta(days=1)
    yesterday_start = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday_end = yesterday_start + timedelta(days=1)
    
    logger.info(f"[일일 차트] 집계 시작: {yesterday_start} ~ {yesterday_end}")
    
    try:
        with transaction.atomic():
            # 1. 어제 전체 재생 집계
            results = PlayLogs.objects.filter(
                played_at__gte=yesterday_start,
                played_at__lt=yesterday_end,
                is_deleted=False
            ).values('music_id').annotate(
                play_count=Count('play_log_id')
            ).order_by('-play_count')[:100]
            
            if not results:
                logger.info("[일일 차트] 집계 데이터 없음")
                return {"status": "no_data", "count": 0}
            
            # 2. 순위별 차트 저장
            # timezone 제거 (DB가 timestamp 타입)
            chart_date = localtime(yesterday_start).replace(tzinfo=None)
            created_count = 0
            
            for rank, item in enumerate(results, start=1):
                Charts.objects.create(
                    music_id=item['music_id'],
                    play_count=item['play_count'],
                    chart_date=chart_date,
                    rank=rank,
                    type='daily',
                    created_at=now,
                    updated_at=now,
                    is_deleted=False
                )
                created_count += 1
            
            logger.info(f"[일일 차트] 갱신 완료: {created_count}개 항목")
            return {"status": "success", "count": created_count}
            
    except Exception as e:
        logger.error(f"[일일 차트] 오류: {str(e)}")
        raise


@shared_task(name='music.tasks.update_ai_chart')
def update_ai_chart():
    """
    AI 차트 갱신 (매일 자정 실행)
    - 어제 하루 동안의 AI 곡 재생 횟수 집계
    - AI 곡만 상위 100곡 저장
    """
    now = timezone.now()
    yesterday = now - timedelta(days=1)
    yesterday_start = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday_end = yesterday_start + timedelta(days=1)
    
    logger.info(f"[AI 차트] 집계 시작: {yesterday_start} ~ {yesterday_end}")
    
    try:
        with transaction.atomic():
            # 1. 어제 AI 곡 재생 집계
            results = PlayLogs.objects.filter(
                played_at__gte=yesterday_start,
                played_at__lt=yesterday_end,
                is_deleted=False,
                music__is_ai=True,  # AI 곡만
                music__is_deleted=False
            ).values('music_id').annotate(
                play_count=Count('play_log_id')
            ).order_by('-play_count')[:100]
            
            if not results:
                logger.info("[AI 차트] 집계 데이터 없음")
                return {"status": "no_data", "count": 0}
            
            # 2. 순위별 차트 저장
            # timezone 제거 (DB가 timestamp 타입)
            chart_date = localtime(yesterday_start).replace(tzinfo=None)
            created_count = 0
            
            for rank, item in enumerate(results, start=1):
                Charts.objects.create(
                    music_id=item['music_id'],
                    play_count=item['play_count'],
                    chart_date=chart_date,
                    rank=rank,
                    type='ai',
                    created_at=now,
                    updated_at=now,
                    is_deleted=False
                )
                created_count += 1
            
            logger.info(f"[AI 차트] 갱신 완료: {created_count}개 항목")
            return {"status": "success", "count": created_count}
            
    except Exception as e:
        logger.error(f"[AI 차트] 오류: {str(e)}")
        raise


# ============================================================
# 데이터 정리 작업
# ============================================================

@shared_task(name='music.tasks.cleanup_old_playlogs')
def cleanup_old_playlogs():
    """
    오래된 재생 기록 삭제 (매일 새벽 2시 실행)
    - 90일 이전 재생 기록 물리 삭제
    """
    now = timezone.now()
    cutoff = now - timedelta(days=90)
    
    logger.info(f"[PlayLogs 정리] 삭제 기준일: {cutoff}")
    
    try:
        deleted_count, _ = PlayLogs.objects.filter(
            played_at__lt=cutoff
        ).delete()
        
        logger.info(f"[PlayLogs 정리] 삭제 완료: {deleted_count}개")
        return {"status": "success", "deleted_count": deleted_count}
        
    except Exception as e:
        logger.error(f"[PlayLogs 정리] 오류: {str(e)}")
        raise


@shared_task(name='music.tasks.cleanup_old_realtime_charts')
def cleanup_old_realtime_charts():
    """
    오래된 실시간 차트 삭제 (매일 새벽 3시 실행)
    - 7일 이전 실시간 차트 물리 삭제
    - daily, ai 차트는 영구 보관
    """
    now = timezone.now()
    cutoff = now - timedelta(days=7)
    
    logger.info(f"[실시간 차트 정리] 삭제 기준일: {cutoff}")
    
    try:
        deleted_count, _ = Charts.objects.filter(
            type='realtime',
            chart_date__lt=cutoff
        ).delete()
        
        logger.info(f"[실시간 차트 정리] 삭제 완료: {deleted_count}개")
        return {"status": "success", "deleted_count": deleted_count}
        
    except Exception as e:
        logger.error(f"[실시간 차트 정리] 오류: {str(e)}")
        raise
