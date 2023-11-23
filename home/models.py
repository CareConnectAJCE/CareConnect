from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    sub = models.CharField(max_length=255, unique=True)

class Conversation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    is_user_message = models.BooleanField()
    message_content = models.TextField()

    def __str__(self):
        sender = "User" if self.is_user_message else "Bot"
        return f"{sender}: {self.message_content} (User: {self.user.username})"