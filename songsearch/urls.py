from django.urls import path, include
from rest_framework.routers import DefaultRouter
from SongSearchAPI.authentication import TokenAuthentication
from .views import SongViewSet

router = DefaultRouter()
router.register('song', SongViewSet, basename='song')

urlpatterns = [
    path('', include(router.urls)),
]
