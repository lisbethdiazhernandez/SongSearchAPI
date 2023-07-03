from rest_framework import authentication
from rest_framework import exceptions
from rest_framework_simplejwt.authentication import JWTAuthentication

class TokenAuthentication(JWTAuthentication):
    def authenticate(self, request):
        # Perform token authentication
        auth = super().authenticate(request)

        if auth is None:
            # No valid token found, raise authentication failed exception
            raise exceptions.AuthenticationFailed('Invalid token')

        return auth
