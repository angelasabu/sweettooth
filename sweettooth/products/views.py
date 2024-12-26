from django.shortcuts import render
from products.models import Product
from django.http import HttpResponse
import logging


# Create your views here.
logger = logging.getLogger(__name__)


def get_products(request, slug):
    try:
        product = Product.objects.get(slug=slug)
        print("reached here")
        available_variants = product.size_variants.filter(stock__gt=0)

        # Prepare variants with dynamic pricing
        variants_with_prices = []
        for variant in available_variants:
            # Calculate original and discounted prices
            original_price = variant.price
            discounted_price = product.get_discounted_price(original_price)
            
            variants_with_prices.append({
                'size_name': variant.size_name,
                'original_price': original_price,
                'discounted_price': discounted_price,
                'stock': variant.stock,
                'has_discount': original_price != discounted_price
            })

        # Select the first available variant for default display
        default_variant = variants_with_prices[0] if variants_with_prices else None

        return render(request, 'products/products.html', {
            'product': product,
            'available_variants': variants_with_prices,
            'default_variant': default_variant,
            'max_stock': product.size_variants.first().stock if product.size_variants.exists() else 0,
        })
    except Product.DoesNotExist:
        logger.error(f"Product with slug '{slug}' does not exist.")
        return HttpResponse("Product not found.", status=404)
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        return HttpResponse("An error occurred while processing your request.", status=500)