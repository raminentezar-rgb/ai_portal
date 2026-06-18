from django.urls import path
from . import views

urlpatterns = [
    path('', views.ai_quiz, name='ai_quiz'),
]
