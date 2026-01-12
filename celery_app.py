import os
from celery import Celery

# Django의 settings 모듈을 Celery에 기본값으로 설정합니다.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')

app = Celery('backend')

# Celery가 Django settings에서 모든 설정 값을 로드하도록 합니다.
# 'CELERY_'로 시작하는 모든 설정 키를 사용합니다.
app.config_from_object('django.conf:settings', namespace='CELERY')

# 등록된 Django 앱 설정에서 모든 task 모듈을 자동으로 찾습니다.
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')