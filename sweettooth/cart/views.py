from django.shortcuts import render, redirect, get_object_or_404
from products.models import *
from .models import *
from accounts.models import *
from offer.models import *
from django.http import HttpResponse
from django.core.exceptions import ObjectDoesNotExist
from django.contrib import messages
from django.http import JsonResponse
import json
from django.views.decorators.http import require_POST
from django.utils import timezone
import razorpay
from django.conf import settings
from django.http import HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from orders.models import Order, OrderItem
from django.core.cache import cache
from decimal import Decimal
from accounts.utils import user_login_required
from django.contrib.auth.decorators import login_required

razorpay_client = razorpay.Client(
    auth=(settings.RAZOR_KEY_ID, settings.RAZOR_KEY_SECRET))



# Create your views here.

def _cart_id(request):
    session_key = request.session.session_key
    cart = Cart.objects.get(profile=request.user.profile)
    print(cart, 'lld')
    if not session_key:
        request.session.create()
    return cart


@login_required(login_url='login')
def add_cart(request, uid):
    if request.method == "POST":
        size_name = request.POST.get("size_name")
        qty = int(request.POST.get("qtybutton", 1))
        
        print(size_name, qty, 'dataaaa')

        product = get_object_or_404(Product, uid=uid)
        available_variants = product.size_variants.filter(stock__gt=0)
        
        if not size_name and available_variants.exists():
            size_variant = available_variants.first()
            size_name = size_variant.size_name
        else:
            size_variant = get_object_or_404(SizeVariant, product=product, size_name=size_name)

        profile = request.user.profile
        cart, created = Cart.objects.get_or_create(profile=profile)
        
        try:
            cart_item, item_created = CartItem.objects.get_or_create(
                product=product,
                cart=cart,
                size_variant=size_variant,
                defaults={'quantity': qty}
            )

            if not item_created:
                cart_item.quantity += qty
                cart_item.save()
        except ValidationError as e:
            messages.error(request, e.message)

    print(f"CartItem created: {cart_item.id}")

    return redirect('cart')



@login_required(login_url='login')
def cart(request):
    discount = Decimal('0.0')
    final_total = Decimal('0.0')
    applied_coupon_code = None
    item_count = 0
    subtotal = Decimal('0.0')  # Ensure it's defined before calculations

    try:
        cart = request.user.profile.cart
        cart_items = CartItem.objects.filter(cart=cart, is_active=True)

        processed_cart_items = []  # To store cart items with calculated prices

        for item in cart_items:
            # Check for category offer
            category_offer = getattr(item.product.category.categoryoffer, 'percentage', None)
            if category_offer and item.product.category.categoryoffer.is_active:
                discounted_price = Decimal(item.size_variant.price) * (1 - Decimal(category_offer) / 100)
            else:
                discounted_price = Decimal(item.size_variant.price)

            # Update subtotal
            subtotal += discounted_price * item.quantity

            # Add processed data for template rendering
            processed_cart_items.append({
                'cart_item': item,
                'price': round(discounted_price, 2),  # Rounded to two decimal places
                'total': round(discounted_price * item.quantity, 2),
            })

        item_count = sum(item['cart_item'].quantity for item in processed_cart_items)
        active_coupons = Coupon.objects.filter(is_active=True, expiry_date__gt=timezone.now())

        if request.method == "POST":
            coupon_code = request.POST.get('coupon_code')
            remove_coupon = request.POST.get('remove_coupon')
            if remove_coupon:
                print('hiii, lfmlf')
            try:
                coupon = active_coupons.get(coupon_code=coupon_code)
                if subtotal >= coupon.limit:
                    final_total = coupon.apply_discount(subtotal)
                    discount = subtotal - final_total
                    applied_coupon_code = coupon_code
                else:
                    return JsonResponse({
                        'success': False,
                        'message': f"Subtotal must be at least {coupon.limit} to use this coupon."
                    })
            except Coupon.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'message': "Invalid or expired coupon code."
                })
        else:
            final_total = subtotal

        request.session['final_total'] = float(final_total)
        request.session['subtotal'] = float(subtotal)
        request.session['applied_coupon_code'] = applied_coupon_code

    except ObjectDoesNotExist:
        processed_cart_items = []
        active_coupons = []
    print(f"subtotal{ subtotal},discount{ discount},final_total: {final_total},cart_items:{ processed_cart_items},active_coupons: {active_coupons}applied_coupon_code: {applied_coupon_code},item_count: {item_count},")

    context = {
        'subtotal': subtotal,
        'discount': discount,
        'final_total': final_total,
        'cart_items': processed_cart_items,
        'active_coupons': active_coupons,
        'applied_coupon_code': applied_coupon_code,
        'item_count': item_count,
    }
    return render(request, 'cart/cart.html', context)




@login_required(login_url='login')
def update_cart_quantity(request):
    if request.method == "POST":
        data = json.loads(request.body)
        action = data.get("action")
        cart_item_id = data.get("cart_item_id")

        try:
            cart_item = CartItem.objects.get(id=cart_item_id)

            # Update quantity based on action
            if action == "increment":
                if cart_item.quantity == cart_item.size_variant.stock:
                    return JsonResponse({"success": False, "error": "Stock limit reached"})
                cart_item.quantity += 1
            elif action == "decrement" and cart_item.quantity > 1:
                cart_item.quantity -= 1
            else:
                return JsonResponse({"success": False, "error": "Invalid action or quantity cannot be less than 1"})

            cart_item.save()

            # Calculate item total considering category offer
            category_offer = getattr(cart_item.product.category.categoryoffer, 'percentage', None)
            if category_offer and cart_item.product.category.categoryoffer.is_active:
                item_price = cart_item.size_variant.price * (1 - category_offer / 100)
            else:
                item_price = cart_item.size_variant.price

            item_total = round(cart_item.quantity * item_price, 2)

            # Calculate cart totals
            cart_items = cart_item.cart.cartitem_set.all()
            subtotal = sum(
                (item.size_variant.price * (1 - getattr(item.product.category.categoryoffer, 'percentage', 0) / 100)
                 if getattr(item.product.category.categoryoffer, 'is_active', False) else item.size_variant.price) * item.quantity
                for item in cart_items
            )

            discount = 0
            final_total = subtotal

            # Apply coupon if provided
            coupon_code = data.get("coupon_code", None)
            if coupon_code:
                try:
                    coupon = Coupon.objects.get(
                        coupon_code=coupon_code,
                        is_active=True,
                        expiry_date__gt=timezone.now()
                    )
                    if subtotal >= coupon.limit:
                        discount = subtotal * (coupon.percentage / 100)
                        final_total = subtotal - discount
                except Coupon.DoesNotExist:
                    pass
                
            request.session['final_total'] = float(final_total)
            request.session['subtotal'] = float(subtotal)

            return JsonResponse({
                "success": True,
                "quantity": cart_item.quantity,
                "item_total": item_total,
                "cart_total": subtotal,
                "discount": discount,
                "final_total": final_total,
            })
        except CartItem.DoesNotExist:
            return JsonResponse({"success": False, "error": "Cart item not found"})

    return JsonResponse({"success": False, "error": "Invalid request"})




@login_required(login_url='login')
@require_POST
def remove_cart_item(request, cart_item_id):
    if request.user.is_authenticated:
        cart_item = get_object_or_404(CartItem, id=cart_item_id, cart__profile=request.user.profile)
        cart_item.delete()

        # Recalculate totals after item removal
        cart_items = request.user.profile.cart.cartitem_set.all()
        subtotal = sum(
            (item.size_variant.price * (1 - getattr(item.product.category.categoryoffer, 'percentage', 0) / 100)
             if getattr(item.product.category.categoryoffer, 'is_active', False) else item.size_variant.price) * item.quantity
            for item in cart_items
        )

        return JsonResponse({
            "success": True,
            "cart_total": subtotal,
        })
    else:
        return JsonResponse({"success": False, "error": "Authentication required"}, status=403)

    


@login_required(login_url='login')
def update_cart_icon_quantity(request):
    cart_item_id = request.POST.get('cart_item_id')
    quantity = int(request.POST.get('quantity'))

    cart_item = get_object_or_404(CartItem, id=cart_item_id)
    cart_item.quantity = quantity
    cart_item.save()

    # Calculate updated cart totals
    cart_items = request.user.profile.cart.cartitem_set.all()
    subtotal = sum(
        (item.size_variant.price * (1 - getattr(item.product.category.categoryoffer, 'percentage', 0) / 100)
         if getattr(item.product.category.categoryoffer, 'is_active', False) else item.size_variant.price) * item.quantity
        for item in cart_items
    )

    # Calculate new item count
    item_count = sum(item.quantity for item in cart_items)

    return JsonResponse({
        'success': True,
        'new_item_count': item_count,
        'cart_total': subtotal,
    })



@login_required(login_url='login')
def checkout(request, slug):
    profile = get_object_or_404(Profile, slug=slug)
    cart = request.user.profile.cart
    cart_items = CartItem.objects.filter(cart=cart, is_active=True)

    # Retrieve values from the session
    subtotal = request.session.get('subtotal', 0)
    discount = request.session.get('subtotal', 0) - request.session.get('final_total', 0)  # Calculate discount from session
    final_total = request.session.get('final_total', 0)
    applied_coupon_code = request.session.get('applied_coupon_code', None)

    processed_cart_items = []
    for item in cart_items:
        # Recalculate individual cart item prices based on updated values
        category_offer = getattr(item.product.category.categoryoffer, 'percentage', None)
        if category_offer and item.product.category.categoryoffer.is_active:
            discounted_price = item.size_variant.price * (1 - category_offer / 100)
        else:
            discounted_price = item.size_variant.price

        processed_cart_items.append({
            'cart_item': item,
            'price': round(discounted_price, 2),
            'total': round(discounted_price * item.quantity, 2),
        })

    currency = 'INR'
    amount = final_total * 100  # Convert to paisa for Razorpay

    # Create a Razorpay Order
    razorpay_order = razorpay_client.order.create(
        dict(
            amount=amount,
            currency=currency,
            payment_capture='0',
            notes={
                'profile_id': str(profile.uid),
                'applied_coupon_code': applied_coupon_code,
                'final_total': str(amount),
            }
        )
    )
    
    cache.set('profile_id', profile.uid)
    cache.set('final_total', final_total)

    # order id of the newly created order
    razorpay_order_id = razorpay_order['id']
    callback_url = f'{settings.BASE_APP_URL}/cart/paymenthandler/'

    context = {
        'profile': profile,
        'cart': cart,
        'cart_items': processed_cart_items,  # Updated processed cart items
        'subtotal': subtotal,
        'discount': discount,
        'final_total': final_total,
        'applied_coupon_code': applied_coupon_code,
        'razorpay_order_id': razorpay_order_id,
        'razorpay_merchant_key': settings.RAZOR_KEY_ID,
        'razorpay_amount': amount,
        'currency': currency,
        'callback_url': callback_url,
        'slug': slug
    }

    if request.method == 'POST':
        data = json.loads(request.body)
        if 'selected_address' in data:
            datas = {'selected_address': data['selected_address']}
            serialized_data = json.dumps(datas)
            cache.set('data', serialized_data)
            return JsonResponse({'success': 'success'})

    return render(request, 'cart/checkout.html', context)




@csrf_exempt
def paymenthandler(request):
    # only accept POST request.
    if request.method == "POST":
        try:
            # Extract data
            
            serialized_data = cache.get('data')
            data = json.loads(serialized_data)
            
            
            payment_id = request.POST.get('razorpay_payment_id', '')
            razorpay_order_id = request.POST.get('razorpay_order_id', '')
            signature = request.POST.get('razorpay_signature', '')
            order_details = razorpay_client.order.fetch(razorpay_order_id)
            notes = order_details.get('notes', {})
            profile_id = cache.get('profile_id')
            print(profile_id, 'notes', )
            try:
                profile = Profile.objects.get(uid = profile_id)
            except Profile.DoesNotExist:
                return HttpResponseBadRequest("Profile not found.")
            
            params_dict = {
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': payment_id,
                'razorpay_signature': signature,
            }
            print("Received:", payment_id, razorpay_order_id, signature)

            
            try:
                result = razorpay_client.utility.verify_payment_signature(params_dict)
                if result:
                    print("Signature verified successfully")
                else:
                    print("Signature verification failed")
                if result is not None:
                    amount = int(float(notes['final_total']))
                    final_total = amount/100
                    print(result, 'result')

                    # capture the payemt
                    capture_response = razorpay_client.payment.capture(payment_id, amount)
                    
                    cart = profile.cart
                    cart_items = CartItem.objects.filter(cart=cart, is_active=True)

                    if not cart_items.exists():
                        return JsonResponse({'success': False, 'message': 'Cart is empty.'})

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
                            profile = profile,
                            total_amount = final_total,
                            applied_coupon = applied_coupon_code if applied_coupon_code else "",
                            payment_method = 'Razorpay',
                            shipping_address = f"{selected_address.house_no}, {selected_address.street}, {selected_address.post_office}, {selected_address.district}, {selected_address.state}, {selected_address.country} - {selected_address.pin_code}",
                            is_paid = True,
                            razorpay_payment_id = params_dict.get('razorpay_payment_id'),
                            razorpay_order_id = params_dict.get('razorpay_order_id'),
                            razorpay_signature = params_dict.get('razorpay_signature')
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

                    # render success page on successful caputre of payment
                    return render(request, 'cart/order_success.html')
            except Exception as e:
                final_total = cache.get('final_total')
                cart = profile.cart
                cart_items = CartItem.objects.filter(cart=cart, is_active=True)

                if not cart_items.exists():
                    return JsonResponse({'success': False, 'message': 'Cart is empty.'})

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
                        profile = profile,
                        total_amount = final_total,
                        applied_coupon = applied_coupon_code if applied_coupon_code else "",
                        payment_method = 'Razorpay',
                        shipping_address = f"{selected_address.house_no}, {selected_address.street}, {selected_address.post_office}, {selected_address.district}, {selected_address.state}, {selected_address.country} - {selected_address.pin_code}",
                        is_paid = False,
                        razorpay_payment_id = params_dict.get('razorpay_payment_id'),
                        razorpay_order_id = params_dict.get('razorpay_order_id'),
                        razorpay_signature = params_dict.get('razorpay_signature')
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

                # if there is an error while capturing payment.
                return render(request, 'cart/paymentfail.html', context={'order_id':order.id})
            else:

                # if signature verification fails.
                return render(request, 'cart/paymentfail.html')
        except Exception as e:
            print("Error:", e)
            return HttpResponseBadRequest("An error occurred")
    else:
       # if other than POST request is made.
        return HttpResponseBadRequest()
    
    
@login_required(login_url='login')
def add_wishlist(request, uid):
    if request.method == "POST":
        
        data = json.loads(request.body)
        size_name = data.get("wishlist_size_name")
        
        print(size_name, 'kkk')

        # Fetch the product by UID
        product = get_object_or_404(Product, uid=uid)

        # Handle size variant selection
        available_variants = product.size_variants.filter(stock__gt=0)
        
        if not size_name and available_variants.exists():
            size_variant = available_variants.first()
            size_name = size_variant.size_name
        else:
            size_variant = get_object_or_404(SizeVariant, product=product, size_name=size_name)
            

        # Get or create the user's wishlist
        profile = request.user.profile
        wishlist, created = Wishlist.objects.get_or_create(profile=profile)

        # Add item to the wishlist
        wishlist_item, item_created = WishlistItem.objects.get_or_create(
            wishlist=wishlist,
            product=product,
            size_variant=size_variant,
            defaults={'is_active': True}
        )

        # Handle messages based on item creation status
        if not item_created:
            if wishlist_item.is_active:
                messages.info(request, "Item is already in your wishlist.")
            else:
                wishlist_item.is_active = True
                wishlist_item.save()
                messages.success(request, "Item was reactivated in your wishlist.")
        else:
            messages.success(request, "Item added to your wishlist.")
            
    return JsonResponse({'success':True})



@login_required(login_url='login')
def wishlist(request):
    profile = request.user.profile
    wishlist, created = Wishlist.objects.get_or_create(profile=profile)

    # Fetch all active wishlist items for the user
    wishlist_items = wishlist.get_items().select_related('product', 'size_variant')

    # Process wishlist items with discount price and stock details
    processed_wishlist_items = []
    for wishlist_item in wishlist_items:
        product = wishlist_item.product
        size_variant = wishlist_item.size_variant
        
        # Calculate original and discounted prices
        if size_variant:
            original_price = size_variant.price
            discounted_price = product.get_discounted_price(original_price)
            stock = size_variant.stock
        else:
            original_price = product.price
            discounted_price = product.get_discounted_price(original_price)
            stock = 0  # Default stock to 0 if no size variant exists

        processed_wishlist_items.append({
            'id': wishlist_item.id,
            'product': product,
            'size_variant': size_variant,
            'original_price': round(Decimal(original_price), 2),
            'discounted_price': round(Decimal(discounted_price), 2),
            'stock': stock,
            'has_discount': original_price != discounted_price,
        })

    context = {
        'wishlist_items': processed_wishlist_items
    }
    return render(request, 'cart/wishlist.html', context)




@login_required(login_url='login')
def delete_wishlist_item(request, item_id):
    print('lll')
    if request.method == "POST" and request.user.is_authenticated:
        print('kkkk', item_id)
        try:
            wishlist_item = get_object_or_404(
                WishlistItem, id=item_id, wishlist__profile=request.user.profile
            )
            wishlist_item.delete()
            return JsonResponse({"success": True})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})

    return JsonResponse({"success": False, "error": "Invalid request or not authenticated"})





@csrf_exempt
def retry_payment(request, order_id):
    if request.method == "POST":
        try:
            # Fetch the existing order
            order = Order.objects.get(id=order_id, is_paid=False)
        except Order.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Order not found or already paid.'})

        try:
            # Extract Razorpay details from the POST request
            payment_id = request.POST.get('razorpay_payment_id', '')
            razorpay_order_id = request.POST.get('razorpay_order_id', '')
            signature = request.POST.get('razorpay_signature', '')

            # Verify payment details
            params_dict = {
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': payment_id,
                'razorpay_signature': signature,
            }
            result = razorpay_client.utility.verify_payment_signature(params_dict)

            if result:
                # Capture the payment
                amount = int(float(order.total_amount) * 100)  # Convert to paise
                capture_response = razorpay_client.payment.capture(payment_id, amount)

                # Update the order status
                order.is_paid = True
                order.save()

                return render(request, 'cart/order_success.html', {'order': order})
            else:
                # Payment verification failed
                return render(request, 'cart/paymentfail.html', context={'order_id':order.id})
        except Exception as e:
            print("Error during retry payment:", e)
            print(order.id)
            return render(request, 'cart/paymentfail.html', context={'order_id':order.id})
    else:
        return HttpResponseBadRequest("Invalid request method.")