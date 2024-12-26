from django.db import models
from django.contrib.auth.models import User
from base.models import BaseModel
from django.db.models.signals import post_save
from django.dispatch import receiver
import uuid
from base.emails import send_account_activation_email
from django.utils.text import slugify


class Profile(BaseModel):
    user = models.OneToOneField(User, on_delete = models.CASCADE, related_name = "profile")
    is_email_verified = models.BooleanField(default = False)
    email_token = models.CharField(max_length = 100, null = True, blank = True)
    phone_number = models.CharField(max_length=10)
    slug = models.SlugField(unique=True, blank=True, null=True)
    
    def full_name(self):
        return f"{self.user.first_name} {self.user.last_name}"
    
    def save(self, *args, **kwargs):
        # Generate slug from full_name if slug is not set
        if not self.slug:
            self.slug = slugify(self.full_name())
        
        # Call the parent class's save method
        super(Profile, self).save(*args, **kwargs)
        
    def __str__(self):
        return self.full_name()
        
    
    
class Address(models.Model):
    uid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="addresses")
    house_no = models.CharField(max_length=100)
    street = models.CharField(max_length=255)
    post_office = models.CharField(max_length=255)
    district = models.CharField(max_length=255)
    state = models.CharField(max_length=255)
    country = models.CharField(max_length=255)
    pin_code = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.house_no}, {self.street}, {self.district}, {self.state} - {self.pin_code}"


@receiver(post_save, sender = User)
def send_email_token(sender, instance, created, **kwargs):
    try:
        if created:
            email_token = str(uuid.uuid4())
            Profile.objects.create(user = instance, email_token = email_token )
            email = instance.email
            send_account_activation_email(email, email_token)
            

    except Exception as e:
        print(e)