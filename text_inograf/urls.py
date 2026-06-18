from django.urls import path
from . import views

urlpatterns = [
    path('', views.text_to_image, name='text_to_image')
]