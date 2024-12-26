# Generated by Django 5.1 on 2024-11-09 14:45

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0009_address'),
        ('orders', '0003_alter_order_order_note'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='profile',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='order', to='accounts.profile'),
        ),
    ]
