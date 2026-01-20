"""
공통 및 테스트용 Celery 작업
"""
import time
import logging
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def test_task(self, message: str = "테스트 메시지", delay_seconds: int = 1):
    """
    RabbitMQ 메트릭 테스트용 간단한 작업
    
    Args:
        message: 출력할 메시지
        delay_seconds: 대기 시간 (초)
    
    Returns:
        작업 완료 메시지
    """
    logger.info(f"테스트 작업 시작: {message}")
    time.sleep(delay_seconds)  # 지정된 시간만큼 대기
    logger.info(f"테스트 작업 완료: {message}")
    return {"status": "success", "message": message, "task_id": self.request.id}
