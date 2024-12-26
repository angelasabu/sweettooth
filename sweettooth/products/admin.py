from django.contrib import admin
from .models import *

# Register your models here.

admin.site.register(Category)

class ProductImageAdmin(admin.StackedInline):
    model = ProductImage

class ProductAdmin(admin.ModelAdmin):
    list_display = ['product_name', 'get_price']
    inlines = [ProductImageAdmin]

    # Custom method to display the price of the first SizeVariant
    def get_price(self, obj):
        size_variant = obj.size_variants.first()  # Get the first size variant
        return size_variant.price if size_variant else 'No Price'

    get_price.short_description = 'Price'

@admin.register(SizeVariant)
class SizeVariantAdmin(admin.ModelAdmin):
    list_display = ['size_name', 'price']
    model = SizeVariant

admin.site.register(Product, ProductAdmin)
admin.site.register(ProductImage)
