from django.shortcuts import redirect, render
from products.models import *
from accounts.models import *
from orders.models import *
from cart.models import *
from offer.models import *
from django.shortcuts import get_object_or_404
from django.contrib import messages
from django.http import HttpResponse
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from decimal import Decimal
from accounts.utils import user_login_required
from django.contrib.auth.decorators import login_required
from django.template.loader import render_to_string
from xhtml2pdf import pisa
from django.conf import settings
import razorpay


# Create your views here.

def index(request):
    try:
        cart = request.user.profile.cart
        cart_items = CartItem.objects.filter(cart=cart, is_active=True)
        item_count = sum(item.quantity for item in cart_items)
    except:
        item_count = 0
        
    latest_products = Product.objects.filter(is_active=True).order_by('-uid')[:6]
    context = {
        'item_count' : item_count,
        'latest_products' : latest_products
    }
    return render(request, 'home/index.html', context)



def shop(request):
    search_query = request.GET.get('q', '')
    sort_option = request.GET.get('sort', 'default')
    category_filter = request.GET.get('category', '')  # Get the selected category from the query string

    try:
        cart = request.user.profile.cart
        cart_items = CartItem.objects.filter(cart=cart, is_active=True)
        item_count = sum(item.quantity for item in cart_items)
    except:
        item_count = 0

    # Base queryset
    products = Product.objects.filter(
        category__is_active=True,
        is_active=True
    )

    # Apply search filter
    if search_query:
        products = products.filter(
            Q(product_name__icontains=search_query) | Q(category__category_name__icontains=search_query)
        )

    # Apply category filter
    if category_filter:
        products = products.filter(category__slug=category_filter)

    # Handle no matches
    if (search_query or category_filter) and not products.exists():
        messages.info(request, "No matches found for your search or filter.")

    # Process products with pricing and discounts
    products_with_price = []
    for product in products:
        first_in_stock_variant = product.size_variants.filter(stock__gt=0).first()
        if first_in_stock_variant:
            original_price = first_in_stock_variant.price

            # Check for category offer
            category_offer = CategoryOffer.objects.filter(
                category=product.category,
                is_active=True,
                expiry_date__gte=timezone.now()
            ).first()

            discounted_price = (
                original_price - (original_price * category_offer.percentage / 100)
                if category_offer else original_price
            )

            products_with_price.append({
                'product': product,
                'original_price': original_price,
                'discounted_price': discounted_price,
                'has_discount': discounted_price < original_price
            })
        else:
            # If no size variant is in stock, mark as unavailable
            products_with_price.append({
                'product': product,
                'original_price': None,
                'discounted_price': None,
                'has_discount': False
            })

    # Sorting logic
    if sort_option == 'price_asc':
        products_with_price.sort(key=lambda p: p['discounted_price'] or float('inf'))
    elif sort_option == 'price_desc':
        products_with_price.sort(key=lambda p: p['discounted_price'] or 0, reverse=True)

    # Get all categories for the filter menu
    categories = Category.objects.filter(is_active=True)

    context = {
        'products_with_price': products_with_price,
        'search_query': search_query,
        'sort_option': sort_option,
        'item_count': item_count,
        'categories': categories,  # Pass categories to the template
        'selected_category': category_filter,  # Keep track of the selected category
    }
    return render(request, 'home/shop.html', context)




@login_required(login_url='login')
def user_details(request, slug):
    profile = get_object_or_404(Profile, slug=slug)
    print(profile, 'llll')
    try:
        cart = request.user.profile.cart
        cart_items = CartItem.objects.filter(cart=cart, is_active=True)
        item_count = sum(item.quantity for item in cart_items)
    except:
        item_count = 0
    orders = Order.objects.filter(profile=profile).order_by('-order_date')
    wallet, created = Wallet.objects.get_or_create(profile=profile)
    referral_code = profile.referral_offer.referral_code if hasattr(profile, 'referral_offer') else None
    print(wallet.amount, 'amount')
    transactions = Transaction.objects.filter(wallet=wallet)
    context = {
        'profile': profile,
        'orders': orders,
        'transactions': transactions,
        'wallet': wallet,
        'item_count' : item_count,
        'referral_code':referral_code,
    }
    return render(request, 'home/user_profile.html', context)


@login_required(login_url='login')
def update_profile(request):
    user = request.user
    profile = Profile.objects.get(user=user)
    
    try:
        cart = request.user.profile.cart
        cart_items = CartItem.objects.filter(cart=cart, is_active=True)
        item_count = sum(item.quantity for item in cart_items)
    except:
        item_count = 0

    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        phone_number = request.POST.get('phone_number')

        user.first_name = first_name
        user.last_name = last_name
        user.email = email
        user.save()
        profile.phone_number = phone_number
        profile.save()

        print(request.POST)

        address_count = len([key for key in request.POST.keys() if key.startswith('address_uid_')])

        for i in range(1, address_count + 1):
            address_uid = request.POST.get(f'address_uid_{i}')
            address_value = request.POST.get(f'address_{i}')

            if address_value:
                address_components = address_value.split(',')
                house_no = address_components[0].strip()
                street = address_components[1].strip()
                post_office = address_components[2].strip()
                district = address_components[3].strip()
                state = address_components[4].strip()
                country_pin = address_components[5].strip().split('-')
                country = country_pin[0].strip()
                pin_code = country_pin[1].strip() if len(country_pin) > 1 else ''

                address = Address.objects.get(uid=address_uid)
                address.house_no = house_no
                address.street = street
                address.post_office = post_office
                address.district = district
                address.state = state
                address.country = country
                address.pin_code = pin_code
                address.save()

        messages.success(request, 'Your profile and addresses have been updated successfully.')
        return redirect('user_details', profile.slug)

    return render(request, 'home/user_profile.html', {'profile': profile, 'item_count' : item_count})



@login_required(login_url='login')
def add_address(request):
    if request.method == 'POST':
        house_no = request.POST.get('house_no')
        street = request.POST.get('street')
        post_office = request.POST.get('post_office')
        district = request.POST.get('district')
        state = request.POST.get('state')
        country = request.POST.get('country')
        pin_code = request.POST.get('pin_code')

        profile = request.user.profile
        Address.objects.create(
            profile=profile,
            house_no=house_no,
            street=street,
            post_office=post_office,
            district=district,
            state=state,
            country=country,
            pin_code=pin_code
        )
        return redirect('user_details', profile.slug)

    return render(request, 'add_address.html')

razorpay_client = razorpay.Client(
    auth=(settings.RAZOR_KEY_ID, settings.RAZOR_KEY_SECRET))


@login_required(login_url='login')
def order_details(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    order_items = order.order_items.all()
    for item in order_items:
        item.total_price = item.quantity * item.price
        
    print(order, order.order_items, 'items')
        
    context = {
        'order': order,
        'order_items': order_items,
    }
    if not order.is_paid:
        razorpay_order = razorpay_client.order.create(
            dict(
                amount=int(order.total_amount) * 100,
                currency='INR',
                payment_capture='0',
            )
        )
        
        razorpay_order_id = razorpay_order['id']
        callback_url = f'http://127.0.0.1:8000/cart/retry_payment/{order.id}/'
        
        context.update({
            'razorpay_order_id': razorpay_order_id,
            'callback_url': callback_url,
        })
    return render(request, 'home/order_details.html', context)



@login_required(login_url='login')
def cancel_order(request, order_id):
    if request.method == 'POST' and request.user.is_authenticated:
        try:
            order = Order.objects.get(id=order_id, profile=request.user.profile)
        except Order.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Order not found.'})

        # Check if the order status is not already cancelled
        if order.status in ['Cancelled', 'Cancelled by Admin']:
            return JsonResponse({'success': False, 'message': 'Order is already cancelled.'})

        # Update the order status to 'Cancelled'
        with transaction.atomic():  # Ensure all operations are atomic
            order.status = 'Cancelled'
            order.save()

            # Handle wallet refund if the order is paid
            if order.is_paid:
                wallet, created = Wallet.objects.get_or_create(profile=order.profile)

                # Update wallet balance
                wallet.amount = Decimal(str(wallet.amount)) + Decimal(order.total_amount)
                wallet.save()

                # Create a credit transaction
                Transaction.objects.create(
                    wallet=wallet,
                    amount=order.total_amount,
                    transaction_type='credit',
                )

        return JsonResponse({'success': True, 'message': 'Order cancelled and amount refunded to wallet.'})

    return JsonResponse({'success': False, 'message': 'Invalid request.'})





@login_required(login_url='login')
def download_invoice(request, order_id):
    try:
        # Get the order and related items
        order = Order.objects.get(id=order_id)
        order_items = order.order_items.all()  # Assuming related_name is `order_items`

        # Render the HTML content
        template_path = 'home/invoice_template.html'
        context = {
            'order': order,
            'order_items': order_items,
        }
        html = render_to_string(template_path, context)

        # Generate PDF
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="invoice_{order_id}.pdf"'
        pisa_status = pisa.CreatePDF(html, dest=response)

        # Check for errors
        if pisa_status.err:
            return HttpResponse('We had some errors <pre>' + html + '</pre>')
        return response
    except Order.DoesNotExist:
        return HttpResponse('Order not found', status=404)

