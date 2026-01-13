"""
공통 유틸리티 - 페이지네이션 등
"""
from rest_framework.pagination import PageNumberPagination


class MusicPagination(PageNumberPagination):
    """음악 목록 페이지네이션"""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100
