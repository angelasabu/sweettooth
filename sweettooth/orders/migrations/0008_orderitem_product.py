# Generated by Django 5.1 on 2024-12-09 14:29

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0007_wallet_transaction'),
        ('products', '0007_remove_product_price_remove_product_size_variant_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='orderitem',
            name='product',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='order_items', to='products.product'),
        ),
    ]
