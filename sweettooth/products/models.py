from django.utils import timezone
from django.db import models
from base.models import BaseModel
from django.utils.text import slugify
from PIL import Image
from django.core.validators import MinValueValidator

class Category(BaseModel):
    category_name = models.CharField(max_length = 100)
    slug = models.SlugField(unique = True, null = True, blank = True)
    category_image = models.ImageField(upload_to = "categories")
    is_active = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        self.slug = slugify(self.category_name)
        super(Category, self).save(*args, **kwargs)

    def __str__(self) -> str:
        return self.category_name
    


class Product(BaseModel):
    product_name = models.CharField(max_length = 100)
    slug = models.SlugField(unique = True, null = True, blank = True)
    category = models.ForeignKey(Category, on_delete = models.CASCADE, related_name = "products")
    product_description = models.TextField()
    is_active = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        self.slug = slugify(self.product_name)
        super(Product, self).save(*args, **kwargs)

    def __str__(self) -> str:
        return self.product_name
    
    
    def get_discounted_price(self, original_price):
        # Check if the category has an active offer
        if hasattr(self.category, 'categoryoffer') and self.category.categoryoffer.is_active:
            category_offer = self.category.categoryoffer
            if category_offer.expiry_date >= timezone.now().date():
                # Apply the discount
                discount = (category_offer.percentage / 100) * original_price
                return max(original_price - discount, 0)  # Ensure price does not go below 0
        return original_price


class ProductImage(BaseModel):
    product = models.ForeignKey(Product, on_delete = models.CASCADE, related_name = "product_images")
    image = models.ImageField(upload_to = "product")
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        img = Image.open(self.image.path)

        target_width = 600
        target_height = 750

        width, height = img.size
        aspect_ratio = width / height

        # Calculate the cropping box
        if width / height > target_width / target_height:
            # Image is wider than the target aspect ratio
            new_width = int(height * (target_width / target_height))
            left = (width - new_width) / 2
            top = 0
            right = left + new_width
            bottom = height
        else:
            # Image is taller than the target aspect ratio
            new_height = int(width * (target_height / target_width))
            left = 0
            top = (height - new_height) / 2
            right = width
            bottom = top + new_height

        # Crop the image
        img = img.crop((left, top, right, bottom))

        # Resize the image to the target dimensions
        img = img.resize((target_width, target_height), Image.BICUBIC)

        # Save the cropped and resized image back to the same path
        img.save(self.image.path)
        
        
class SizeVariant(BaseModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='size_variants', default=None)
    size_name = models.CharField(max_length=100)
    price = models.PositiveIntegerField(validators=[MinValueValidator(0)], default=None)
    stock = models.PositiveIntegerField(validators=[MinValueValidator(0)], default=None)
    
    class Meta:
        unique_together = ['product', 'size_name']  # Ensure no duplicate sizes for the same product
    
    
    def __str__(self) -> str:
        return self.size_name
