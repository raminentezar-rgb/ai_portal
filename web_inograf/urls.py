from django.urls import path
from . import views

urlpatterns = [
    path('', views.web_inograf, name='web_inograf'),
]
