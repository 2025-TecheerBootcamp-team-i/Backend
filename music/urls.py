"""
Music 앱의 URL 라우팅
"""
from django.urls import path
from . import views
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    RegisterView,
    LoginView,
    TokenRefreshView,
    MusicLikeView,
    MusicSearchView,
    MusicDetailView,
    ArtistDetailView,
    ArtistTracksView,
    ArtistAlbumsView,
    AlbumDetailView,
    PopularArtistsView,
    ErrorTestView,
    DatabaseQueryTestView,
    PlayLogView,
    ChartView,
    # 사용자 통계
    UserStatisticsView,
    UserListeningTimeView,
    UserTopGenresView,
    UserTopArtistsView,
    UserTopTagsView,
    UserTopTracksView,
    UserAIGenerationView,
    # 플레이리스트
    PlaylistListCreateView,
    PlaylistDetailView,
    PlaylistItemAddView,
    PlaylistItemDeleteView,
    PlaylistLikeView,
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
    
    # 음악 재생 정보 조회 및 재생 로그 기록
    # GET /api/v1/tracks/{music_id}/play - 재생 정보 조회 (로그 저장 안 함)
    # POST /api/v1/tracks/{music_id}/play - 재생 로그 기록
    path('tracks/<int:music_id>/play', PlayLogView.as_view(), name='music-play'),

    # 인기 아티스트 목록 조회
    # GET /api/v1/artists/popular?limit=7
    path('artists/popular', PopularArtistsView.as_view(), name='popular-artists'),
    
    # 아티스트 단일 조회
    # GET /api/v1/artists/{artist_id}/
    path('artists/<int:artist_id>/', ArtistDetailView.as_view(), name='artist-detail'),
    
    # 아티스트별 곡 목록 조회
    # GET /api/v1/artists/{artist_id}/tracks/
    path('artists/<int:artist_id>/tracks/', ArtistTracksView.as_view(), name='artist-tracks'),
    
    # 아티스트별 앨범 목록 조회
    # GET /api/v1/artists/{artist_id}/albums/
    path('artists/<int:artist_id>/albums/', ArtistAlbumsView.as_view(), name='artist-albums'),
    
    # 앨범 상세 조회
    # GET /api/v1/albums/{album_id}/
    path('albums/<int:album_id>/', AlbumDetailView.as_view(), name='album-detail'),
    
    # 좋아요 등록/취소
    # POST /api/v1/tracks/{music_id}/likes
    # DELETE /api/v1/tracks/{music_id}/likes
    path('tracks/<int:music_id>/likes', MusicLikeView.as_view(), name='music-like'),
    
    # 차트 조회
    # GET /api/v1/charts/{type} (realtime|daily|ai)
    path('charts/<str:type>', ChartView.as_view(), name='charts'),
    
    # ========================
    # 플레이리스트 API
    # ========================
    # 플레이리스트 목록 조회 (GET) & 생성 (POST)
    # GET /api/v1/playlists  - 목록 조회
    # POST /api/v1/playlists - 생성
    path('playlists', PlaylistListCreateView.as_view(), name='playlist-list-create'),
    
    # 플레이리스트 상세 조회 (GET) & 수정 (PATCH) & 삭제 (DELETE)
    # GET /api/v1/playlists/{playlistId}    - 상세 조회
    # PATCH /api/v1/playlists/{playlistId}  - 수정
    # DELETE /api/v1/playlists/{playlistId} - 삭제
    path('playlists/<int:playlist_id>', PlaylistDetailView.as_view(), name='playlist-detail'),
    
    # 플레이리스트 곡 추가 (POST)
    # POST /api/v1/playlists/{playlistId}/items
    path('playlists/<int:playlist_id>/items', PlaylistItemAddView.as_view(), name='playlist-item-add'),
    
    # 플레이리스트 곡 삭제 (DELETE)
    # DELETE /api/v1/playlists/items/{itemsId}
    path('playlists/items/<int:item_id>', PlaylistItemDeleteView.as_view(), name='playlist-item-delete'),
    
    # 플레이리스트 좋아요 등록 (POST) & 취소 (DELETE)
    # POST /api/v1/playlists/{playlistId}/likes   - 좋아요
    # DELETE /api/v1/playlists/{playlistId}/likes - 좋아요 취소
    path('playlists/<int:playlist_id>/likes', PlaylistLikeView.as_view(), name='playlist-like'),
    
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
    
    # ========================
    # 사용자 통계 API
    # ========================
    # 전체 통계 조회
    # GET /api/v1/users/{user_id}/statistics/?period=month|all
    path('users/<int:user_id>/statistics/', UserStatisticsView.as_view(), name='user-statistics'),
    
    # 청취 시간 통계
    # GET /api/v1/users/{user_id}/statistics/listening-time/
    path('users/<int:user_id>/statistics/listening-time/', UserListeningTimeView.as_view(), name='user-listening-time'),
    
    # Top 장르 통계
    # GET /api/v1/users/{user_id}/statistics/genres/?limit=3
    path('users/<int:user_id>/statistics/genres/', UserTopGenresView.as_view(), name='user-top-genres'),
    
    # Top 아티스트 통계
    # GET /api/v1/users/{user_id}/statistics/artists/?limit=3
    path('users/<int:user_id>/statistics/artists/', UserTopArtistsView.as_view(), name='user-top-artists'),
    
    # Top 태그(분위기/키워드) 통계
    # GET /api/v1/users/{user_id}/statistics/tags/?limit=6
    path('users/<int:user_id>/statistics/tags/', UserTopTagsView.as_view(), name='user-top-tags'),
    
    # Top 음악 차트
    # GET /api/v1/users/{user_id}/statistics/tracks/?limit=15
    path('users/<int:user_id>/statistics/tracks/', UserTopTracksView.as_view(), name='user-top-tracks'),
    
    # AI 생성 활동 통계
    # GET /api/v1/users/{user_id}/statistics/ai-generation/
    path('users/<int:user_id>/statistics/ai-generation/', UserAIGenerationView.as_view(), name='user-ai-generation'),
]
