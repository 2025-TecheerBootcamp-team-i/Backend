"""
Music 앱의 Serializers 패키지
모든 Serializer를 한 곳에서 import 할 수 있도록 export
"""

# 기본 Serializers
from .base import (
    ArtistSerializer,
    AlbumSerializer,
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

# 외부에서 사용 가능한 모든 클래스
__all__ = [
    # base
    'ArtistSerializer',
    'AlbumSerializer',
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
]
