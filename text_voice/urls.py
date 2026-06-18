from django.urls import path
from . import views

urlpatterns = [
    path('', views.text_to_voice, name='text_to_voice')
]