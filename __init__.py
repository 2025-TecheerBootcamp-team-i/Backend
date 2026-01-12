# Celery 앱을 자동으로 로드하여 Django 시작 시 Celery가 사용 가능하도록 합니다.
from .celery_app import app as celery_app

__all__ = ('celery_app',)
