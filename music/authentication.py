"""
커스텀 JWT 인증 백엔드
Users 모델과 연동하여 JWT 토큰 검증
"""
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, AuthenticationFailed
from .models import Users


class CustomJWTAuthentication(JWTAuthentication):
    """
    커스텀 JWT 인증 백엔드
    
    simplejwt의 기본 인증은 Django의 AUTH_USER_MODEL을 사용하지만,
    이 프로젝트는 별도의 Users 모델을 사용하므로 커스텀 인증이 필요합니다.
    """
    
    def get_user(self, validated_token):
        """
        JWT 토큰에서 user_id를 추출하여 Users 모델에서 사용자 조회
        
        Args:
            validated_token: 검증된 JWT 토큰
            
        Returns:
            Users: 사용자 인스턴스 (is_authenticated 속성 추가)
            
        Raises:
            AuthenticationFailed: 사용자를 찾을 수 없거나 삭제된 경우
        """
        try:
            user_id = validated_token.get('user_id')
            if not user_id:
                raise InvalidToken('토큰에 user_id가 없습니다.')
            
            # Users 모델에서 사용자 조회
            user = Users.objects.get(user_id=user_id, is_deleted=False)
            
            # Django REST Framework의 IsAuthenticated 권한을 위한 속성 추가
            # Users 모델은 Django의 기본 User 모델이 아니므로 is_authenticated 속성이 없음
            user.is_authenticated = True
            user.is_active = not user.is_deleted  # is_active 속성도 추가
            
            return user
            
        except Users.DoesNotExist:
            raise AuthenticationFailed('사용자를 찾을 수 없습니다.')
        except Exception as e:
            raise AuthenticationFailed(f'인증 실패: {str(e)}')
