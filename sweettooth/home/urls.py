from django.urls import path
from home.views import *

urlpatterns = [
    path('', index, name='index'),
    path('shop/', shop, name='shop'),
    path('user/<slug:slug>/', user_details, name='user_details'),
    path('update_profile/', update_profile, name='update_profile'),
    path('order_details/<int:order_id>/', order_details, name='order_details'),
    path('add_address/', add_address, name='add_address'),
    path('cancel_order/<int:order_id>/', cancel_order, name='cancel_order'),
    path('download_invoice/<int:order_id>/', download_invoice, name='download_invoice'),
]