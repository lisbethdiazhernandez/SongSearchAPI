import requests
import datetime
import os
from rest_framework import viewsets
from .models import Song
from .serializers import SongSerializer
from rest_framework.response import Response
from rest_framework import status

class SongViewSet(viewsets.ModelViewSet):
    queryset = Song.objects.all().order_by('name')
    serializer_class = SongSerializer
    spotify_access_token = None
    spotify_token_expires = None
    genius_access_token = None
    genius_token_expires = None

    def get_spotify_access_token(self):

        if self.spotify_access_token and self.spotify_token_expires > datetime.datetime.now():
            # Token is still valid
            return self.spotify_access_token

        client_id = os.getenv("SPOTIFY_CLIENT_ID")
        client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
        try:
            response = requests.post('https://accounts.spotify.com/api/token', data={'grant_type': 'client_credentials'}, auth=(client_id, client_secret))
            response.raise_for_status()  # Raise an exception if the request was unsuccessful
            expires_in = response.json().get('expires_in', 0)
            self.spotify_token_expires = datetime.datetime.now() + datetime.timedelta(seconds=expires_in)
            self.spotify_access_token = response.json().get('access_token')
            return self.spotify_access_token
        except requests.exceptions.RequestException as e:
            raise ValueError("Error getting Spotify access token") from e

    def get_genius_access_token(self):
        if self.genius_access_token and self.genius_token_expires > datetime.datetime.now():
            # Token is still valid
            return self.genius_access_token

        client_id = os.getenv("GENIUS_CLIENT_ID")
        client_secret = os.getenv("GENIUS_CLIENT_SECRET")
        try:
            response = requests.post('https://api.genius.com/oauth/token', data={'grant_type': 'client_credentials'}, auth=(client_id, client_secret))
            response.raise_for_status()  # Raise an exception if the request was unsuccessful

            expires_in = response.json().get('expires_in', 0)
            self.genius_token_expires = datetime.datetime.now() + datetime.timedelta(seconds=expires_in)
            self.genius_access_token = response.json().get('access_token')
            return self.genius_access_token
        except requests.exceptions.RequestException as e:
            raise ValueError("Error getting Genius access token") from e


    def get_itunes_data(self, search_term):
        try:
            response = requests.get(f'https://itunes.apple.com/search?term={search_term}&media=music&entity=song&limit=10')
            response.raise_for_status()  # Raise an exception if the request was unsuccessful
            return response.json().get('results', [])
        except requests.exceptions.RequestException as e:
            raise ValueError("Error fetching data from iTunes API") from e

    def get_genius_data(self, search_term, access_token):
        headers = {'Authorization': f'Bearer {access_token}'}
        try:
            response = requests.get('https://api.genius.com/search', params={'q': search_term}, headers=headers)
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
                
            return results
        except requests.exceptions.RequestException as e:
            raise ValueError("Error fetching data from Genius API") from e


    def get_spotify_data(self, search_term, access_token):
        headers = {'Authorization': f'Bearer {access_token}'}
        tracks = []
        try:
            response = requests.get(f'https://api.spotify.com/v1/search', params={'q': search_term, 'type': 'track', 'limit': 10}, headers=headers)
            response.raise_for_status()  # Raise an exception if the request was unsuccessful
            tracks_data = response.json().get('tracks', {}).get('items', [])
            
            for track_data in tracks_data:
                track = track_data.copy()  # copy track data to not modify original data
                artist_id = track_data['artists'][0]['id']  # get the artist id
                
                # make a new request to get the artist info to get genres
                response = requests.get(f'https://api.spotify.com/v1/artists/{artist_id}', headers=headers)
                response.raise_for_status()  # Raise an exception if the request was unsuccessful
                
                artist_info = response.json()
                track['artist_genres'] = artist_info.get('genres', [])  # add the artist's genres to the track data
                
                tracks.append(track)
        except requests.exceptions.RequestException as e:
            raise ValueError("Error fetching data from Spotify API") from e

        return tracks

    def get_queryset(self):
        queryset = Song.objects.all()
        album = self.request.query_params.get('album', None)
        genre = self.request.query_params.get('genre', None)

        if album is not None:
            queryset = queryset.filter(album__icontains=album)
        
        if genre is not None:
            queryset = queryset.filter(genres__icontains=genre)
        
        return queryset.order_by('name')

    def list(self, request, *args, **kwargs):
        search_term = request.query_params.get('search_term', '')

        try:
            spotify_access_token = self.get_spotify_access_token()
            genius_access_token = self.get_genius_access_token()

            data_itunes = self.get_itunes_data(search_term)
            data_spotify = self.get_spotify_data(search_term, spotify_access_token)
            data_genius = self.get_genius_data(search_term, genius_access_token)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


        # Clear existing data
        Song.objects.all().delete()

        # iTunes - Create song objects
        for song in data_itunes:
            Song.objects.create(
                name=song.get('trackName', ''),
                provider_song_id=song.get('trackId', ''),
                album=song.get('collectionName', ''),
                artist=song.get('artistName', ''),
                album_cover=song.get('artworkUrl100', ''),
                year_release_date=song.get('releaseDate', '')[:4],
                genres=song.get('primaryGenreName',''),
                duration=song.get('trackTimeMillis', ''),
                origin='iTunes',
            )
            
        # Spotify - Create song objects
        for song in data_spotify:
            album = song.get('album', {})
            artists = [artist.get('name', '') for artist in song.get('artists', [])]
            genres = ', '.join(song.get('artist_genres', []))
            Song.objects.create(
                name=song.get('name', ''),
                provider_song_id=song.get('id', ''),
                album=album.get('name', ''),
                artist=', '.join(artists),
                album_cover=album.get('images', [{}])[0].get('url', ''),
                year_release_date=album.get('release_date', '')[:4],
                genres=genres,
                duration=song.get('duration_ms', ''),
                origin='Spotify',
            )

       # Genius - Create song objects
        for hit in data_genius:
            song = hit.get('result', {})
            artists = [song.get('primary_artist', {}).get('name', '')]
            genres = song.get('genres', '')
            year_release_date = song.get('year_release_date', '')

            Song.objects.create(
                name=song.get('title', ''),
                provider_song_id=song.get('id', ''),
                album=song.get('album', ''),
                artist=', '.join(artists),
                album_cover=song.get('song_art_image_url', ''),
                year_release_date=year_release_date,
                genres='N/A', #Genius does not provide Genres
                duration='N/A', #Genius does not provide Duration
                origin='Genius',
            )



        self.queryset = self.queryset.order_by('name', 'artist')
        return super().list(request, *args, **kwargs)
 
