# Generated by Django 4.2.6 on 2024-02-02 09:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0009_doctor'),
    ]

    operations = [
        migrations.AddField(
            model_name='doctor',
            name='experience',
            field=models.IntegerField(default=1),
            preserve_default=False,
        ),
    ]