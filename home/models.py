from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    sub = models.CharField(max_length=255, unique=True)
    is_doctor = models.BooleanField(default=False)

    def __str__(self):
        return self.username
    
class Doctor(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True, related_name="doctor_details")
    specialization = models.CharField(max_length=255)
    qualification = models.TextField()
    experience = models.IntegerField()
    phone = models.CharField(max_length=15)
    address = models.TextField()
    city = models.CharField(max_length=255)
    state = models.CharField(max_length=255)
    country = models.CharField(max_length=255)
    zip = models.CharField(max_length=10)
    latitude = models.FloatField(null=True)
    longitude = models.FloatField(null=True)

class Appointment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="patient")
    doctor = models.ForeignKey(User, on_delete=models.CASCADE, related_name="doctor")
    appointment_time = models.DateTimeField(null=True)
    reason = models.TextField()
    visited = models.BooleanField(default=False)
    visited_time = models.DateTimeField(null=True)
    doctor_remarks = models.TextField(null=True)

    def __str__(self):
        return f"{self.user.username} -> {self.doctor.username} ({self.appointment_time}) for {self.reason}"

class Conversation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    is_user_message = models.BooleanField()
    message_content = models.TextField()

    def __str__(self):
        sender = "User" if self.is_user_message else "Bot"
        return f"{sender}: {self.message_content} (User: {self.user.username})"