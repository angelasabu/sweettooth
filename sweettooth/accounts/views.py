import random
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.models import User
from accounts.models import Profile
from django.contrib.auth import authenticate, login, logout
from django.http import HttpResponseRedirect, HttpResponse
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
import re
from home.views import index
from django.core.cache import cache
from django.views.decorators.cache import cache_control
from django.core.mail import send_mail
from django.contrib.auth.tokens import default_token_generator
from django.conf import settings
from .utils import user_login_required
from decimal import Decimal
from offer.models import *
from orders.models import *




# Create your views here




@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def login_page(request):
    user_id = request.session.get('user_id')  # Use get method to avoid KeyError
    if user_id is not None:
        return redirect('/')
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        user_obj = User.objects.filter(username = email)

        if not user_obj.exists():
            messages.warning(request, 'Account not found')
            return HttpResponseRedirect(request.path_info)

        if not user_obj[0].profile.is_email_verified:
            messages.warning(request, 'Your account is not verified.')
            return HttpResponseRedirect(request.path_info)

        user_obj = authenticate(username = email, password = password)
        if user_obj:
            request.session['user_id'] = user_obj.id
            login(request, user_obj)
            return redirect('/')

        messages.warning(request, 'Invalid credentials.')
        return HttpResponseRedirect(request.path_info)

    return render(request, 'accounts/login.html')


@user_login_required
def user_logout(request):
    logout(request)
    delete_user_id = request.session.pop('user_id', None)
    request.session.flush()
    return redirect('login')




REFERRAL_AMOUNT = Decimal('100.00')  # Amount to be credited for referrals

def signup_page(request):
    if request.method == 'POST':
        first_name = request.POST.get('first_name').strip()
        last_name = request.POST.get('last_name').strip()
        email = request.POST.get('email').strip()
        phone_number = request.POST.get('phone_number').strip()
        password = request.POST.get('password').strip()
        confirm_password = request.POST.get('confirm_password').strip()
        referral_code = request.POST.get('referral_code', '').strip()

        # Validation logic (as in your existing function)

        # Create the user
        user_obj = User.objects.create(first_name=first_name, last_name=last_name, email=email, username=email)
        user_obj.set_password(password)
        user_obj.save()
        profile = Profile.objects.get(user=user_obj)
        profile.phone_number = phone_number
        profile.save()

        # Create Wallet for the new user
        wallet = Wallet.objects.create(profile=profile)

        # Generate and save referral code for the new user
        referral_offer = ReferralOffer.objects.create(
            user=profile,
            referral_code=ReferralOffer.generate_referral_code()
        )

        # Check if a valid referral code was provided
        if referral_code:
            try:
                referrer_offer = ReferralOffer.objects.get(referral_code=referral_code)
                referrer_profile = referrer_offer.user

                # Credit wallets of both referrer and new user
                referrer_wallet = referrer_profile.wallet
                new_user_wallet = wallet

                referrer_wallet.amount = Decimal(referrer_wallet.amount) + Decimal('100.00')
                referrer_wallet.save()

                new_user_wallet.amount = Decimal(new_user_wallet.amount) + Decimal('100.00')
                new_user_wallet.save()

                # Create transactions for both users
                Transaction.objects.create(
                    wallet=referrer_wallet,
                    amount=REFERRAL_AMOUNT,
                    transaction_type='credit'
                )
                Transaction.objects.create(
                    wallet=new_user_wallet,
                    amount=REFERRAL_AMOUNT,
                    transaction_type='credit'
                )

                # Link the new user to the referrer
                referral_offer.referred_by = referrer_profile
                referral_offer.save()

                messages.success(request, 'Referral bonus credited!')

            except ReferralOffer.DoesNotExist:
                messages.warning(request, 'Invalid referral code.')

        messages.success(request, 'Your account has been created successfully.')
        return HttpResponseRedirect(request.path_info)

    return render(request, 'accounts/signup.html')



def activate_email(request, email_token):
    try:
        user = Profile.objects.get(email_token = email_token)
        user.is_email_verified = True
        user.save()
        return redirect('/')
    except Exception as e:
        return HttpResponse('Invalid Email token')
    

def forgot_password(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        
        try:
            validate_email(email)
        except ValidationError:
            messages.warning(request, 'Please enter a valid email address.')
            return HttpResponseRedirect(request.path_info)
        
        user_obj = User.objects.filter(username = email)
        if not user_obj.exists():
            messages.warning(request, 'Account not found')
            return HttpResponseRedirect(request.path_info)
        if user_obj:
            user = user_obj.first()
            otp = random.randint(100000, 999999)
            
            request.session['otp'] = otp
            request.session['otp_email'] = email
            
            
            subject = 'Your Password Reset OTP'
            message = f'Your OTP for resetting your password is: {otp}.'
            try:
                
                send_mail(
                    subject,
                    message,
                    settings.EMAIL_HOST_USER,  # Replace with your email address
                    [email],
                    fail_silently=False
                )
                
                messages.success(request, 'We have sent you an OTP to reset your password. Please check your email.')
                return redirect('verify_otp')
                
            except Exception as e:
                messages.warning(request, 'Please enter a valid email.')
                return HttpResponseRedirect(request.path_info)            
            
        
    return render(request, 'accounts/forgot_password.html')

def verify_otp(request) :
    if request.method == 'POST':
        entered_otp = request.POST.get('otp')
        otp = request.session.get('otp')
        if int(entered_otp) == otp:
            return redirect('change_password')
        else:
            messages.warning(request, 'Invalid OTP.')
            return HttpResponseRedirect(request.path_info)
    return render(request,'accounts/verify_otp.html')


def change_password(request):
    if request.method == 'POST':
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        if new_password == confirm_password:
            user_email = request.session.get('otp_email')
            print("User Emaill", user_email)
            user = User.objects.filter(username=user_email).first()
            print(user, 'user')
            user.set_password(new_password)
            user.save()
            return redirect('login')
        else:
            messages.warning(request, 'Password Not Matching')
    return render(request,'accounts/change_password.html')