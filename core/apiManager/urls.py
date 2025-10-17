from django.urls import path
from . import views

urlpatterns = [
    path('health/', views.health, name='api-health'),
    path('send_audio/', views.send_audio, name='send_audio'),
    
]
