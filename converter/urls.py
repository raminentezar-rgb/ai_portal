"""
URL configuration for converter project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('sw.js', TemplateView.as_view(template_name='sw.js', content_type='application/javascript'), name='sw.js'),
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
    path('text_inograf/', include('text_inograf.urls')),
    path('video_inograf/', include('video_inograf.urls')),
    path('youtube_inograf/', include('youtube_inograf.urls')),
    path('text_voice/', include('text_voice.urls')),
    path('video_text/', include('video_text.urls')),
    path('youtube_text/', include('youtube_text.urls')),
    path('text_inograf/', include('text_inograf.urls')),
    path('pic_text/', include('pic_text.urls')),
    path('web_inograf/', include('web_inograf.urls')),
    path('audio_inograf/', include('audio_inograf.urls')),
    path('ai_quiz/', include('ai_quiz.urls')),
    path('chat_doc/', include('chat_doc.urls')),
    path('data_chart/', include('data_chart.urls')),
    path('accounts/', include('accounts.urls')),
    path('accounts/', include('allauth.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
