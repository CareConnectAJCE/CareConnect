# Generated by Django 4.2.6 on 2024-01-24 03:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0004_appointment'),
    ]

    operations = [
        migrations.AddField(
            model_name='appointment',
            name='visited',
            field=models.BooleanField(default=False),
        ),
    ]