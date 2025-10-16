from django.urls import path
from . import views

urlpatterns = [
    path('health/', views.health, name='api-health'),
    path('movies/', views.movies_list, name='api-movies'),
]
