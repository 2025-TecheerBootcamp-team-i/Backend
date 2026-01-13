"""
Music 앱의 Views 패키지
모든 View를 한 곳에서 import 할 수 있도록 export
"""

# 공통 유틸리티
from .common import MusicPagination

# 인증 관련 Views
from .auth import (
    RegisterView,
    LoginView,
)

# 좋아요 관련 Views
from .likes import MusicLikeView

# 검색 관련 Views
from .search import MusicSearchView

# 음악 상세 관련 Views
from .music import MusicDetailView

# 외부에서 사용 가능한 모든 클래스
__all__ = [
    # common
    'MusicPagination',
    # auth
    'RegisterView',
    'LoginView',
    # likes
    'MusicLikeView',
    # search
    'MusicSearchView',
    # music
    'MusicDetailView',
]
