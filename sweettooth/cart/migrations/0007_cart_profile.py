# Generated by Django 5.1 on 2024-10-28 05:22

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0009_address'),
        ('cart', '0006_cartitem_total'),
    ]

    operations = [
        migrations.AddField(
            model_name='cart',
            name='profile',
            field=models.OneToOneField(default='', on_delete=django.db.models.deletion.CASCADE, related_name='cart', to='accounts.profile'),
        ),
    ]
