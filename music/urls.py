"""
Music 앱의 URL 라우팅
"""
from django.urls import path
from . import views
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    RegisterView,
    LoginView,
    MusicLikeView,
    MusicSearchView,
    MusicDetailView,
    MusicPlayView,
    ArtistDetailView,
    ArtistTracksView,
    ArtistAlbumsView,
    ErrorTestView,
    DatabaseQueryTestView,
)

app_name = 'music'

urlpatterns = [
    
    # API 엔드포인트

    # 인증 관련
    path('auth/users/', RegisterView.as_view(), name='register'),
    path('auth/tokens/', LoginView.as_view(), name='login'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # 테스트용 엔드포인트
    # GET /api/v1/test/error?code=500&rate=0.5  # 에러율 테스트
    path('test/error', ErrorTestView.as_view(), name='error-test'),
    # GET /api/v1/test/db?count=10  # Database Queries 테스트
    path('test/db', DatabaseQueryTestView.as_view(), name='db-test'),
    
    # iTunes 기반 검색 (새로운 메인 검색)
    # GET /api/v1/search?q={검색어}&exclude_ai={true|false}
    path('search', MusicSearchView.as_view(), name='itunes-search'),
    
    # iTunes ID 기반 상세 조회 (DB에 없으면 자동 저장)
    # GET /api/v1/tracks/{itunes_id}
    path('tracks/<int:itunes_id>', MusicDetailView.as_view(), name='track-detail'),
    
    # 음악 재생 (audio_url 반환 및 재생 로그 기록)
    # GET /api/v1/tracks/{music_id}/play
    path('tracks/<int:music_id>/play', MusicPlayView.as_view(), name='music-play'),

    # 아티스트 단일 조회
    # GET /api/v1/artists/{artist_id}/
    path('artists/<int:artist_id>/', ArtistDetailView.as_view(), name='artist-detail'),
    
    # 아티스트별 곡 목록 조회
    # GET /api/v1/artists/{artist_id}/tracks/
    path('artists/<int:artist_id>/tracks/', ArtistTracksView.as_view(), name='artist-tracks'),
    
    # 아티스트별 앨범 목록 조회
    # GET /api/v1/artists/{artist_id}/albums/
    path('artists/<int:artist_id>/albums/', ArtistAlbumsView.as_view(), name='artist-albums'),
    
    # 좋아요 등록/취소
    # POST /api/v1/tracks/{music_id}/likes
    # DELETE /api/v1/tracks/{music_id}/likes
    path('tracks/<int:music_id>/likes', MusicLikeView.as_view(), name='music-like'),
    
    # 웹 페이지 (UI)
    path('generator/', views.music_generator_page, name='music_generator_page'),
    path('list/', views.music_list_page, name='music_list_page'),
    path('monitor/<int:music_id>/', views.music_monitor_page, name='music_monitor_page'),
    

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
