"""
Music 앱의 Views 패키지
모든 View를 한 곳에서 import 할 수 있도록 export
"""

# 공통 유틸리티 및 템플릿 뷰
from .common import (
    MusicPagination, 
    ErrorTestView, 
    DatabaseQueryTestView,
    music_generator_page,
    music_list_page,
    music_monitor_page,
)

# 인증 관련 Views
from .auth import (
    RegisterView,
    LoginView,
    TokenRefreshView,
    EmailCheckView,
)

# 좋아요 관련 Views
from .likes import MusicLikeView, UserLikedMusicListView, AlbumLikeView, UserLikedAlbumsView

# 검색 관련 Views
from .search import MusicSearchView, AiMusicSearchView

# 음악 상세 관련 Views
from .music import MusicDetailView, MusicPlayView, MusicTagsView

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
    UserTopTracksView,
    UserAIGenerationView,
)

# 플레이리스트 관련 Views
from .playlist import (
    PlaylistListCreateView,
    PlaylistDetailView,
    PlaylistItemAddView,
    PlaylistItemDeleteView,
    PlaylistLikeView,
    PlaylistLikedView,
)

# AI 음악 생성 Views (리팩토링된 CBV)
from .ai_music import (
    AiMusicGenerateView,
    AiMusicGenerateAsyncView,
    CeleryTaskStatusView,
    MusicListView as AiMusicListView,
    MusicDetailView as AiMusicDetailView,
    UserAiMusicListView,
    SunoTaskStatusView,
    SunoWebhookView,
    ConvertPromptView,
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
    'EmailCheckView',
    # likes
    'MusicLikeView',
    'UserLikedMusicListView',
    'AlbumLikeView',
    'UserLikedAlbumsView',
    # search
    'MusicSearchView',
    'AiMusicSearchView',
    # music
    'MusicDetailView',
    'MusicPlayView',
    'MusicTagsView',
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
    'UserTopTracksView',
    'UserAIGenerationView',
    # playlist
    'PlaylistListCreateView',
    'PlaylistDetailView',
    'PlaylistItemAddView',
    'PlaylistItemDeleteView',
    'PlaylistLikeView',
    'PlaylistLikedView',
    # legacy (함수 기반 - 템플릿 렌더링용)
    'music_generator_page',
    'music_list_page',
    'music_monitor_page',
    # ai_music (리팩토링된 CBV)
    'AiMusicGenerateView',
    'AiMusicGenerateAsyncView',
    'CeleryTaskStatusView',
    'AiMusicListView',
    'AiMusicDetailView',
    'UserAiMusicListView',
    'SunoTaskStatusView',
    'SunoWebhookView',
    'ConvertPromptView',
]
