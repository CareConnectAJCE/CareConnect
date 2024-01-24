from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    sub = models.CharField(max_length=255, unique=True)
    is_doctor = models.BooleanField(default=False)

    def __str__(self):
        return self.username

class Appointment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    doctor = models.ForeignKey(User, on_delete=models.CASCADE, related_name="doctor")
    appointment_time = models.DateTimeField()
    reason = models.TextField()
    visited = models.BooleanField(default=False)
    visited_time = models.DateTimeField(null=True)

    def __str__(self):
        return f"{self.user.username} -> {self.doctor.username} ({self.appointment_time}) for {self.reason}"

class Conversation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    is_user_message = models.BooleanField()
    message_content = models.TextField()

    def __str__(self):
        sender = "User" if self.is_user_message else "Bot"
        return f"{sender}: {self.message_content} (User: {self.user.username})"