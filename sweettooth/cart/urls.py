from django.urls import path
from .views import *


urlpatterns = [
    path('', cart, name='cart'),
    path('add_cart/<str:uid>/', add_cart, name='add_cart'),
    path('update_quantity/', update_cart_quantity, name='update_cart_quantity'),
    path('remove/<int:cart_item_id>/', remove_cart_item, name='remove_cart_item'),
    path('checkout/<slug:slug>/', checkout, name='checkout'),
    path('paymenthandler/', paymenthandler, name='paymenthandler'),
    path('add_wishlist/<str:uid>/', add_wishlist, name='add_wishlist'),
    path('wishlist/', wishlist, name='wishlist'),
    path('delete_wishlist_item/<int:item_id>/', delete_wishlist_item, name='delete_wishlist_item'),
    path('retry_payment/<int:order_id>/', retry_payment, name='retry_payment'),
]