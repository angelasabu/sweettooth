from django.db import models
from base.models import BaseModel
from products.models import *
from accounts.models import *
from django.utils import timezone
from django.core.exceptions import ValidationError

# Create your models here.
class Cart(models.Model):
    profile = models.OneToOneField(Profile, on_delete=models.CASCADE, related_name="cart")
    cart_id = models.CharField(max_length=250, blank=True)
    date_added = models.DateField(auto_now_add=True)
    
    
    def __str__(self):
        return f"Cart for {self.profile.user.first_name}"
    
    
class CartItem(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    is_active = models.BooleanField(default=True)
    size_variant = models.ForeignKey(SizeVariant, on_delete=models.CASCADE, null=True, blank=True, related_name='cart_items')
    total = models.PositiveIntegerField(default=0, blank=True, null=True)

    def __str__(self):
        return str(self.product)
    
        
    def save(self, *args, **kwargs):
        if self.size_variant:
            self.total = self.quantity * self.size_variant.price
        if self.quantity > self.size_variant.stock:
                raise ValidationError(f"Cannot add more than {self.size_variant.stock} items of this size to the cart.")
            
        super().save(*args, **kwargs)
        
        

class Coupon(models.Model):
    coupon_code = models.CharField(max_length=20, unique=True, verbose_name="Coupon Code")
    percentage = models.DecimalField(max_digits=5, decimal_places=2)
    limit = models.DecimalField(max_digits=10, decimal_places=2)
    total_coupons = models.PositiveIntegerField()
    expiry_date = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    
    def __str__(self):
        return f"{self.coupon_code} - {self.percentage}% off"
    
    
    def is_expired(self):
        return timezone.now() > self.expiry_date

    
    
    def can_use(self):
        return self.is_active and not self.is_expired()
    
    
    def apply_discount(self, total):
        if total >= self.limit and self.can_use():
            discount_amount = total * (self.percentage / 100)
            return total - discount_amount
        
        return total
    
    
    

class Wishlist(models.Model):
    profile = models.OneToOneField(Profile, on_delete=models.CASCADE, related_name="wishlist")
    date_added = models.DateField(auto_now_add=True)
    
    
    def __str__(self): 
        return str(self.profile)

    def get_items(self):
        return self.wishlistitem_set.filter(is_active=True)
   

class WishlistItem(models.Model):
    wishlist = models.ForeignKey(Wishlist, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    size_variant = models.ForeignKey(SizeVariant, on_delete=models.CASCADE, null=True, blank=True, related_name='wishlist_items')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    
    def __str__(self):
        return str(self.product)
    