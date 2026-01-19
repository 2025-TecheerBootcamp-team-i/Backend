"""
좋아요 관련 Views - 음악 좋아요 등록/취소
"""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from ..models import Music, MusicLikes
from ..serializers import MusicLikeSerializer


class MusicLikeView(APIView):
    """
    음악 좋아요 등록/취소 API
    
    - POST: 좋아요 등록
    - DELETE: 좋아요 취소
    """
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="좋아요 등록",
        description="음악에 좋아요 등록",
        tags=['좋아요']
    )
    
    def post(self, request, music_id):
        """
        좋아요 등록
        POST /api/v1/tracks/{musicId}/likes
        """
        # 음악 존재 확인 (SoftDeleteManager가 자동으로 is_deleted=False인 레코드만 조회)
        music = get_object_or_404(Music, music_id=music_id)
        
        # 이미 좋아요가 있는지 확인
        # SoftDeleteManager를 사용하므로 all_objects로 삭제된 것도 확인
        like = MusicLikes.all_objects.filter(user=request.user, music=music).first()
        
        if like:
            if like.is_deleted:
                # 삭제된 좋아요를 복구
                like.restore()
            else:
                # 이미 활성화된 좋아요가 있음
                return Response(
                    {
                        'message': '이미 좋아요를 누른 음악입니다.',
                        'music_id': music_id,
                        'is_liked': True
                    },
                    status=status.HTTP_200_OK
                )
        else:
            # 새로운 좋아요 생성
            like = MusicLikes.objects.create(user=request.user, music=music)
        
        serializer = MusicLikeSerializer({
            'message': '좋아요가 등록되었습니다.',
            'music_id': music_id,
            'is_liked': True
        })
        
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @extend_schema(
        summary="좋아요 취소",
        description="음악 좋아요 취소",
        tags=['좋아요']
    )
    def delete(self, request, music_id):
        """
        좋아요 취소
        DELETE /api/v1/tracks/{musicId}/likes
        """
        # 음악 존재 확인 (SoftDeleteManager가 자동으로 is_deleted=False인 레코드만 조회)
        music = get_object_or_404(Music, music_id=music_id)
        
        # 좋아요 찾기 (SoftDeleteManager가 자동으로 is_deleted=False인 레코드만 조회)
        try:
            like = MusicLikes.objects.get(user=request.user, music=music)
            # TrackableMixin의 delete() 메서드가 자동으로 Soft Delete 수행
            like.delete()
            
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
