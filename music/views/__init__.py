"""
Music 앱의 Views 패키지
모든 View를 한 곳에서 import 할 수 있도록 export
"""

# 공통 유틸리티
from .common import MusicPagination, ErrorTestView, DatabaseQueryTestView

# 인증 관련 Views
from .auth import (
    RegisterView,
    LoginView,
    TokenRefreshView,
)

# 좋아요 관련 Views
from .likes import MusicLikeView

# 검색 관련 Views
from .search import MusicSearchView

# 음악 상세 관련 Views
from .music import MusicDetailView, MusicPlayView

# 아티스트 관련 Views
from .artists import ArtistDetailView, ArtistTracksView, ArtistAlbumsView, AlbumDetailView, PopularArtistsView

# 재생 기록 관련 Views
from .playlogs import PlayLogView, PlayLogCreateView

# 차트 관련 Views
from .charts import ChartView

# 사용자 통계 관련 Views
from .statistics import (
    UserStatisticsView,
    UserListeningTimeView,
    UserTopGenresView,
    UserTopArtistsView,
    UserTopTagsView,
    UserAIGenerationView,
)

# 플레이리스트 관련 Views
from .playlist import (
    PlaylistListCreateView,
    PlaylistDetailView,
    PlaylistItemAddView,
    PlaylistItemDeleteView,
    PlaylistLikeView,
)

# 레거시 함수 기반 Views (웹 페이지 및 음악 생성)
from .legacy import (
    music_generator_page,
    music_list_page,
    music_monitor_page,
    generate_music,
    generate_music_async,
    suno_webhook,
    get_task_status,
    get_suno_task_status,
    list_music,
    get_music_detail,
)

# 외부에서 사용 가능한 모든 클래스 및 함수
__all__ = [
    # common
    'MusicPagination',
    'ErrorTestView',
    'DatabaseQueryTestView',
    # auth
    'RegisterView',
    'LoginView',
    'TokenRefreshView',
    # likes
    'MusicLikeView',
    # search
    'MusicSearchView',
    # music
    'MusicDetailView',
    'MusicPlayView',
    # artists
    'ArtistDetailView',
    'ArtistTracksView',
    'ArtistAlbumsView',
    'AlbumDetailView',
    'PopularArtistsView',
    # playlogs
    'PlayLogView',
    'PlayLogCreateView',
    # charts
    'ChartView',
    # statistics (사용자 통계)
    'UserStatisticsView',
    'UserListeningTimeView',
    'UserTopGenresView',
    'UserTopArtistsView',
    'UserTopTagsView',
    'UserAIGenerationView',
    # playlist
    'PlaylistListCreateView',
    'PlaylistDetailView',
    'PlaylistItemAddView',
    'PlaylistItemDeleteView',
    'PlaylistLikeView',
    # legacy (함수 기반)
    'music_generator_page',
    'music_list_page',
    'music_monitor_page',
    'generate_music',
    'generate_music_async',
    'suno_webhook',
    'get_task_status',
    'get_suno_task_status',
    'list_music',
    'get_music_detail',
]
