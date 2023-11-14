from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    sub = models.CharField(max_length=255, unique=True)