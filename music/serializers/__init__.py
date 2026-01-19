"""
Music 앱의 Serializers 패키지
모든 Serializer를 한 곳에서 import 할 수 있도록 export
"""

# 기본 Serializers
from .base import (
    ArtistSerializer,
    AlbumSerializer,
    AlbumDetailSerializer,
    TagSerializer,
    AiInfoSerializer,
)

# 음악 관련 Serializers
from .music import (
    MusicDetailSerializer,
    MusicLikeSerializer,
    MusicPlaySerializer,
)

# 검색 관련 Serializers
from .search import (
    iTunesSearchResultSerializer,
)

# 인증 관련 Serializers
from .auth import (
    UserRegisterSerializer,
    UserLoginSerializer,
)

# 사용자 통계 Serializers
from .statistics import (
    ListeningTimeSerializer,
    GenreStatSerializer,
    ArtistStatSerializer,
    TagStatSerializer,
    AIGenerationStatSerializer,
    UserStatisticsSerializer,
)

# 플레이리스트 관련 Serializers
from .playlist import (
    PlaylistSerializer,
    PlaylistDetailSerializer,
    PlaylistCreateSerializer,
    PlaylistUpdateSerializer,
    PlaylistItemSerializer,
    PlaylistItemAddSerializer,
    PlaylistLikeSerializer,
)

# 차트 관련 Serializers
from .charts import (
    PlayLogCreateSerializer,
    PlayLogResponseSerializer,
    ChartMusicSerializer,
    ChartItemSerializer,
    ChartResponseSerializer,
)

# 외부에서 사용 가능한 모든 클래스
__all__ = [
    # base
    'ArtistSerializer',
    'AlbumSerializer',
    'AlbumDetailSerializer',
    'TagSerializer',
    'AiInfoSerializer',
    # music
    'MusicDetailSerializer',
    'MusicLikeSerializer',
    'MusicPlaySerializer',
    # search
    'iTunesSearchResultSerializer',
    # auth
    'UserRegisterSerializer',
    'UserLoginSerializer',
    # statistics (사용자 통계)
    'ListeningTimeSerializer',
    'GenreStatSerializer',
    'ArtistStatSerializer',
    'TagStatSerializer',
    'AIGenerationStatSerializer',
    'UserStatisticsSerializer',
    # playlist
    'PlaylistSerializer',
    'PlaylistDetailSerializer',
    'PlaylistCreateSerializer',
    'PlaylistUpdateSerializer',
    'PlaylistItemSerializer',
    'PlaylistItemAddSerializer',
    'PlaylistLikeSerializer',
    # charts
    'PlayLogCreateSerializer',
    'PlayLogResponseSerializer',
    'ChartMusicSerializer',
    'ChartItemSerializer',
    'ChartResponseSerializer',
]
