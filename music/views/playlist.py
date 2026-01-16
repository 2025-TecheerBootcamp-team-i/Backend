"""
플레이리스트 관련 Views - 플레이리스트 CRUD, 곡 관리, 좋아요
"""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.shortcuts import get_object_or_404
from django.db.models import Q
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
        # 기본 쿼리: 삭제되지 않은 플레이리스트
        queryset = Playlists.objects.filter(is_deleted=False)
        
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
        
        serializer = PlaylistSerializer(queryset, many=True)
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
            playlist = serializer.save(user=request.user, is_deleted=False)
            
            # 생성된 플레이리스트 상세 정보 반환
            detail_serializer = PlaylistDetailSerializer(playlist, context={'request': request})
            return Response(detail_serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


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
        playlist = get_object_or_404(Playlists, playlist_id=playlist_id, is_deleted=False)
        
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
        playlist = get_object_or_404(Playlists, playlist_id=playlist_id, is_deleted=False)
        
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
        playlist = get_object_or_404(Playlists, playlist_id=playlist_id, is_deleted=False)
        
        # 권한 확인: 자신의 플레이리스트만 삭제 가능
        if playlist.user != request.user:
            return Response(
                {'error': '자신의 플레이리스트만 삭제할 수 있습니다.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # 소프트 삭제
        playlist.is_deleted = True
        playlist.save()
        
        return Response(
            {'message': '플레이리스트가 삭제되었습니다.'},
            status=status.HTTP_200_OK
        )


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
        playlist = get_object_or_404(Playlists, playlist_id=playlist_id, is_deleted=False)
        
        # 권한 확인: 자신의 플레이리스트에만 곡 추가 가능
        if playlist.user != request.user:
            return Response(
                {'error': '자신의 플레이리스트에만 곡을 추가할 수 있습니다.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = PlaylistItemAddSerializer(data=request.data)
        
        if serializer.is_valid():
            music_id = serializer.validated_data['music_id']
            music = get_object_or_404(Music, music_id=music_id, is_deleted=False)
            
            # 이미 추가된 곡인지 확인
            existing_item = PlaylistItems.objects.filter(
                playlist=playlist,
                music=music,
                is_deleted=False
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
                last_item = PlaylistItems.objects.filter(
                    playlist=playlist,
                    is_deleted=False
                ).order_by('-order').first()
                
                order = (last_item.order + 1) if last_item else 1
            
            # 곡 추가
            item = PlaylistItems.objects.create(
                playlist=playlist,
                music=music,
                order=order,
                is_deleted=False
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
        item = get_object_or_404(PlaylistItems, item_id=item_id, is_deleted=False)
        
        # 권한 확인: 자신의 플레이리스트에서만 곡 삭제 가능
        if item.playlist.user != request.user:
            return Response(
                {'error': '자신의 플레이리스트에서만 곡을 삭제할 수 있습니다.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # 소프트 삭제
        item.is_deleted = True
        item.save()
        
        return Response(
            {'message': '플레이리스트에서 곡이 삭제되었습니다.'},
            status=status.HTTP_200_OK
        )


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
        # 플레이리스트 존재 확인
        playlist = get_object_or_404(Playlists, playlist_id=playlist_id, is_deleted=False)
        
        # 공개 플레이리스트만 좋아요 가능 (선택적, 요구사항에 따라 변경 가능)
        if playlist.visibility == 'private' and playlist.user != request.user:
            return Response(
                {'error': '비공개 플레이리스트에는 좋아요를 할 수 없습니다.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # 이미 좋아요가 있는지 확인
        like, created = PlaylistLikes.objects.get_or_create(
            user=request.user,
            playlist=playlist,
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
                    'message': '이미 좋아요를 누른 플레이리스트입니다.',
                    'playlist_id': playlist_id,
                    'is_liked': True
                },
                status=status.HTTP_200_OK
            )
        
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
        # 플레이리스트 존재 확인
        playlist = get_object_or_404(Playlists, playlist_id=playlist_id, is_deleted=False)
        
        # 좋아요 찾기
        try:
            like = PlaylistLikes.objects.get(
                user=request.user,
                playlist=playlist,
                is_deleted=False
            )
            like.is_deleted = True
            like.save()
            
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
