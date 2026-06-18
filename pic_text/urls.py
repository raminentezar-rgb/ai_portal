from django.urls import path
from . import views


urlpatterns = [
    path('', views.pic_text, name='pic_text'),
]

