# Generated by Django 2.0.1 on 2018-01-19 07:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reservations', '0007_auto_20180119_0612'),
    ]

    operations = [
        migrations.AlterField(
            model_name='room',
            name='number',
            field=models.CharField(max_length=255, unique=True),
        ),
    ]