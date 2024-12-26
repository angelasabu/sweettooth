from django.urls import path
from .views import *


urlpatterns = [
    path('login/', login_page, name='login'),
    path('logout/', user_logout, name='logout'),
    path('signup/', signup_page, name='signup'),
    path('forgot_password/', forgot_password, name='forgot_password'),
    path('activate/<email_token>', activate_email, name='activate_email'),
    path('verify_otp/', verify_otp, name='verify_otp'),
    path('change_password/', change_password, name='change_password'),
]
