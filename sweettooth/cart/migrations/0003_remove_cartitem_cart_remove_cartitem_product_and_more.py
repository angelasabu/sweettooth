# Generated by Django 5.1 on 2024-10-16 12:43

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('cart', '0002_remove_cart_is_active_remove_cart_product_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='cartitem',
            name='cart',
        ),
        migrations.RemoveField(
            model_name='cartitem',
            name='product',
        ),
        migrations.DeleteModel(
            name='Cart',
        ),
        migrations.DeleteModel(
            name='CartItem',
        ),
    ]