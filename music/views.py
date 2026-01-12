"""
Music 앱의 View 모듈
음악 관련 API 엔드포인트를 처리합니다.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
=======
인증 관련 View
회원가입, 로그인, JWT 토큰 발급 처리
"""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.hashers import check_password
from .models import Users, Music, MusicLikes, MusicTags, Tags
from .serializers import (
    MusicListSerializer, 
    MusicDetailSerializer, 
    MusicLikeSerializer,
    UserRegisterSerializer,
    UserLoginSerializer
)


class MusicPagination(PageNumberPagination):
    """음악 목록 페이지네이션"""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class MusicViewSet(viewsets.ReadOnlyModelViewSet):
    """
    음악 목록 및 상세 조회 ViewSet
    
    - list: 음악 목록 조회 (검색, 필터링 지원)
    - retrieve: 음악 상세 조회
    """
    pagination_class = MusicPagination
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        """
        QuerySet 생성 (is_deleted=False만 조회)
        검색 및 필터링 지원
        """
        queryset = Music.objects.filter(is_deleted=False).select_related(
            'artist', 'album'
        ).order_by('-created_at')
        
        # 검색 (음악명, 아티스트명)
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(music_name__icontains=search) |
                Q(artist__artist_name__icontains=search)
            )
        
        # 장르 필터링
        genre = self.request.query_params.get('genre')
        if genre:
            queryset = queryset.filter(genre__iexact=genre)
        
        # AI 생성곡 필터링
        is_ai = self.request.query_params.get('is_ai')
        if is_ai is not None:
            is_ai_bool = is_ai.lower() in ['true', '1', 'yes']
            queryset = queryset.filter(is_ai=is_ai_bool)
        
        return queryset
    
    def get_serializer_class(self):
        """액션에 따라 다른 Serializer 사용"""
        if self.action == 'retrieve':
            return MusicDetailSerializer
        return MusicListSerializer
    
    def list(self, request, *args, **kwargs):
        """
        음악 목록 조회
        GET /api/v1/db/tracks
        """
        return super().list(request, *args, **kwargs)
    
    def retrieve(self, request, *args, **kwargs):
        """
        음악 상세 조회
        GET /api/v1/db/tracks/{musicId}
        """
        return super().retrieve(request, *args, **kwargs)


class MusicLikeView(APIView):
    """
    음악 좋아요 등록/취소 API
    
    - POST: 좋아요 등록
    - DELETE: 좋아요 취소
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, music_id):
        """
        좋아요 등록
        POST /api/v1/tracks/{musicId}/likes
        """
        # 음악 존재 확인
        music = get_object_or_404(Music, music_id=music_id, is_deleted=False)
        
        # 이미 좋아요가 있는지 확인
        like, created = MusicLikes.objects.get_or_create(
            user=request.user,
            music=music,
            defaults={'is_deleted': False}
        )
        
        if not created and like.is_deleted:
            # 삭제된 좋아요를 복구
            like.is_deleted = False
            like.save()
            created = True
        elif not created:
            # 이미 좋아요가 있음
            return Response(
                {
                    'message': '이미 좋아요를 누른 음악입니다.',
                    'music_id': music_id,
                    'is_liked': True
                },
                status=status.HTTP_200_OK
            )
        
        serializer = MusicLikeSerializer({
            'message': '좋아요가 등록되었습니다.',
            'music_id': music_id,
            'is_liked': True
        })
        
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    def delete(self, request, music_id):
        """
        좋아요 취소
        DELETE /api/v1/tracks/{musicId}/likes
        """
        # 음악 존재 확인
        music = get_object_or_404(Music, music_id=music_id, is_deleted=False)
        
        # 좋아요 찾기
        try:
            like = MusicLikes.objects.get(
                user=request.user,
                music=music,
                is_deleted=False
            )
            like.is_deleted = True
            like.save()
            
            serializer = MusicLikeSerializer({
                'message': '좋아요가 취소되었습니다.',
                'music_id': music_id,
                'is_liked': False
            })
            
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except MusicLikes.DoesNotExist:
            return Response(
                {
                    'message': '좋아요를 누르지 않은 음악입니다.',
                    'music_id': music_id,
                    'is_liked': False
                },
                status=status.HTTP_404_NOT_FOUND
            )


class MusicTagSearchView(APIView):
    """
    태그 기반 음악 검색 API
    GET /api/v1/tracks/search/tags
    """
    permission_classes = [AllowAny]
    pagination_class = MusicPagination
    
    def get(self, request):
        """
        태그로 음악 검색
        Query: tags=신나는,밝은
        """
        tags_param = request.query_params.get('tags')
        
        if not tags_param:
            return Response(
                {'error': 'tags 파라미터가 필요합니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 쉼표로 구분된 태그 파싱
        tag_keys = [tag.strip() for tag in tags_param.split(',') if tag.strip()]
        
        if not tag_keys:
            return Response(
                {'error': '유효한 태그를 입력해주세요.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 태그에 해당하는 음악 찾기
        tags = Tags.objects.filter(
            tag_key__in=tag_keys,
            is_deleted=False
        )
        
        music_ids = MusicTags.objects.filter(
            tag__in=tags,
            is_deleted=False
        ).values_list('music_id', flat=True).distinct()
        
        musics = Music.objects.filter(
            music_id__in=music_ids,
            is_deleted=False
        ).select_related('artist', 'album').order_by('-created_at')
        
        # 페이지네이션
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(musics, request)
        
        if page is not None:
            serializer = MusicListSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
        
        serializer = MusicListSerializer(musics, many=True)
        return Response({
            'count': musics.count(),
            'results': serializer.data
        })


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
