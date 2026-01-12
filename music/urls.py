
"""
Music 앱의 URL 라우팅
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from .views import RegisterView, LoginView, MusicViewSet, MusicLikeView, MusicTagSearchView

# Router 설정 (ViewSet 자동 라우팅)
router = DefaultRouter()
router.register(r'db/tracks', MusicViewSet, basename='music')

app_name = 'music'

urlpatterns = [
    # 인증 관련
    path('auth/users/', RegisterView.as_view(), name='register'),
    path('auth/tokens/', LoginView.as_view(), name='login'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # ViewSet URLs (목록, 상세)
    # GET /api/v1/db/tracks - 음악 목록
    # GET /api/v1/db/tracks/{id} - 음악 상세
    path('', include(router.urls)),
    
    # 태그 검색
    # GET /api/v1/tracks/search/tags
    path('tracks/search/tags', MusicTagSearchView.as_view(), name='music-tag-search'),
    
    # 좋아요 등록/취소
    # POST /api/v1/tracks/{music_id}/likes
    # DELETE /api/v1/tracks/{music_id}/likes
    path('tracks/<int:music_id>/likes', MusicLikeView.as_view(), name='music-like'),
]