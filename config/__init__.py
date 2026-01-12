"""
config 패키지 초기화
Django 프로젝트 설정 파일들을 포함합니다.
"""

# Celery 앱이 Django 설정과 함께 로드되도록 함
from .celery import app as celery_app

__all__ = ('celery_app',)
