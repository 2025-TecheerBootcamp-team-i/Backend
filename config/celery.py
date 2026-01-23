import os
from celery import Celery
from celery.signals import task_prerun, task_postrun, task_failure
from prometheus_client import Counter, Histogram, Gauge
from django_prometheus.conf import REGISTRY
import time

# Django의 settings 모듈을 Celery에 기본값으로 설정합니다.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('backend')

# Celery가 Django settings에서 모든 설정 값을 로드하도록 합니다.
# 'CELERY_'로 시작하는 모든 설정 키를 사용합니다.
app.config_from_object('django.conf:settings', namespace='CELERY')

# 등록된 Django 앱 설정에서 모든 task 모듈을 자동으로 찾습니다.
app.autodiscover_tasks()

# ==============================================
# Celery Prometheus 메트릭 정의
# ==============================================

# Celery 작업 실행 횟수
celery_tasks_total = Counter(
    'celery_tasks_total',
    'Total number of tasks executed',
    ['task_name', 'status'],
    registry=REGISTRY
)

# Celery 작업 실행 시간
celery_task_duration = Histogram(
    'celery_task_duration_seconds',
    'Task execution time in seconds',
    ['task_name'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, float('inf')],
    registry=REGISTRY
)

# 현재 실행 중인 Celery 작업 수
celery_tasks_running = Gauge(
    'celery_tasks_running',
    'Number of tasks currently running',
    ['task_name'],
    registry=REGISTRY
)

# 작업 실행 시간 추적을 위한 임시 저장소
task_start_times = {}

@task_prerun.connect
def task_prerun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, **extra):
    """작업 시작 시 메트릭 기록"""
    task_name = task.name if task else sender.name
    task_start_times[task_id] = time.time()
    celery_tasks_running.labels(task_name=task_name).inc()

@task_postrun.connect
def task_postrun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, retval=None, state=None, **extra):
    """작업 완료 시 메트릭 기록"""
    task_name = task.name if task else sender.name
    
    # 실행 시간 계산
    if task_id in task_start_times:
        duration = time.time() - task_start_times[task_id]
        celery_task_duration.labels(task_name=task_name).observe(duration)
        del task_start_times[task_id]
    
    # 완료 카운트
    celery_tasks_total.labels(task_name=task_name, status='success').inc()
    celery_tasks_running.labels(task_name=task_name).dec()

@task_failure.connect
def task_failure_handler(sender=None, task_id=None, exception=None, args=None, kwargs=None, traceback=None, einfo=None, **extra):
    """작업 실패 시 메트릭 기록"""
    task_name = sender.name
    
    # 실행 시간 계산
    if task_id in task_start_times:
        duration = time.time() - task_start_times[task_id]
        celery_task_duration.labels(task_name=task_name).observe(duration)
        del task_start_times[task_id]
    
    # 실패 카운트
    celery_tasks_total.labels(task_name=task_name, status='failure').inc()
    celery_tasks_running.labels(task_name=task_name).dec()

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')