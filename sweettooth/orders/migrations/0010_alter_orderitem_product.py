# Generated by Django 5.1 on 2024-12-09 14:34

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0009_alter_orderitem_product'),
        ('products', '0007_remove_product_price_remove_product_size_variant_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='orderitem',
            name='product',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='order_items', to='products.product'),
        ),
    ]
