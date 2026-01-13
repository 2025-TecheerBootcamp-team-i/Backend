
"""
Music 앱의 URL 라우팅
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    RegisterView, 
    LoginView, 
    MusicViewSet, 
    MusicLikeView,
    MusicSearchView,
    MusicDetailView
)

# Router 설정 (ViewSet 자동 라우팅)
router = DefaultRouter()
router.register(r'db/tracks', MusicViewSet, basename='music')

app_name = 'music'

urlpatterns = [
    # 인증 관련
    path('auth/users/', RegisterView.as_view(), name='register'),
    path('auth/tokens/', LoginView.as_view(), name='login'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # iTunes 기반 검색 (새로운 메인 검색)
    # GET /api/v1/search?q={검색어}&exclude_ai={true|false}
    path('search', MusicSearchView.as_view(), name='itunes-search'),
    
    # iTunes ID 기반 상세 조회 (DB에 없으면 자동 저장)
    # GET /api/v1/tracks/{itunes_id}
    path('tracks/<int:itunes_id>', MusicDetailView.as_view(), name='track-detail'),
    
    # 좋아요 등록/취소
    # POST /api/v1/tracks/{music_id}/likes
    # DELETE /api/v1/tracks/{music_id}/likes
    path('tracks/<int:music_id>/likes', MusicLikeView.as_view(), name='music-like'),
    
    # 기존 DB 직접 조회 엔드포인트 (호환성 유지)
    # GET /api/v1/db/tracks - 음악 목록
    # GET /api/v1/db/tracks/{id} - 음악 상세
    path('', include(router.urls)),
]