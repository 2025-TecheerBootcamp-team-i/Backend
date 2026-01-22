"""
좋아요 관련 Views - 음악 좋아요 등록/취소, 앨범 좋아요 등록/취소
"""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from ..models import Music, MusicLikes, Users, Playlists, PlaylistItems, Albums, AlbumLikes
from ..serializers import MusicLikeSerializer, UserLikedMusicSerializer, AlbumLikeSerializer, UserLikedAlbumSerializer


class MusicLikeView(APIView):
    """
    음악 좋아요 등록/취소 API
    
    - POST: 좋아요 등록
    - DELETE: 좋아요 취소
    """
    permission_classes = [AllowAny]
    
    @extend_schema(
        summary="좋아요 등록",
        description="음악에 좋아요 등록",
        tags=['좋아요']
    )
    
    def post(self, request, music_id):
        """
        좋아요 등록
        POST /api/v1/tracks/{musicId}/like
        
        좋아요를 누르면:
        1. MusicLikes 테이블에 좋아요 등록
        2. "나의 좋아요 목록" 시스템 플레이리스트에 자동으로 곡 추가
        """
        # 인증 확인 (테스트용: 인증 없으면 userId 1 사용)
        if not request.user or not request.user.is_authenticated:
            # 테스트용: userId 1 사용
            user = get_object_or_404(Users, user_id=1)
        else:
            user = request.user
        
        # 음악 존재 확인 (SoftDeleteManager가 자동으로 is_deleted=False인 레코드만 조회)
        music = get_object_or_404(Music, music_id=music_id)
        
        # 이미 좋아요가 있는지 확인
        # SoftDeleteManager를 사용하므로 all_objects로 삭제된 것도 확인
        like = MusicLikes.all_objects.filter(user=user, music=music).first()
        
        is_new_like = False
        if like:
            if like.is_deleted:
                # 삭제된 좋아요를 복구
                like.restore()
                is_new_like = True
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
            like = MusicLikes.objects.create(user=user, music=music)
            is_new_like = True
        
        # 시스템 플레이리스트 ("나의 좋아요 목록")에 자동으로 곡 추가
        if is_new_like:
            try:
                # 사용자의 시스템 플레이리스트 조회
                system_playlist = Playlists.objects.filter(
                    user=user,
                    visibility='system',
                    title='나의 좋아요 목록'
                ).first()
                
                if system_playlist:
                    # 이미 플레이리스트에 추가되어 있는지 확인
                    existing_item = PlaylistItems.objects.filter(
                        playlist=system_playlist,
                        music=music
                    ).first()
                    
                    if not existing_item:
                        # 마지막 순서 계산
                        last_item = PlaylistItems.objects.filter(
                            playlist=system_playlist
                        ).order_by('-order').first()
                        
                        next_order = (last_item.order + 1) if last_item else 1
                        
                        # 시스템 플레이리스트에 곡 추가
                        PlaylistItems.objects.create(
                            playlist=system_playlist,
                            music=music,
                            order=next_order
                        )
            except Exception as e:
                # 시스템 플레이리스트 추가 실패해도 좋아요는 정상 처리
                import logging
                logging.getLogger(__name__).warning(
                    f"시스템 플레이리스트 추가 실패: user_id={user.user_id}, "
                    f"music_id={music_id}, error={e}"
                )
        
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
        DELETE /api/v1/tracks/{musicId}/like
        
        좋아요를 취소하면:
        1. MusicLikes 테이블에서 좋아요 삭제
        2. "나의 좋아요 목록" 시스템 플레이리스트에서 곡 제거
        """
        # 인증 확인 (테스트용: 인증 없으면 userId 1 사용)
        if not request.user or not request.user.is_authenticated:
            # 테스트용: userId 1 사용
            user = get_object_or_404(Users, user_id=1)
        else:
            user = request.user
        
        # 음악 존재 확인 (SoftDeleteManager가 자동으로 is_deleted=False인 레코드만 조회)
        music = get_object_or_404(Music, music_id=music_id)
        
        # 좋아요 찾기 (SoftDeleteManager가 자동으로 is_deleted=False인 레코드만 조회)
        try:
            like = MusicLikes.objects.get(user=user, music=music)
            # TrackableMixin의 delete() 메서드가 자동으로 Soft Delete 수행
            like.delete()
            
            # 시스템 플레이리스트 ("나의 좋아요 목록")에서 곡 제거
            try:
                # 사용자의 시스템 플레이리스트 조회
                system_playlist = Playlists.objects.filter(
                    user=user,
                    visibility='system',
                    title='나의 좋아요 목록'
                ).first()
                
                if system_playlist:
                    # 플레이리스트에서 해당 곡 제거
                    playlist_item = PlaylistItems.objects.filter(
                        playlist=system_playlist,
                        music=music
                    ).first()
                    
                    if playlist_item:
                        playlist_item.delete()
            except Exception as e:
                # 시스템 플레이리스트 제거 실패해도 좋아요 취소는 정상 처리
                import logging
                logging.getLogger(__name__).warning(
                    f"시스템 플레이리스트 제거 실패: user_id={user.user_id}, "
                    f"music_id={music_id}, error={e}"
                )
            
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


class UserLikedMusicListView(APIView):
    """
    사용자가 좋아요한 곡 목록 조회 API
    
    - GET: 사용자가 좋아요한 모든 곡 목록 조회
    """
    permission_classes = [AllowAny]
    
    @extend_schema(
        summary="사용자 좋아요 곡 목록 조회",
        description="특정 사용자가 좋아요한 모든 곡 목록을 조회합니다.",
        tags=['좋아요'],
        responses={200: UserLikedMusicSerializer(many=True)}
    )
    def get(self, request, user_id):
        """
        사용자가 좋아요한 곡 목록 조회
        GET /api/v1/users/{user_id}/likes
        """
        # 사용자 존재 확인
        user = get_object_or_404(Users, user_id=user_id)
        
        # 해당 사용자가 좋아요한 곡들의 music_id 조회
        liked_music_ids = MusicLikes.objects.filter(
            user=user,
            is_deleted=False
        ).values_list('music_id', flat=True)
        
        # 좋아요한 곡이 없는 경우
        if not liked_music_ids:
            return Response(
                {
                    'message': '좋아요한 곡이 없습니다.',
                    'user_id': user_id,
                    'count': 0,
                    'results': []
                },
                status=status.HTTP_200_OK
            )
        
        # 좋아요한 곡들의 상세 정보 조회 (select_related로 최적화)
        liked_musics = Music.objects.filter(
            music_id__in=liked_music_ids,
            is_deleted=False
        ).select_related('artist', 'album').order_by('-created_at')
        
        serializer = UserLikedMusicSerializer(liked_musics, many=True)
        
        return Response(
            {
                'message': '좋아요한 곡 목록을 조회했습니다.',
                'user_id': user_id,
                'count': liked_musics.count(),
                'results': serializer.data
            },
            status=status.HTTP_200_OK
        )


class AlbumLikeView(APIView):
    """
    앨범 좋아요 등록/취소 API
    
    - POST: 좋아요 등록
    - DELETE: 좋아요 취소
    """
    permission_classes = [AllowAny]
    
    @extend_schema(
        summary="앨범 좋아요 등록",
        description="앨범에 좋아요 등록",
        tags=['좋아요']
    )
    def post(self, request, album_id):
        """
        앨범 좋아요 등록
        POST /api/v1/albums/{albumId}/likes
        """
        # 인증 확인 (테스트용: 인증 없으면 userId 1 사용)
        if not request.user or not request.user.is_authenticated:
            # 테스트용: userId 1 사용
            user = get_object_or_404(Users, user_id=1)
        else:
            user = request.user
        
        # 앨범 존재 확인 (SoftDeleteManager가 자동으로 is_deleted=False인 레코드만 조회)
        album = get_object_or_404(Albums, album_id=album_id)
        
        # 이미 좋아요가 있는지 확인
        # SoftDeleteManager를 사용하므로 all_objects로 삭제된 것도 확인
        like = AlbumLikes.all_objects.filter(user=user, album=album).first()
        
        if like:
            if like.is_deleted:
                # 삭제된 좋아요를 복구
                like.restore()
            else:
                # 이미 활성화된 좋아요가 있음
                like_count = AlbumLikes.objects.filter(album=album).count()
                return Response(
                    {
                        'message': '이미 좋아요를 누른 앨범입니다.',
                        'album_id': album_id,
                        'is_liked': True,
                        'like_count': like_count
                    },
                    status=status.HTTP_200_OK
                )
        else:
            # 새로운 좋아요 생성
            like = AlbumLikes.objects.create(user=user, album=album)
        
        # 좋아요 개수 조회
        like_count = AlbumLikes.objects.filter(album=album).count()
        
        serializer = AlbumLikeSerializer({
            'message': '앨범 좋아요가 추가되었습니다.',
            'album_id': album_id,
            'is_liked': True,
            'like_count': like_count
        })
        
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @extend_schema(
        summary="앨범 좋아요 취소",
        description="앨범 좋아요 취소",
        tags=['좋아요']
    )
    def delete(self, request, album_id):
        """
        앨범 좋아요 취소
        DELETE /api/v1/albums/{albumId}/likes
        """
        # 인증 확인 (테스트용: 인증 없으면 userId 1 사용)
        if not request.user or not request.user.is_authenticated:
            # 테스트용: userId 1 사용
            user = get_object_or_404(Users, user_id=1)
        else:
            user = request.user
        
        # 앨범 존재 확인 (SoftDeleteManager가 자동으로 is_deleted=False인 레코드만 조회)
        album = get_object_or_404(Albums, album_id=album_id)
        
        # 좋아요 찾기 (SoftDeleteManager가 자동으로 is_deleted=False인 레코드만 조회)
        try:
            like = AlbumLikes.objects.get(user=user, album=album)
            # TrackableMixin의 delete() 메서드가 자동으로 Soft Delete 수행
            like.delete()
            
            # 좋아요 개수 조회
            like_count = AlbumLikes.objects.filter(album=album).count()
            
            serializer = AlbumLikeSerializer({
                'message': '앨범 좋아요가 취소되었습니다.',
                'album_id': album_id,
                'is_liked': False,
                'like_count': like_count
            })
            
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except AlbumLikes.DoesNotExist:
            # 좋아요 개수 조회
            like_count = AlbumLikes.objects.filter(album=album).count()
            
            return Response(
                {
                    'message': '좋아요를 누르지 않은 앨범입니다.',
                    'album_id': album_id,
                    'is_liked': False,
                    'like_count': like_count
                },
                status=status.HTTP_404_NOT_FOUND
            )


class UserLikedAlbumsView(APIView):
    """
    사용자가 좋아요한 앨범 목록 조회 API
    
    - GET: 사용자가 좋아요한 모든 앨범 목록 조회
    """
    permission_classes = [AllowAny]
    
    @extend_schema(
        summary="좋아요한 앨범 목록 조회",
        description="현재 로그인한 사용자가 좋아요한 모든 앨범 목록을 조회합니다.",
        tags=['좋아요'],
        responses={200: UserLikedAlbumSerializer(many=True)}
    )
    def get(self, request):
        """
        좋아요한 앨범 목록 조회
        GET /api/v1/albums/likes
        """
        # 인증 확인 (테스트용: 인증 없으면 userId 1 사용)
        if not request.user or not request.user.is_authenticated:
            # 테스트용: userId 1 사용
            user = get_object_or_404(Users, user_id=1)
        else:
            user = request.user
        
        # 해당 사용자가 좋아요한 앨범들의 album_id 조회
        liked_album_ids = AlbumLikes.objects.filter(
            user=user,
            is_deleted=False
        ).values_list('album_id', flat=True)
        
        # 좋아요한 앨범들의 상세 정보 조회 (select_related로 최적화)
        liked_albums = Albums.objects.filter(
            album_id__in=liked_album_ids,
            is_deleted=False
        ).select_related('artist').order_by('-created_at')
        
        serializer = UserLikedAlbumSerializer(liked_albums, many=True, context={'request': request})
        
        return Response(serializer.data, status=status.HTTP_200_OK)
