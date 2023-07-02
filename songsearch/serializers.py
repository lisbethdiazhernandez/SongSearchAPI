from rest_framework import serializers
from .models import Song

class SongSerializer(serializers.ModelSerializer):
    genres = serializers.JSONField()

    class Meta:
        model = Song
        fields = ['name', 'provider_song_id', 'album', 'artist', 'album_cover', 'year_release_date', 'genres', 'duration', 'origin']
