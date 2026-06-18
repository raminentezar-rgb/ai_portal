from django.urls import path
from . import views

urlpatterns = [
    path('', views.audio_inograf, name='audio_inograf'),
]
