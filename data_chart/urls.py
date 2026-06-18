from django.urls import path
from . import views

urlpatterns = [
    path('', views.data_chart, name='data_chart'),
]
