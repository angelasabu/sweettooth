from django.shortcuts import render, redirect
from django.shortcuts import render, redirect, get_object_or_404
from accounts.models import *
from products.models import *
from cart.models import *
from django.http import JsonResponse
from .models import *
from django.views.decorators.csrf import csrf_exempt
import json
from django.db import transaction
from accounts.utils import user_login_required
from django.contrib.auth.decorators import login_required


# Create your views here.

@login_required(login_url='login')
def create_order(request):
    if request.method == 'POST' and request.user.is_authenticated:
        data = json.loads(request.body)
        
        profile = request.user.profile
        cart = profile.cart
        cart_items = CartItem.objects.filter(cart=cart, is_active=True)

        if not cart_items.exists():
            return JsonResponse({'success': False, 'message': 'Cart is empty.'})

        final_total = request.session.get('final_total', 0)
        applied_coupon_code = request.session.get('applied_coupon_code', None)

        selected_address_id = data['selected_address']
        selected_address = Address.objects.get(id=selected_address_id)

        for item in cart_items:
            if item.size_variant.stock < item.quantity:
                return JsonResponse({
                    'success': False,
                    'message': f"Not enough stock for {item.product.product_name} ({item.size_variant.size_name}). Available stock: {item.size_variant.stock}"
                })

        with transaction.atomic():
            order = Order.objects.create(
                profile=profile,
                total_amount=final_total,
                applied_coupon=applied_coupon_code if applied_coupon_code else "",
                payment_method=data['payment_method'],
                order_note=data.get('order_note', ''),
                shipping_address=f"{selected_address.house_no}, {selected_address.street}, {selected_address.post_office}, {selected_address.district}, {selected_address.state}, {selected_address.country} - {selected_address.pin_code}",
                is_paid=False
            )

            for item in cart_items:
                OrderItem.objects.create(
                    product=item.product,
                    order=order,
                    product_name=item.product.product_name,
                    quantity=item.quantity,
                    price=item.size_variant.price
                )

                item.size_variant.stock -= item.quantity
                item.size_variant.save()

            cart_items.delete()

        return JsonResponse({'success': True})
    return JsonResponse({'success': False, 'message': 'Invalid request.'})


@login_required(login_url='login')
def order_success(request):
    return render(request, 'cart/order_success.html')


@login_required(login_url='login')
def wallet_order(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        profile = request.user.profile
        wallet = Wallet.objects.get(profile=profile)
        cart = Cart.objects.get(profile=request.user.profile)
        cart_items = CartItem.objects.filter(cart=cart, is_active=True)

        if not cart_items.exists():
            return JsonResponse({'success': False, 'message': 'Cart is empty.'})

        final_total = request.session.get('final_total', 0)
        applied_coupon_code = request.session.get('applied_coupon_code', None)

        selected_address_id = data['selected_address']
        selected_address = Address.objects.get(id=selected_address_id)
        
        total_amount = 0
        for item in cart_items:
            total_amount += item.total
            if item.size_variant.stock < item.quantity:
                return JsonResponse({
                    'success': False,
                    'message': f"Not enough stock for {item.product.product_name} ({item.size_variant.size_name}). Available stock: {item.size_variant.stock}"
                })
                
        if wallet.amount < total_amount:
            return JsonResponse({
                    'success': False,
                    'message': "Insufficient balance"
                })

        with transaction.atomic():
            order = Order.objects.create(
                profile=profile,
                total_amount=final_total,
                applied_coupon=applied_coupon_code if applied_coupon_code else "",
                payment_method=data['payment_method'],
                order_note=data.get('order_note', ''),
                shipping_address=f"{selected_address.house_no}, {selected_address.street}, {selected_address.post_office}, {selected_address.district}, {selected_address.state}, {selected_address.country} - {selected_address.pin_code}",
                is_paid=False
            )

            for item in cart_items:
                OrderItem.objects.create(
                    order=order,
                    product_name=item.product.product_name,
                    quantity=item.quantity,
                    price=item.size_variant.price
                )

                item.size_variant.stock -= item.quantity
                item.size_variant.save()

            cart_items.delete()
            wallet.amount -= total_amount
            wallet.save()
            
            Transaction.objects.create(
                    wallet=wallet,
                    amount=order.total_amount,
                    transaction_type='debit',
                )
            return JsonResponse({'success': True})
    return JsonResponse({'success': False, 'message': 'Invalid request.'})