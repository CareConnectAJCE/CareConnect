from django.contrib import admin
from .models import User, Appointment, Conversation, Doctor, Report

# Register your models here.
admin.site.register(User)
admin.site.register(Appointment)
admin.site.register(Conversation)
admin.site.register(Doctor)
admin.site.register(Report)