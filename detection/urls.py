from django.urls import path
from . import views

urlpatterns = [
    path('eye/', views.eye_landing, name='eye_landing'),
    path('throat/', views.throat_landing, name='throat_landing'),
]