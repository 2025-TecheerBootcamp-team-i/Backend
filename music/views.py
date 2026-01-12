"""
인증 관련 View
회원가입, 로그인, JWT 토큰 발급 처리
"""
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.hashers import check_password
from .models import Users
from .serializers import UserRegisterSerializer, UserLoginSerializer


class RegisterView(APIView):
    """
    회원가입 API
    POST /api/v1/auth/users/
    """
    permission_classes = [AllowAny]
    
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
    
    def post(self, request):
        """로그인 처리 및 JWT 토큰 발급"""
        serializer = UserLoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        email = serializer.validated_data['email']
        password = serializer.validated_data['password']
        
        # 사용자 조회 (삭제되지 않은 사용자만)
        try:
            user = Users.objects.get(email=email, is_deleted=False)
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