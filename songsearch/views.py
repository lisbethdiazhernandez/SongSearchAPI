import requests
import re
import datetime
import os
from rest_framework import viewsets
from .models import Song
from .serializers import SongSerializer
from rest_framework.response import Response
from rest_framework import status, viewsets
from django.core.cache import cache
import hashlib
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

class Provider:
    def __init__(self, name):
        self.name = name

    def get_access_token(self):
        raise NotImplementedError

    @staticmethod
    def clean_search_term(parameter: str) -> str:
        """
        Clean the search term that the user entered, as it might contain malicious data
        """
        return re.sub(r'[^a-zA-Z0-9_]', '', parameter)

    def get_data(self, search_term: str):
        raise NotImplementedError

    def get_song_details(self, response):
        return response

class Itunes(Provider):
    def __init__(self):
        super().__init__('iTunes')

    def get_access_token(self):
        # iTunes doesn't require an access token, so this method is not implemented for the iTunes provider
        pass

    def get_data(self, search_term: str):
        cleaned_search_term = self.clean_search_term(search_term)
        try:
            response = requests.get(f'https://itunes.apple.com/search',
                                    params={'term': cleaned_search_term, 'media': 'music', 'limit': 10})
            response.raise_for_status()  # Raise an exception if the request was unsuccessful
            return response.json().get('results', [])
        except requests.exceptions.RequestException as e:
            raise ValueError("Error fetching data from iTunes API") from e

    def get_song_details(self, data):
        song_details = []
        for track in data:
            song = Song(
                name=track.get('trackName', ''),
                provider_song_id=track.get('trackId', ''),
                album= track.get('collectionName', ''),
                artist=track.get('artistName', ''),
                album_cover=track.get('artworkUrl100', ''),
                year_release_date=track.get('releaseDate', '')[:4],
                genres=track.get('primaryGenreName', ''),
                duration=track.get('trackTimeMillis', ''),
                origin='iTunes'
            )
            song_details.append(song)
        return song_details

class Spotify(Provider):
    def __init__(self):
        super().__init__('Spotify')
        self.access_token = None
        self.token_expires = None

    def get_access_token(self):
        if self.access_token and self.token_expires > datetime.datetime.now():
            return self.access_token

        client_id = os.getenv("SPOTIFY_CLIENT_ID")
        client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
        try:
            response = requests.post('https://accounts.spotify.com/api/token',
                                     data={'grant_type': 'client_credentials'},
                                     auth=(client_id, client_secret))
            response.raise_for_status()  # Raise an exception if the request was unsuccessful
            expires_in = response.json().get('expires_in', 0)
            self.token_expires = datetime.datetime.now() + datetime.timedelta(seconds=expires_in)
            self.access_token = response.json().get('access_token')
            return self.access_token
        except requests.exceptions.RequestException as e:
            raise ValueError("Error getting Spotify access token") from e

    def get_data(self, search_term: str):
        access_token = self.get_access_token()
        cleaned_search_term = self.clean_search_term(search_term)
        headers = {'Authorization': f'Bearer {access_token}'}

        tracks = []
        try:
            response = requests.get(
                f'https://api.spotify.com/v1/search',
                params={'q': cleaned_search_term, 'type': 'track', 'limit': 10},
                headers=headers
            )
            response.raise_for_status()  # Raise an exception if the request was unsuccessful
            tracks_data = response.json().get('tracks', {}).get('items', [])

            
            for track_data in tracks_data:
                track = track_data.copy()  # Copy track data to not modify the original data
                artist_id = track_data['artists'][0]['id']  # Get the artist id

                # Make a new request to get the artist info to get genres
                response = requests.get(f'https://api.spotify.com/v1/artists/{artist_id}', headers=headers)
                response.raise_for_status()  # Raise an exception if the request was unsuccessful

                artist_info = response.json()
                track['artist_genres'] = artist_info.get('genres', [])  # Add the artist's genres to the track data

                tracks.append(track)

        except requests.exceptions.RequestException as e:
            raise ValueError("Error fetching data from Spotify API") from e
        
        return tracks

    def get_song_details(self, data):
        
        song_details = []
        for track in data:
            album = track.get('album', {})
            artists = [artist.get('name', '') for artist in track.get('artists', [])]
            genres = ', '.join(track.get('artist_genres', []))
            try:
                # Extract relevant details from the track_info response and create a Song object
                song = Song(
                    name=track.get('name', ''),
                    provider_song_id=track.get('id', ''),
                    album=album.get('name', ''),
                    artist=', '.join(artists),
                    album_cover=album.get('images', [{}])[0].get('url', ''),
                    year_release_date=album.get('release_date', '')[:4],
                    genres=genres,
                    duration=track.get('duration_ms', ''),
                    origin='Spotify'
                )

                song_details.append(song)
            except requests.exceptions.RequestException as e:
                # Error occurred while fetching track details, raise the exception to be handled in the viewset
                raise e

        return song_details


class Genius(Provider):
    def __init__(self):
        super().__init__('Genius') 
        self.access_token = None
        self.token_expires = None  

    def get_access_token(self):
        if self.access_token and self.token_expires > datetime.datetime.now():
            return self.access_token

        client_id = os.getenv("GENIUS_CLIENT_ID")
        client_secret = os.getenv("GENIUS_CLIENT_SECRET")
        try:
            response = requests.post('https://api.genius.com/oauth/token',
                                    data={'grant_type': 'client_credentials'},
                                    auth=(client_id, client_secret))
            response.raise_for_status()  # Raise an exception if the request was unsuccessful
            expires_in = response.json().get('expires_in', 0)
            self.token_expires = datetime.datetime.now() + datetime.timedelta(seconds=expires_in)
            self.access_token = response.json().get('access_token')
            return self.access_token
        except requests.exceptions.RequestException as e:
            raise ValueError("Error getting Genius access token") from e

    def get_data(self, search_term: str):
        access_token = self.get_access_token()
        cleaned_search_term = self.clean_search_term(search_term)
        headers = {'Authorization': f'Bearer {access_token}'}
        tracks = []
        try:
            response = requests.get('https://api.genius.com/search', params={'q': cleaned_search_term}, headers=headers)
            response.raise_for_status()  # Raise an exception if the request was unsuccessful
            results = response.json().get('response', {}).get('hits', [])
            for result in results:
                song = result.get('result', {})
                song_id = song.get('id')
                # Make an additional request to get song details
                response = requests.get(f'https://api.genius.com/songs/{song_id}', headers=headers)
                response.raise_for_status()  # Raise an exception if the request was unsuccessful

                song_detail = response.json().get('response', {}).get('song', {})
                album = song_detail.get('album', {})
                song['album'] = album.get('name', '') if album else 'N/A'
                release_date_components = song.get('release_date_components', {})
                song['year_release_date'] = release_date_components.get('year')
            
                tracks.append(song)

            return tracks
        except requests.exceptions.RequestException as e:
            raise ValueError("Error fetching data from Genius API") from e


    def get_song_details(self, data):
        song_details = []
        for track in data:
            artists = [track.get('primary_artist', {}).get('name', '')]
            year_release_date = track.get('year_release_date', '')
            try:
                # Extract relevant details from the song_detail response and create a Song object
                song = Song(
                    name=track.get('title', ''),
                    provider_song_id=track.get('id', ''),
                    album=track.get('album', ''),
                    artist=', '.join(artists),
                    album_cover=track.get('song_art_image_url', ''),
                    year_release_date=year_release_date,
                    genres='N/A', #Genius does not provide Genres
                    duration='N/A', #Genius does not provide Duration
                    origin='Genius',
                )
                song_details.append(song)
            except requests.exceptions.RequestException as e:
                # Error occurred while fetching track details, raise the exception to be handled in the viewset
                raise e

        return song_details


class SongViewSet(viewsets.ViewSet):
    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter('search_term', openapi.IN_QUERY, type=openapi.TYPE_STRING, description='Search term'),
            openapi.Parameter('album', openapi.IN_QUERY, type=openapi.TYPE_STRING, description='Album filter (optional)', required=False),
            openapi.Parameter('genre', openapi.IN_QUERY, type=openapi.TYPE_STRING, description='Genre filter (optional)', required=False),
        ]
    )

    def list(self, request):
        search_term = request.GET.get('search_term')
        album_filter = request.GET.get('album')
        genre_filter = request.GET.get('genre')

        if not search_term:
            return Response({'error': 'Search term is required'}, status=status.HTTP_400_BAD_REQUEST)

       # Generate a unique cache key
        cache_key_parts = ['song_data', search_term]
        if album_filter:
            album_filter = re.sub(r'[^a-zA-Z0-9_]', '', album_filter)
            cache_key_parts.append(album_filter)
        if genre_filter:
            genre_filter = re.sub(r'[^a-zA-Z0-9_]', '', genre_filter)
            cache_key_parts.append(genre_filter)
        cache_key = hashlib.md5(':'.join(cache_key_parts).encode('utf-8')).hexdigest()

        cached_data = cache.get(cache_key)
        if cached_data:
            return Response(cached_data)

        providers = [Spotify(), Itunes(), Genius()]
        song_data = []
        for provider in providers:
            try:
                data = provider.get_data(search_term)
                if provider.name == 'Spotify' or provider.name == 'Genius' or provider.name == 'iTunes':
                    data = provider.get_song_details(data)
                song_data.extend(data)
            except ValueError:
                # Error occurred while fetching data from the provider, skip and continue with the next provider
                pass
        # Filter song_data by album and genre if provided
        if album_filter:
            song_data = [song for song in song_data if song.album == album_filter]
        if genre_filter:
            song_data = [song for song in song_data if genre_filter.lower() in song.genres.lower()]

        # Sort song_data by name and artist
        song_data = sorted(song_data, key=lambda song: (song.name, song.artist))

        serialized_data = SongSerializer(song_data, many=True).data
        # Cache the data for future requests
        cache.set(cache_key, serialized_data, timeout=60 * 60 * 6)  # Cache for 6 hours

        return Response(serialized_data)

