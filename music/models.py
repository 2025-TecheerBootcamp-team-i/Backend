# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models


class Music(models.Model):
    music_id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey('Users', models.DO_NOTHING, blank=True, null=True)
    artist = models.ForeignKey('Artists', models.DO_NOTHING, blank=True, null=True)
    album = models.ForeignKey('Albums', models.DO_NOTHING, blank=True, null=True)
    music_name = models.CharField(max_length=200)
    is_ai = models.BooleanField(blank=True, null=True)
    audio_url = models.CharField(max_length=200, blank=True, null=True)
    genre = models.CharField(max_length=50, blank=True, null=True)
    duration = models.IntegerField(blank=True, null=True)
    lyrics = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)
    is_deleted = models.BooleanField(blank=True, null=True)
    valence = models.DecimalField(max_digits=10, decimal_places=6, blank=True, null=True)
    arousal = models.DecimalField(max_digits=10, decimal_places=6, blank=True, null=True)
    itunes_id = models.BigIntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'music'


class Artists(models.Model):
    artist_id = models.BigAutoField(primary_key=True)
    artist_name = models.CharField(max_length=100)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)
    is_deleted = models.BooleanField(blank=True, null=True)
    artist_image = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'artists'


class Albums(models.Model):
    album_id = models.BigAutoField(primary_key=True)
    artist = models.ForeignKey(Artists, models.DO_NOTHING, blank=True, null=True)
    album_name = models.CharField(max_length=200, blank=True, null=True)
    album_image = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)
    is_deleted = models.BooleanField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'albums'


class Tags(models.Model):
    tag_id = models.BigAutoField(primary_key=True)
    tag_key = models.TextField(unique=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_deleted = models.BooleanField()

    class Meta:
        managed = False
        db_table = 'tags'


class MusicTags(models.Model):
    tag = models.ForeignKey(Tags, models.DO_NOTHING)
    music = models.OneToOneField(Music, models.DO_NOTHING, primary_key=True)  # The composite primary key (music_id, tag_id) found, that is not supported. The first column is selected.
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    is_deleted = models.BooleanField()

    class Meta:
        managed = False
        db_table = 'music_tags'
        unique_together = (('music', 'tag'),)


class Users(models.Model):
    user_id = models.BigAutoField(primary_key=True)
    email = models.CharField(max_length=100)
    password = models.IntegerField(blank=True, null=True)
    nickname = models.CharField(max_length=50, blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)
    is_deleted = models.BooleanField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'users'
