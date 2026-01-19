"""
인증 관련 Views - 회원가입, 로그인
"""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView as BaseTokenRefreshView
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from django.contrib.auth.hashers import check_password
from drf_spectacular.utils import extend_schema
from ..models import Users
from ..serializers import UserRegisterSerializer, UserLoginSerializer


class RegisterView(APIView):
    """
    회원가입 API
    POST /api/v1/auth/users/
    """
    permission_classes = [AllowAny]
    
    @extend_schema(
        summary="회원가입",
        description="""이메일, 비밀번호, 닉네임으로 회원가입

**유효성 검증 규칙:**
- **이메일**: 형식 검증(사용자명@도메인.최상위도메인) + 중복 확인 불가
- **비밀번호**: 8-16자 + 영문자/숫자/특수기호 각 1개 이상 필수
- **비밀번호 확인**: 원본 비밀번호와 정확히 일치해야 함
- **닉네임**: 필수 입력 (2-20자)

**특수기호 허용 목록**: !@#$%^&*()_+-=[]{}|;:',\".<>/?~
""",
        request=UserRegisterSerializer,
        responses={
            201: {
                'description': '회원가입 성공',
                'content': {
                    'application/json': {
                        'example': {
                            'message': '회원가입 성공',
                            'user_id': 1,
                            'email': 'user@example.com',
                            'nickname': '사용자닉네임'
                        }
                    }
                }
            },
            400: {
                'description': '유효성 검증 실패',
                'content': {
                    'application/json': {
                        'examples': {
                            'email_validation': {
                                'value': {'email': ['이메일 형식이 올바르지 않습니다']}
                            },
                            'password_complexity': {
                                'value': {'password': ['문자/숫자/특수기호가 부족해요: 숫자, 특수기호']}
                            },
                            'password_mismatch': {
                                'value': {'password_confirm': ['비밀번호가 일치하지 않습니다']}
                            }
                        }
                    }
                }
            }
        },
        tags=['인증']
    )
    
    def post(self, request):
        """이메일, 비밀번호, 닉네임으로 회원가입"""
        serializer = UserRegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response({
                'message': '회원가입 성공',
                'user_id': user.user_id,
                'email': user.email,
                'nickname': user.nickname
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    """
    로그인 API
    POST /api/v1/auth/tokens/
    이메일/비밀번호 검증 후 JWT 토큰(Access, Refresh) 발급
    """
    permission_classes = [AllowAny]
    
    @extend_schema(
        summary="로그인",
        description="이메일/비밀번호 검증 후 JWT 토큰(Access, Refresh) 발급",
        request=UserLoginSerializer,
        tags=['인증']
    )
    
    def post(self, request):
        """로그인 처리 및 JWT 토큰 발급"""
        serializer = UserLoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        email = serializer.validated_data['email']
        password = serializer.validated_data['password']
        
        # 사용자 조회
        # SoftDeleteManager가 자동으로 is_deleted=False인 레코드만 조회
        try:
            user = Users.objects.get(email=email)
        except Users.DoesNotExist:
            return Response(
                {'error': '이메일 또는 비밀번호가 올바르지 않습니다.'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # 비밀번호 검증
        if not check_password(password, user.password):
            return Response(
                {'error': '이메일 또는 비밀번호가 올바르지 않습니다.'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # JWT 토큰 생성 (Access + Refresh)
        refresh = RefreshToken()
        refresh['user_id'] = user.user_id
        refresh['email'] = user.email
        
        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user_id': user.user_id,
            'email': user.email,
            'nickname': user.nickname
        }, status=status.HTTP_200_OK)


class TokenRefreshView(BaseTokenRefreshView):
    """
    JWT Refresh Token 갱신 API
    
    POST /api/v1/auth/refresh/
    POST /api/music/auth/refresh/
    """
    
    @extend_schema(
        summary="JWT 토큰 갱신",
        description="Refresh Token을 사용하여 새로운 Access Token 발급",
        request=TokenRefreshSerializer,
        tags=['인증']
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)
