from django.urls import path
from . import views

urlpatterns = [
    path('', views.chat_doc, name='chat_doc'),
    path('api/message/', views.chat_message, name='chat_message'),
]
