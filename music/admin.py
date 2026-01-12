from django.contrib import admin
from .models import (
    Music, Artists, Albums, Genres, Tags, MusicTags,
    Playlists, PlaylistItems, PlaylistLikes,
    Users, UsersGenre,
    PlayLogs, MusicLikes, Charts,
    AiInfo
)


# ===== 🎵 MUSIC 섹션 =====

@admin.register(Music)
class MusicAdmin(admin.ModelAdmin):
    list_display = ('music_id', 'music_name', 'get_artist_name', 'get_album_name', 'genre', 'duration_display', 'is_ai', 'created_at')
    list_filter = ('is_ai', 'is_deleted', 'created_at')
    search_fields = ('music_name', 'artist__artist_name', 'album__album_name', 'genre')
    list_per_page = 100
    ordering = ('-created_at',)
    
    def get_artist_name(self, obj):
        return obj.artist.artist_name if obj.artist else '-'
    get_artist_name.short_description = '아티스트'
    
    def get_album_name(self, obj):
        return obj.album.album_name if obj.album else '-'
    get_album_name.short_description = '앨범'
    
    def duration_display(self, obj):
        if obj.duration:
            minutes = obj.duration // 60
            seconds = obj.duration % 60
            return f"{minutes}:{seconds:02d}"
        return '-'
    duration_display.short_description = '재생시간'


@admin.register(Artists)
class ArtistsAdmin(admin.ModelAdmin):
    list_display = ('artist_id', 'artist_name', 'get_music_count', 'created_at', 'is_deleted')
    search_fields = ('artist_name',)
    list_filter = ('is_deleted', 'created_at')
    list_per_page = 100
    
    def get_music_count(self, obj):
        return obj.music_set.count()
    get_music_count.short_description = '곡 수'


@admin.register(Albums)
class AlbumsAdmin(admin.ModelAdmin):
    list_display = ('album_id', 'album_name', 'get_artist_name', 'created_at', 'is_deleted')
    search_fields = ('album_name', 'artist__artist_name')
    list_filter = ('is_deleted', 'created_at')
    list_per_page = 100
    
    def get_artist_name(self, obj):
        return obj.artist.artist_name if obj.artist else '-'
    get_artist_name.short_description = '아티스트'


@admin.register(Genres)
class GenresAdmin(admin.ModelAdmin):
    list_display = ('genre_id', 'genre_name', 'created_at', 'is_deleted')
    search_fields = ('genre_name',)
    list_filter = ('is_deleted',)
    list_per_page = 50


@admin.register(Tags)
class TagsAdmin(admin.ModelAdmin):
    list_display = ('tag_id', 'tag_key', 'created_at', 'is_deleted')
    search_fields = ('tag_key',)
    list_filter = ('is_deleted',)
    list_per_page = 50


@admin.register(MusicTags)
class MusicTagsAdmin(admin.ModelAdmin):
    list_display = ('get_music_name', 'get_tag_name', 'created_at')
    search_fields = ('music__music_name', 'tag__tag_key')
    list_per_page = 100
    
    def get_music_name(self, obj):
        return obj.music.music_name if obj.music else '-'
    get_music_name.short_description = '음악'
    
    def get_tag_name(self, obj):
        return obj.tag.tag_key if obj.tag else '-'
    get_tag_name.short_description = '태그'


# ===== 📝 PLAYLIST 섹션 =====

@admin.register(Playlists)
class PlaylistsAdmin(admin.ModelAdmin):
    list_display = ('playlist_id', 'title', 'get_user_nickname', 'visibility', 'created_at', 'is_deleted')
    search_fields = ('title', 'user__nickname')
    list_filter = ('visibility', 'is_deleted', 'created_at')
    list_per_page = 50
    
    def get_user_nickname(self, obj):
        return obj.user.nickname if obj.user else '-'
    get_user_nickname.short_description = '생성자'


@admin.register(PlaylistItems)
class PlaylistItemsAdmin(admin.ModelAdmin):
    list_display = ('item_id', 'get_playlist_title', 'get_music_name', 'order', 'created_at')
    search_fields = ('playlist__title', 'music__music_name')
    list_per_page = 50
    
    def get_playlist_title(self, obj):
        return obj.playlist.title if obj.playlist else '-'
    get_playlist_title.short_description = '플레이리스트'
    
    def get_music_name(self, obj):
        return obj.music.music_name if obj.music else '-'
    get_music_name.short_description = '음악'


@admin.register(PlaylistLikes)
class PlaylistLikesAdmin(admin.ModelAdmin):
    list_display = ('like_id', 'get_playlist_title', 'get_user_nickname', 'created_at')
    search_fields = ('playlist__title', 'user__nickname')
    list_per_page = 50
    
    def get_playlist_title(self, obj):
        return obj.playlist.title if obj.playlist else '-'
    get_playlist_title.short_description = '플레이리스트'
    
    def get_user_nickname(self, obj):
        return obj.user.nickname if obj.user else '-'
    get_user_nickname.short_description = '사용자'


# ===== 👤 USER 섹션 =====

@admin.register(Users)
class UsersAdmin(admin.ModelAdmin):
    list_display = ('user_id', 'nickname', 'email', 'created_at', 'is_deleted')
    search_fields = ('nickname', 'email')
    list_filter = ('is_deleted', 'created_at')
    list_per_page = 50


@admin.register(UsersGenre)
class UsersGenreAdmin(admin.ModelAdmin):
    list_display = ('get_user_id', 'get_user_nickname', 'get_genre_name', 'created_at')
    search_fields = ('user__nickname', 'genre__genre_name')
    list_per_page = 50
    
    def get_user_id(self, obj):
        return obj.user.user_id if obj.user else '-'
    get_user_id.short_description = 'User ID'
    
    def get_user_nickname(self, obj):
        return obj.user.nickname if obj.user else '-'
    get_user_nickname.short_description = '사용자'
    
    def get_genre_name(self, obj):
        return obj.genre.genre_name if obj.genre else '-'
    get_genre_name.short_description = '선호 장르'


# ===== 📊 ANALYTICS 섹션 =====

@admin.register(PlayLogs)
class PlayLogsAdmin(admin.ModelAdmin):
    list_display = ('play_log_id', 'get_user_nickname', 'get_music_name', 'played_at')
    search_fields = ('user__nickname', 'music__music_name')
    list_filter = ('played_at',)
    list_per_page = 100
    ordering = ('-played_at',)
    
    def get_user_nickname(self, obj):
        return obj.user.nickname if obj.user else '-'
    get_user_nickname.short_description = '사용자'
    
    def get_music_name(self, obj):
        return obj.music.music_name if obj.music else '-'
    get_music_name.short_description = '음악'


@admin.register(MusicLikes)
class MusicLikesAdmin(admin.ModelAdmin):
    list_display = ('like_id', 'get_user_nickname', 'get_music_name', 'created_at')
    search_fields = ('user__nickname', 'music__music_name')
    list_filter = ('created_at',)
    list_per_page = 100
    
    def get_user_nickname(self, obj):
        return obj.user.nickname if obj.user else '-'
    get_user_nickname.short_description = '사용자'
    
    def get_music_name(self, obj):
        return obj.music.music_name if obj.music else '-'
    get_music_name.short_description = '음악'


@admin.register(Charts)
class ChartsAdmin(admin.ModelAdmin):
    list_display = ('chart_id', 'get_music_name', 'rank', 'play_count', 'chart_date', 'type')
    search_fields = ('music__music_name',)
    list_filter = ('type', 'chart_date', 'created_at')
    ordering = ('rank',)
    list_per_page = 100
    
    def get_music_name(self, obj):
        return obj.music.music_name if obj.music else '-'
    get_music_name.short_description = '음악'


# ===== 🤖 AI 섹션 =====

@admin.register(AiInfo)
class AiInfoAdmin(admin.ModelAdmin):
    list_display = ('aiinfo_id', 'get_music_name', 'get_input_prompt_short', 'created_at')
    search_fields = ('music__music_name', 'input_prompt')
    list_filter = ('created_at',)
    list_per_page = 50
    
    def get_music_name(self, obj):
        return obj.music.music_name if obj.music else '-'
    get_music_name.short_description = '음악'
    
    def get_input_prompt_short(self, obj):
        if obj.input_prompt:
            return obj.input_prompt[:50] + '...' if len(obj.input_prompt) > 50 else obj.input_prompt
        return '-'
    get_input_prompt_short.short_description = 'AI 프롬프트'
