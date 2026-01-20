"""
데이터 정리 관련 Celery 작업
"""
import logging
from datetime import timedelta
from celery import shared_task
from django.utils import timezone

from ..models import PlayLogs, Charts

logger = logging.getLogger(__name__)


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
