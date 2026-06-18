from django.urls import path
from . import views

urlpatterns = [
    path('', views.youtube_to_image, name='youtube_to_image')
]