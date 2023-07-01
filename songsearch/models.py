from django.db import models

class Song(models.Model):
    name = models.CharField(max_length=200)
    id = models.CharField(max_length=200)
    album = models.CharField(max_length=200)
    artist = models.CharField(max_length=200)
    album_cover = models.URLField(max_length=200)
    year_release_date = models.CharField(max_length=4)
    genres = models.JSONField()
    duration = models.CharField(max_length=200)
    origin = models.CharField(max_length=200)
