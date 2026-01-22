"""
플레이리스트 관련 Views - 플레이리스트 CRUD, 곡 관리, 좋아요
"""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.shortcuts import get_object_or_404
from django.db.models import Q
from drf_spectacular.utils import extend_schema
from ..models import Playlists, PlaylistItems, PlaylistLikes, Music, Users
from ..serializers.playlist import (
    PlaylistSerializer,
    PlaylistDetailSerializer,
    PlaylistCreateSerializer,
    PlaylistUpdateSerializer,
    PlaylistItemSerializer,
    PlaylistItemAddSerializer,
    PlaylistLikeSerializer,
)


# 헬퍼 함수는 제거하고 request.user를 직접 사용합니다 (likes.py와 동일한 방식)


@extend_schema(tags=['플레이리스트'])
class PlaylistListCreateView(APIView):
    """
    플레이리스트 목록 조회 & 생성 API
    
    - GET: 플레이리스트 목록 조회 (자신의 플레이리스트 + 공개 플레이리스트)
    - POST: 플레이리스트 생성
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """
        플레이리스트 목록 조회
        GET /api/v1/playlists
        
        Query Parameters:
        - visibility: public/private (선택)
        - user_id: 특정 사용자의 플레이리스트만 조회 (선택)
        """
        # SoftDeleteManager가 자동으로 is_deleted=False인 레코드만 조회
        queryset = Playlists.objects.all()
        # 공개 범위 필터링
        visibility = request.query_params.get('visibility')
        if visibility:
            queryset = queryset.filter(visibility=visibility)
        
        # 특정 사용자 필터링
        user_id = request.query_params.get('user_id')
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        else:
            # 자신의 플레이리스트 또는 공개 플레이리스트만 조회
            queryset = queryset.filter(
                Q(user=request.user) | Q(visibility='public')
            )
        
        # 최신순 정렬
        queryset = queryset.order_by('-created_at')
        
        serializer = PlaylistSerializer(queryset, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def post(self, request):
        """
        플레이리스트 생성
        POST /api/v1/playlists
        
        Request Body:
        {
            "title": "플레이리스트 제목",
            "visibility": "public" or "private"
        }
        """
        serializer = PlaylistCreateSerializer(data=request.data)
        
        if serializer.is_valid():
            # TrackableMixin이 자동으로 is_deleted=False, created_at, updated_at 설정
            playlist = serializer.save(user=request.user)
            
            # 생성된 플레이리스트 상세 정보 반환
            detail_serializer = PlaylistDetailSerializer(playlist, context={'request': request})
            return Response(detail_serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
@extend_schema(tags=['플레이리스트'])
class PlaylistLikedView(APIView):
    """
    좋아요한 플레이리스트 목록 조회 API

    - GET: 좋아요한 플레이리스트 목록 조회
    """
    permission_classes = [AllowAny]  # IsAuthenticated에서 AllowAny로 변경 (앨범 API와 일관성)

    def get(self, request):
        """
        좋아요한 플레이리스트 목록 조회
        GET /api/v1/playlists/likes
        
        시스템 플레이리스트는 제외하고 반환합니다.
        """
        try:
            # 인증 확인 (테스트용: 인증 없으면 userId 1 사용)
            if not request.user or not request.user.is_authenticated:
                # 테스트용: userId 1 사용
                user = get_object_or_404(Users, user_id=1)
            else:
                user = request.user
            
            # SoftDeleteManager가 자동으로 is_deleted=False인 레코드만 조회
            liked_playlist_ids = PlaylistLikes.objects.filter(
                user=user
            ).values_list('playlist_id', flat=True)

            # 좋아요한 플레이리스트들 조회 (SoftDeleteManager 자동 적용)
            # 시스템 플레이리스트 제외
            queryset = Playlists.objects.filter(
                playlist_id__in=liked_playlist_ids
            ).exclude(
                visibility='system'
            ).order_by('-created_at')

            serializer = PlaylistSerializer(queryset, many=True, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Exception as e:
            # 에러 로깅
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"좋아요한 플레이리스트 조회 실패: {str(e)}", exc_info=True)
            
            return Response(
                {
                    'error': '좋아요한 플레이리스트 조회 중 오류가 발생했습니다.',
                    'detail': str(e)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

@extend_schema(tags=['플레이리스트'])
class PlaylistDetailView(APIView):
    """
    플레이리스트 상세 조회, 수정, 삭제 API
    
    - GET: 플레이리스트 상세 정보 조회 (곡 목록 포함)
    - PATCH: 플레이리스트 정보 수정
    - DELETE: 플레이리스트 삭제 (소프트 삭제)
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request, playlist_id):
        """
        플레이리스트 상세 조회
        GET /api/v1/playlists/{playlistId}
        """
        # SoftDeleteManager가 자동으로 is_deleted=False인 레코드만 조회
        playlist = get_object_or_404(Playlists, playlist_id=playlist_id)
        
        # 권한 확인: 자신의 플레이리스트이거나 공개 플레이리스트만 조회 가능
        if playlist.visibility == 'private' and playlist.user != request.user:
            return Response(
                {'error': '비공개 플레이리스트는 조회할 수 없습니다.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = PlaylistDetailSerializer(playlist, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def patch(self, request, playlist_id):
        """
        플레이리스트 수정
        PATCH /api/v1/playlists/{playlistId}
        
        Request Body:
        {
            "title": "새로운 제목" (선택),
            "visibility": "public" or "private" (선택)
        }
        """
        # SoftDeleteManager가 자동으로 is_deleted=False인 레코드만 조회
        playlist = get_object_or_404(Playlists, playlist_id=playlist_id)
        
        # 시스템 플레이리스트는 수정 불가
        if playlist.visibility == 'system':
            return Response(
                {'error': '시스템 플레이리스트는 수정할 수 없습니다.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # 권한 확인: 자신의 플레이리스트만 수정 가능
        if playlist.user != request.user:
            return Response(
                {'error': '자신의 플레이리스트만 수정할 수 있습니다.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = PlaylistUpdateSerializer(playlist, data=request.data, partial=True)
        
        if serializer.is_valid():
            serializer.save()
            
            # 수정된 플레이리스트 상세 정보 반환
            detail_serializer = PlaylistDetailSerializer(playlist, context={'request': request})
            return Response(detail_serializer.data, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, playlist_id):
        """
        플레이리스트 삭제
        DELETE /api/v1/playlists/{playlistId}
        """
        # SoftDeleteManager가 자동으로 is_deleted=False인 레코드만 조회
        playlist = get_object_or_404(Playlists, playlist_id=playlist_id)
        
        # 시스템 플레이리스트는 삭제 불가
        if playlist.visibility == 'system':
            return Response(
                {'error': '시스템 플레이리스트는 삭제할 수 없습니다.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # 권한 확인: 자신의 플레이리스트만 삭제 가능
        if playlist.user != request.user:
            return Response(
                {'error': '자신의 플레이리스트만 삭제할 수 있습니다.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # TrackableMixin의 delete() 메서드가 자동으로 Soft Delete 수행
        playlist.delete()
        
        return Response(
            {
                'message': '플레이리스트가 삭제되었습니다.',
                'playlist_id': playlist_id  # 삭제된 ID 추가
            },
            status=status.HTTP_200_OK
        )

@extend_schema(tags=['플레이리스트'])
class PlaylistItemAddView(APIView):
    """
    플레이리스트 곡 추가 API
    
    - POST: 플레이리스트에 곡 추가
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, playlist_id):
        """
        플레이리스트에 곡 추가
        POST /api/v1/playlists/{playlistId}/items
        
        Request Body:
        {
            "music_id": 123,
            "order": 1 (선택, 미지정 시 자동으로 마지막 순서)
        }
        """
        # SoftDeleteManager가 자동으로 is_deleted=False인 레코드만 조회
        playlist = get_object_or_404(Playlists, playlist_id=playlist_id)
        
        # 권한 확인: 자신의 플레이리스트에만 곡 추가 가능
        if playlist.user != request.user:
            return Response(
                {'error': '자신의 플레이리스트에만 곡을 추가할 수 있습니다.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = PlaylistItemAddSerializer(data=request.data)
        
        if serializer.is_valid():
            music_id = serializer.validated_data['music_id']
            # SoftDeleteManager가 자동으로 is_deleted=False인 레코드만 조회
            music = get_object_or_404(Music, music_id=music_id)
            
            # 이미 추가된 곡인지 확인
            # SoftDeleteManager가 자동으로 is_deleted=False인 레코드만 조회
            existing_item = PlaylistItems.objects.filter(
                playlist=playlist,
                music=music
            ).first()
            
            if existing_item:
                return Response(
                    {'error': '이미 플레이리스트에 추가된 곡입니다.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # order 값 설정
            order = serializer.validated_data.get('order')
            if order is None:
                # order 미지정 시 마지막 순서로 추가
                # SoftDeleteManager가 자동으로 is_deleted=False인 레코드만 조회
                last_item = PlaylistItems.objects.filter(
                    playlist=playlist
                ).order_by('-order').first()
                
                order = (last_item.order + 1) if last_item else 1
            
            # 곡 추가 (TrackableMixin이 자동으로 필드 설정)
            item = PlaylistItems.objects.create(
                playlist=playlist,
                music=music,
                order=order
            )
            
            item_serializer = PlaylistItemSerializer(item)
            return Response(
                {
                    'message': '플레이리스트에 곡이 추가되었습니다.',
                    'item': item_serializer.data
                },
                status=status.HTTP_201_CREATED
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(tags=['플레이리스트'])
class PlaylistItemDeleteView(APIView):
    """
    플레이리스트 곡 삭제 API
    
    - DELETE: 플레이리스트에서 곡 삭제
    """
    permission_classes = [IsAuthenticated]
    
    def delete(self, request, item_id):
        """
        플레이리스트에서 곡 삭제
        DELETE /api/v1/playlists/items/{itemsId}
        """
        # SoftDeleteManager가 자동으로 is_deleted=False인 레코드만 조회
        item = get_object_or_404(PlaylistItems, item_id=item_id)
        
        # 권한 확인: 자신의 플레이리스트에서만 곡 삭제 가능
        if item.playlist.user != request.user:
            return Response(
                {'error': '자신의 플레이리스트에서만 곡을 삭제할 수 있습니다.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # TrackableMixin의 delete() 메서드가 자동으로 Soft Delete 수행
        item.delete()
        
        return Response(
            {'message': '플레이리스트에서 곡이 삭제되었습니다.'},
            status=status.HTTP_200_OK
        )


@extend_schema(tags=['플레이리스트'])
class PlaylistLikeView(APIView):
    """
    플레이리스트 좋아요 등록/취소 API
    
    - POST: 좋아요 등록
    - DELETE: 좋아요 취소
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, playlist_id):
        """
        플레이리스트 좋아요 등록
        POST /api/v1/playlists/{playlistId}/likes
        """
        # 플레이리스트 존재 확인 (SoftDeleteManager가 자동으로 is_deleted=False인 레코드만 조회)
        playlist = get_object_or_404(Playlists, playlist_id=playlist_id)
        
        # 시스템 플레이리스트에는 좋아요 불가
        if playlist.visibility == 'system':
            return Response(
                {'error': '시스템 플레이리스트에는 좋아요를 할 수 없습니다.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # 자신의 플레이리스트에는 좋아요 불가
        if playlist.user == request.user:
            return Response(
                {'error': '자신의 플레이리스트에는 좋아요를 할 수 없습니다.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # 공개 플레이리스트만 좋아요 가능 (선택적, 요구사항에 따라 변경 가능)
        if playlist.visibility == 'private' and playlist.user != request.user:
            return Response(
                {'error': '비공개 플레이리스트에는 좋아요를 할 수 없습니다.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # 이미 좋아요가 있는지 확인 (삭제된 것도 포함)
        like = PlaylistLikes.all_objects.filter(user=request.user, playlist=playlist).first()
        
        if like:
            if like.is_deleted:
                # 삭제된 좋아요를 복구
                like.restore()
            else:
                # 이미 활성화된 좋아요가 있음
                return Response(
                    {
                        'message': '이미 좋아요를 누른 플레이리스트입니다.',
                        'playlist_id': playlist_id,
                        'is_liked': True
                    },
                    status=status.HTTP_200_OK
                )
        else:
            # 새로운 좋아요 생성
            like = PlaylistLikes.objects.create(user=request.user, playlist=playlist)
        
        serializer = PlaylistLikeSerializer({
            'message': '좋아요가 등록되었습니다.',
            'playlist_id': playlist_id,
            'is_liked': True
        })
        
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    def delete(self, request, playlist_id):
        """
        플레이리스트 좋아요 취소
        DELETE /api/v1/playlists/{playlistId}/likes
        """
        # 플레이리스트 존재 확인 (SoftDeleteManager가 자동으로 is_deleted=False인 레코드만 조회)
        playlist = get_object_or_404(Playlists, playlist_id=playlist_id)
        
        # 좋아요 찾기 (SoftDeleteManager가 자동으로 is_deleted=False인 레코드만 조회)
        try:
            like = PlaylistLikes.objects.get(user=request.user, playlist=playlist)
            # TrackableMixin의 delete() 메서드가 자동으로 Soft Delete 수행
            like.delete()
            
            serializer = PlaylistLikeSerializer({
                'message': '좋아요가 취소되었습니다.',
                'playlist_id': playlist_id,
                'is_liked': False
            })
            
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except PlaylistLikes.DoesNotExist:
            return Response(
                {
                    'message': '좋아요를 누르지 않은 플레이리스트입니다.',
                    'playlist_id': playlist_id,
                    'is_liked': False
                },
                status=status.HTTP_404_NOT_FOUND
            )
