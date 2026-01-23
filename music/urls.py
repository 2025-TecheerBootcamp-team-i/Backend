"""
Music 앱의 URL 라우팅
"""
from django.urls import path
from . import views
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    RegisterView,
    LoginView,
    EmailCheckView,
    TokenRefreshView,
    MusicLikeView,
    UserLikedMusicListView,
    MusicSearchView,
    AiMusicSearchView,
    MusicDetailView as iTunesMusicDetailView,  # iTunes 기반 상세 조회 (기존)
    ArtistDetailView,
    ArtistTracksView,
    ArtistAlbumsView,
    AlbumDetailView,
    PopularArtistsView,
    ErrorTestView,
    DatabaseQueryTestView,
    PlayLogView,
    MusicPlayLogsView,
    ChartView,
    # 사용자 통계
    UserStatisticsView,
    UserListeningTimeView,
    UserTopGenresView,
    UserTopArtistsView,
    UserTopTagsView,
    UserTopTracksView,
    UserAIGenerationView,
    UserAiMusicListView,
    # 플레이리스트
    PlaylistListCreateView,
    PlaylistDetailView,
    PlaylistItemAddView,
    PlaylistItemDeleteView,
    PlaylistLikeView,
)

# AI 음악 생성 (리팩토링된 CBV)
from .views.ai_music import (
    AiMusicGenerateView,
    AiMusicGenerateAsyncView,
    CeleryTaskStatusView,
    MusicListView as AiMusicListView,
    MusicDetailView as AiMusicDetailView,
    SunoTaskStatusView,
    SunoWebhookView,
    ConvertPromptView,
)

app_name = 'music'

urlpatterns = [
    
    # API 엔드포인트

    # 인증 관련
    path('auth/users/', RegisterView.as_view(), name='register'),
    path('auth/tokens/', LoginView.as_view(), name='login'),
    path('auth/check-email/', EmailCheckView.as_view(), name='email_check'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # 테스트용 엔드포인트
    # GET /api/v1/test/error?code=500&rate=0.5  # 에러율 테스트
    path('test/error', ErrorTestView.as_view(), name='error-test'),
    # GET /api/v1/test/db?count=10  # Database Queries 테스트
    path('test/db', DatabaseQueryTestView.as_view(), name='db-test'),
    
    # iTunes 기반 검색 (새로운 메인 검색)
    # GET /api/v1/search?q={검색어}&exclude_ai={true|false}
    path('search', MusicSearchView.as_view(), name='itunes-search'),
    
    # AI 음악 검색 (AI 음악 전용)
    # GET /api/music/search-ai/?q={검색어}
    path('search-ai/', AiMusicSearchView.as_view(), name='ai-music-search'),
    
    # iTunes ID 기반 상세 조회 (DB에 없으면 자동 저장)
    # GET /api/v1/tracks/{itunes_id}
    path('tracks/<int:itunes_id>', iTunesMusicDetailView.as_view(), name='track-detail'),
    
    # 음악 재생 정보 조회 및 재생 로그 기록
    # GET /api/v1/tracks/{music_id}/play - 재생 정보 조회 (로그 저장 안 함)
    # POST /api/v1/tracks/{music_id}/play - 재생 로그 기록
    path('tracks/<int:music_id>/play', PlayLogView.as_view(), name='music-play'),
    
    # 음악별 재생 로그 목록 조회
    # GET /api/v1/playlogs/{music_id}/ - 특정 음악의 재생 로그 조회
    path('playlogs/<int:music_id>/', MusicPlayLogsView.as_view(), name='music-playlogs'),

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
    
    # 좋아요 등록/취소 (POST, DELETE만 지원)
    # POST /api/v1/tracks/{music_id}/like
    # DELETE /api/v1/tracks/{music_id}/like
    path('tracks/<int:music_id>/like', MusicLikeView.as_view(), name='music-like'),
    
    # 사용자가 좋아요한 곡 목록 조회 (GET만 지원)
    # GET /api/v1/users/{user_id}/likes
    path('users/<int:user_id>/likes', UserLikedMusicListView.as_view(), name='user-liked-music-list'),
    
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
    
    # ========================
    # AI 음악 생성 API (리팩토링된 CBV)
    # ========================
    # 프롬프트 변환
    # POST /api/v1/music/convert-prompt/
    path('convert-prompt/', ConvertPromptView.as_view(), name='convert_prompt'),
    
    # 음악 생성 (동기) - 완료까지 대기
    # POST /api/v1/music/generate/
    path('generate/', AiMusicGenerateView.as_view(), name='ai_music_generate'),
    
    # 음악 생성 (비동기) - Celery Task ID 반환
    # POST /api/v1/music/generate-async/
    path('generate-async/', AiMusicGenerateAsyncView.as_view(), name='ai_music_generate_async'),
    
    # Celery 작업 상태 조회
    # GET /api/v1/music/task/{task_id}/
    path('task/<str:task_id>/', CeleryTaskStatusView.as_view(), name='celery_task_status'),
    
    # Suno API 작업 상태 조회 (Polling용)
    # GET /api/v1/music/suno-task/{task_id}/
    path('suno-task/<str:task_id>/', SunoTaskStatusView.as_view(), name='suno_task_status'),
    
    # Suno API 웹훅 (음악 생성 완료 콜백)
    # POST /api/v1/music/webhook/suno/
    path('webhook/suno/', SunoWebhookView.as_view(), name='suno_webhook'),
    
    # AI 음악 목록 조회 (is_ai, user_id 필터링 지원)
    # GET /api/v1/music/?is_ai=true&user_id=1
    path('', AiMusicListView.as_view(), name='ai_music_list'),
    
    # AI 음악 상세 조회 (music_id 기반)
    # GET /api/v1/music/{music_id}/
    path('<int:music_id>/', AiMusicDetailView.as_view(), name='ai_music_detail'),
    
    # 웹 페이지 (UI) - 기존 템플릿 유지
    path('generator/', views.music_generator_page, name='music_generator_page'),
    path('list/', views.music_list_page, name='music_list_page'),
    path('monitor/<int:music_id>/', views.music_monitor_page, name='music_monitor_page'),
    
    # ========================
    # 사용자 통계 API
    # ========================
    # 사용자가 생성한 AI 음악 목록 조회
    # GET /api/v1/users/{user_id}/ai-music/
    path('users/<int:user_id>/ai-music/', UserAiMusicListView.as_view(), name='user-ai-music-list'),
    
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
