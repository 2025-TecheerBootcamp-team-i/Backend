"""
Suno API 예외 클래스 정의
"""


class SunoAPIError(Exception):
    """Suno API 기본 예외 클래스"""
    pass


class SunoCreditInsufficientError(SunoAPIError):
    """Suno API 크레딧 부족 예외"""
    pass


class SunoAuthenticationError(SunoAPIError):
    """Suno API 인증 실패 예외"""
    pass
