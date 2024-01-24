from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path("login", views.login, name="login"),
    path("logout", views.logout, name="logout"),
    path("callback", views.callback, name="callback"),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    path('edit_user', views.edit_user, name='edit_user'),
    path('doctor/', views.doctor_view, name='doctor'),
    path('patient/', views.patient_view, name='patient'),
    path('appointment/visited/', views.appointment_visited, name='mark_visited'),
    path('appointment/deleted/', views.appointment_deleted, name='mark_deleted'),
    path('chat/', views.chatbot_landing, name='chat'),
    path('response/', views.get_bot_response, name='bot_response')
]
