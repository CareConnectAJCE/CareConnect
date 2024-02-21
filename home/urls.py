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
    path('dashboard/admin/', views.admin_view, name='admin'),
    path('doctor/', views.doctor_view, name='doctor'),
    path('doctor/single/<int:id>/', views.doctor_single_view, name='doctor_single'),
    path('doctor/rate/', views.doctor_rating, name='doctor_rating'),
    path('patient/', views.patient_view, name='patient'),
    path('patient/single/<int:id>/', views.patient_single_view, name='patient_single'),
    path('patient/location', views.save_user_location, name='patient_location'),
    path('patient/prescription/<int:id>/', views.patient_prescription, name='patient_prescription'),
    path('doctor/register/', views.doctor_registration, name='doctor_register'),
    path('doctor/approve/<str:sub>/', views.approve_doctor, name="approve_doctor"),
    path('appointment/', views.appointment, name='appointment'),
    path('appointment/visited/', views.appointment_visited, name='mark_visited'),
    path('appointment/deleted/', views.appointment_deleted, name='mark_deleted'),
    path('chat/', views.chatbot_landing, name='chat'),
    path('response/', views.get_bot_response, name='bot_response'),
    path('predict/doctor', views.predict_doctor_symptom, name="doctor_predictor")
]
