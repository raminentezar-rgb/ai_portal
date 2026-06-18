from django.urls import path
from . import views

urlpatterns = [
    path('', views.video_to_text, name='video_to_text')
]