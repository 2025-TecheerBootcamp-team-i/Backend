from django.contrib import admin
from .models import Music, Artists, Albums, Tags, MusicTags, Users


@admin.register(Music)
class MusicAdmin(admin.ModelAdmin):
    list_display = ('music_id', 'music_name', 'artist', 'album', 'genre', 'duration', 'is_ai', 'created_at')
    list_filter = ('genre', 'is_ai', 'is_deleted')
    search_fields = ('music_name', 'artist__artist_name', 'album__album_name')
    list_per_page = 50


@admin.register(Artists)
class ArtistsAdmin(admin.ModelAdmin):
    list_display = ('artist_id', 'artist_name', 'created_at', 'is_deleted')
    search_fields = ('artist_name',)
    list_filter = ('is_deleted',)
    list_per_page = 50


@admin.register(Albums)
class AlbumsAdmin(admin.ModelAdmin):
    list_display = ('album_id', 'album_name', 'artist', 'created_at', 'is_deleted')
    search_fields = ('album_name', 'artist__artist_name')
    list_filter = ('is_deleted',)
    list_per_page = 50


@admin.register(Tags)
class TagsAdmin(admin.ModelAdmin):
    list_display = ('tag_id', 'tag_key', 'created_at')
    search_fields = ('tag_key',)


@admin.register(MusicTags)
class MusicTagsAdmin(admin.ModelAdmin):
    list_display = ('music', 'tag', 'created_at')
    search_fields = ('music__music_name', 'tag__tag_key')


@admin.register(Users)
class UsersAdmin(admin.ModelAdmin):
    list_display = ('user_id', 'nickname', 'email', 'created_at', 'is_deleted')
    search_fields = ('nickname', 'email')
    list_filter = ('is_deleted',)
