from django.urls import path
from . import views

app_name = 'music'

urlpatterns = [
    # 웹 페이지 (UI)
    path('generator/', views.music_generator_page, name='music_generator_page'),
    path('list/', views.music_list_page, name='music_list_page'),
    path('monitor/<int:music_id>/', views.music_monitor_page, name='music_monitor_page'),
    
    # API 엔드포인트
    # 음악 생성 (동기)
    path('generate/', views.generate_music, name='generate_music'),
    
    # 음악 생성 (비동기 - Celery)
    path('generate-async/', views.generate_music_async, name='generate_music_async'),
    
    # Suno API 웹훅 (음악 생성 완료 콜백)
    path('webhook/suno/', views.suno_webhook, name='suno_webhook'),
    
    # 작업 상태 조회 (Celery)
    path('task/<str:task_id>/', views.get_task_status, name='get_task_status'),
    
    # Suno API 작업 상태 조회 (Polling용)
    path('suno-task/<str:task_id>/', views.get_suno_task_status, name='get_suno_task_status'),
    
    # 음악 목록 조회
    path('', views.list_music, name='list_music'),
    
    # 음악 상세 조회
    path('<int:music_id>/', views.get_music_detail, name='get_music_detail'),
]
