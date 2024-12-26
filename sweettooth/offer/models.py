from django.db import models
from django.utils.timezone import now
from products.models import *
from accounts.models import *

# Create your models here.



class CategoryOffer(models.Model):
    category = models.OneToOneField(Category, on_delete=models.CASCADE)
    percentage = models.FloatField()
    expiry_date = models.DateField()
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Category Offer"
        verbose_name_plural = "Category Offers"

    def __str__(self):
        return f"{self.category.category_name} - {self.percentage}% Offer"
    
    
    
class ProductOffer(models.Model):
    product = models.OneToOneField(Product, on_delete=models.CASCADE)
    percentage = models.FloatField()
    expiry_date = models.DateField()
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Product Offer"
        verbose_name_plural = "Product Offers"

    def __str__(self):
        return f"{self.product.product_name} - {self.percentage}% Offer"
    
    
class ReferralOffer(models.Model):
    user = models.OneToOneField(Profile, on_delete=models.CASCADE, related_name="referral_offer")
    referral_code = models.CharField(max_length=12, unique=True)
    referred_by = models.ForeignKey(Profile, on_delete=models.SET_NULL, null=True, blank=True, related_name="referrals")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.user.first_name}'s Referral Code: {self.referral_code}"

    @staticmethod
    def generate_referral_code():
        return str(uuid.uuid4())[:12].upper()