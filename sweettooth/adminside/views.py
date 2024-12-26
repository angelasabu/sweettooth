import re
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from accounts.models import Profile
from django.http import JsonResponse
import json
from django.contrib.auth.models import User
from products.models import *
from cart.models import *
from orders.models import *
from offer.models import *
from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import ValidationError
from django.views.decorators.csrf import csrf_exempt
from django.contrib.sessions.models import Session
from django.utils import timezone
import logging
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.db.models import Sum, Count
from django.db.models.functions import TruncMonth
from io import BytesIO
from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa
from django.views import View
from django.utils.timezone import make_aware
from datetime import datetime, date, timedelta
from django.db.models import Sum

logger = logging.getLogger(__name__)




# Create your views here.

def is_superuser(user):
    return user.is_superuser


def admin_login(request):
    admin_id = request.session.get('admin_id')
    if admin_id is not None:
        return redirect('admin_home')
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')

        if not re.match(r'^[A-Za-z0-9_]+$', username):
            messages.error(request, "Username should only contain letters, numbers and underscores.")
            return redirect ('admin_login')

        if ' ' in username:
            messages.error(request, "Username should not contain spaces.")
            return redirect ('admin_login')

        if len(password) < 8:
            messages.error(request, "Password should be atleast 8 characters long.")
            return redirect ('admin_login')

        if not re.search(r'\d', password):
            messages.error(request, "Password should contain atleast one number.")
        
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            if user.is_superuser:
                request.session['admin_id'] = user.id
                login(request, user)
                return redirect('admin_home')
            else:
                messages.error(request, "You do not have access to the admin panel.")
        else:
            messages.error(request, "Invalid username or password.")
        return redirect('admin_login')
    return render(request, 'admin/admin_login.html')


@user_passes_test(is_superuser, login_url='admin_login')
def admin_logout(request):
    delete_user_id = request.session.pop('admin_id', None)
    logout(request)
    return redirect('admin_login')



@user_passes_test(is_superuser, login_url='admin_login')
def admin_home(request):
    admin_id = request.session.get('admin_id')
    if admin_id is None:
        return redirect('admin_login')
    if not request.user.is_superuser:
        return redirect('admin_login')
    
    
    orders = Order.objects.filter(status='Delivered')
    count = orders.count()

    revenue = orders.aggregate(total_revenue=Sum('total_amount'))['total_revenue'] or 0

    chart_month = []
    new_users = []
    orders_count = []

    for month in range(1, 13):
        item_quantity = (
            OrderItem.objects.filter(order__status='Delivered', order__order_date__month=month)
            .aggregate(total_quantity=Sum('quantity'))['total_quantity'] or 0
        )
        chart_month.append(item_quantity)

        user_count = Profile.objects.filter(user__date_joined__month=month).count()
        new_users.append(user_count)

        monthly_orders = orders.filter(order_date__month=month).count()
        orders_count.append(monthly_orders)
    
    total_delivered_amount = Order.objects.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    
    current_month = now().month
    current_year = now().year
    current_month_delivered_amount = Order.objects.filter(
        order_date__year=current_year,
        order_date__month=current_month
    ).aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    
    total_orders = Order.objects.aggregate(Count('id'))['id__count'] or 0
    
    total_products = Product.objects.filter(is_active=True).aggregate(Count('uid'))['uid__count'] or 0
    
    total_categories = Category.objects.filter(is_active=True).aggregate(Count('uid'))['uid__count'] or 0
    
    latest_users = Profile.objects.order_by('-created_at')[:5]
    
    latest_orders = Order.objects.order_by('-order_date')[:7]
    
    bestselling_products = (
        OrderItem.objects.values('product_name')
        .annotate(total_quantity=Sum('quantity'))
        .order_by('-total_quantity')[:3]
    )
    for product in bestselling_products:
        product_obj = Product.objects.get(product_name=product['product_name'])
        product['product_image'] = product_obj.product_images.first().image.url if product_obj.product_images.exists() else None
    
    
    context = {
        'total_delivered_amount': total_delivered_amount,
        'current_month_delivered_amount': current_month_delivered_amount,
        'total_orders': total_orders,
        'total_products': total_products,
        'total_categories': total_categories,
        'sales_chart_data': orders_count,
        'visitors_chart_data': new_users,
        'products_chart_data': chart_month,
        'latest_users': latest_users,
        'latest_orders': latest_orders,
        'bestselling_products': bestselling_products,
    }
    return render(request, 'admin/admin_index.html', context)



@user_passes_test(is_superuser, login_url='admin_login')
def user_management(request):
    profiles = Profile.objects.filter(user__is_superuser=False)
    context = {'profiles': profiles}
    return render(request, 'admin/user_management.html', context)



@user_passes_test(is_superuser, login_url='admin_login')
def update_user_status(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            profile_id = data.get('profile_id')
            print(profile_id)
            is_active = data.get('is_active')

            user = User.objects.get(id=profile_id)
            
            user.is_active = not user.is_active
            user.save()
            
            if not user.is_active:
                sessions = Session.objects.filter(expire_date__gte=timezone.now())
                
            
                for session in sessions:
                        session_data = session.get_decoded()
                        
                        if session_data.get('_auth_user_id') == str(user.id):
                            session.delete()

            return JsonResponse({'status': 'success', 'message': 'User status updated successfully'})
        except User.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'User does not exist.'})
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON data.'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'})




@user_passes_test(is_superuser, login_url='admin_login')
def add_category(request):
    if request.method == 'POST':
        category_name = request.POST.get('category_name')
        category_image = request.FILES.get('category_image')

        if not category_name or not category_image:
            messages.error(request, 'Category name and image are required.')
            return redirect('add_category')

        if Category.objects.filter(category_name=category_name).exists():
            messages.error(request, 'Category with this name already exists.')
            return redirect('add_category')

        category = Category.objects.create(
            category_name=category_name,
            category_image=category_image
        )

        messages.success(request, 'Category added successfully!')
        return redirect('list_category')

    return render(request, 'admin/admin_add_category.html')



@user_passes_test(is_superuser, login_url='admin_login')
def add_product(request):
    if request.method == 'POST':

        product_name = request.POST.get('product_name')
        category_id = request.POST.get('category')
        product_description = request.POST.get('product_description')
        
        if not product_name or not category_id or not product_description:
            messages.error(request, 'All fields are required.')
            return redirect('add_product')

        
        if Product.objects.filter(product_name=product_name).exists():
            messages.error(request, 'Product with this name already exists.')
            return redirect('add_product')

        try:
            category = Category.objects.get(uid=category_id)

            product = Product.objects.create(
                product_name=product_name,
                category=category,
                product_description=product_description,
            )

            image_errors = False
            for i in range(1, 4):
                image_file = request.FILES.get(f'product_image{i}')
                if image_file:
                    ProductImage.objects.create(product=product, image=image_file)
                else:
                    image_errors = True

            if image_errors:
                messages.error(request, 'All 3 product images are required.')
                product.delete()
                return redirect('add_product')

            variant_count = 0
            for i in range(1, 6):
                size_name = request.POST.get(f'size_name_{i}')
                price = request.POST.get(f'price_{i}')
                stock = request.POST.get(f'stock_{i}')

                if size_name or price or stock:
                    if not (size_name and price and stock):
                        messages.error(request, f'All fields (size name, price, and stock) must be filled for variant {i}.')
                        product.delete()
                        return redirect('add_product')

                    variant_count += 1
                    SizeVariant.objects.create(
                        product=product,
                        size_name=size_name,
                        price=int(price),
                        stock=int(stock)
                    )

            
            if variant_count == 0:
                messages.error(request, 'At least one size variant must be provided.')
                product.delete()
                return redirect('add_product')

            messages.success(request, 'Product added successfully!')
            return redirect('list_product')

        except Category.DoesNotExist:
            messages.error(request, 'Invalid category selected.')
            return redirect('add_product')
        except ValidationError as e:
            messages.error(request, f"Error: {str(e)}")
            return redirect('add_product')

   
    categories = Category.objects.all()
    context = {
        'categories': categories,
        'size_range': range(1, 4)
    }
    
    return render(request, 'admin/admin_add_products.html', context)




@user_passes_test(is_superuser, login_url='admin_login')
def list_category(request):
    categories = Category.objects.all().order_by('category_name')
    context = {'categories': categories}
    return render(request, 'admin/admin_list_category.html', context)


@user_passes_test(is_superuser, login_url='admin_login')
@csrf_exempt
def toggle_category_status(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        category_id = data.get('category_uid')
        print(category_id)
        is_active = data.get('is_active')

        try:
            category = Category.objects.get(uid=category_id)
            category.is_active = is_active
            category.save()

            return JsonResponse({'success': True, 'is_active': category.is_active})
        except Category.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Category not found.'})
    return JsonResponse({'success': False, 'error': 'Invalid request method.'})




@user_passes_test(is_superuser, login_url='admin_login')
def list_product(request):
    products = Product.objects.prefetch_related('product_images').all().order_by('product_name')
    context = {'products': products}
    return render(request, 'admin/admin_list_product.html', context)



@user_passes_test(is_superuser, login_url='admin_login')
@csrf_exempt 
def toggle_product_status(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            is_active = data.get('is_active')
            product_id = data.get('product_id')
            product = Product.objects.get(uid=product_id)
            size_variants = product.size_variants.all()
            has_stock = any(variant.stock > 1 for variant in size_variants)
            
            if has_stock:
                product.is_active = is_active
            
            product.save()

            return JsonResponse({'success': True})
        except Product.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Product not found'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=400)


@user_passes_test(is_superuser, login_url='admin_login')
def edit_category(request, category_uid):
    category = Category.objects.get(uid=category_uid)
    if request.method == 'POST':
        category_name = request.POST.get('category_name')
        category_image = request.FILES.get('category_image')
        category.category_name = category_name
        if category_image:
            category.category_image.delete()
            category.category_image = category_image
        category.save()
        return redirect('list_category')
    context={
        'category' : category
    }
    return render(request, 'admin/admin_edit_category.html', context)

@user_passes_test(is_superuser, login_url='admin_login')
def edit_product(request, product_id):
    product = Product.objects.get(uid=product_id)
    categories = Category.objects.all()

    if request.method == 'POST':
        product_name = request.POST.get('product_name')
        category_id = request.POST.get('category')
        product_description = request.POST.get('product_description')

        if not product_name or not category_id or not product_description:
            messages.error(request, 'All fields are required.')
            return redirect('edit_product', product_id=product_id)

        category = Category.objects.get(uid=category_id)

        product.product_name = product_name
        product.category = category
        product.product_description = product_description
        product.save()
        
            
        SizeVariant.objects.filter(product=product).delete()
        size_errors = False
        for i in range(1, 4):
            size_name = request.POST.get(f'size_name_{i}')
            price = request.POST.get(f'price_{i}')
            stock = request.POST.get(f'stock_{i}')

            if size_name and price and stock:
                SizeVariant.objects.create(
                    product=product,
                    size_name=size_name,
                    price=int(price),
                    stock=int(stock)
                )
            elif size_name or price or stock:
                size_errors = True

        if size_errors:
            messages.error(request, 'All fields (size name, price, and stock) must be filled for each size variant.')
            return redirect('edit_product', product_id=product_id)

        messages.success(request, 'Product updated successfully!')
        return redirect('list_product')

    size_variants = list(product.size_variants.all()[:3])
    while len(size_variants) < 3:
        size_variants.append({'size_name': '', 'price': '', 'stock': ''})

    context = {
        'product': product,
        'categories': categories,
        'size_variants': size_variants
    }
    return render(request, 'admin/admin_edit_product.html', context)

def edit_product_image(request, image_id):
    if request.method == "POST":
        print(f"Received image_id: {image_id}")
        image_instance = get_object_or_404(ProductImage, uid=image_id)
        new_image = request.FILES.get('product_image')
        
        if new_image:
            # Update the image field with the new file
            image_instance.image = new_image
            image_instance.save()
            return JsonResponse({'success': True, 'message': "Product image updated successfully."})
        else:
            return JsonResponse({'success': False, 'error': "Please upload a valid image file."}, status=400)
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)




@user_passes_test(is_superuser, login_url='admin_login')
def check_product_name(request):
    if request.method == "GET":
        product_name = request.GET.get('product_name', None)
        exists = Product.objects.filter(product_name__iexact=product_name).exists()
        return JsonResponse({'exists': exists})
    

@user_passes_test(is_superuser, login_url='admin_login')   
def check_category_name(request):
    if request.method == "GET":
        category_name = request.GET.get('category_name', None)
        exists = Category.objects.filter(category_name__iexact=category_name).exists()
        return JsonResponse({'exists': exists})
    
def product_detail(request, product_id):
    product = Product.objects.get(uid = product_id)
    categories = Category.objects.all()
    context={
        'product' : product,
        'categories' : categories
    }
    return render(request, 'admin/admin_product_detail.html', context)



@user_passes_test(is_superuser, login_url='admin_login')
def add_coupon(request):
    if request.method == "POST":
        coupon_code = request.POST.get("coupon_code")
        percentage = request.POST.get("percentage")
        limit = request.POST.get("limit")
        total_coupons = request.POST.get("total_coupons")
        expiry_date = request.POST.get("expiry_date")
        
        try:
            percentage = float(percentage)
            limit = float(limit)
            total_coupons = int(total_coupons)
            expiry_date = timezone.datetime.strptime(expiry_date, '%Y-%m-%d').replace(tzinfo=timezone.get_current_timezone())
            
            Coupon.objects.create(
                coupon_code=coupon_code,
                percentage=percentage,
                limit=limit,
                total_coupons=total_coupons,
                expiry_date=expiry_date
            )
            messages.success(request, "Coupon added successfully.")
            return redirect("list_coupon")
            
        except ValueError:
            messages.error(request, "Invalid input. Please check your data.")
    
    return render(request, "admin/admin_add_coupon.html")



@user_passes_test(is_superuser, login_url='admin_login')
def list_coupon(request):
    coupons = Coupon.objects.all()
    return render(request, "admin/admin_list_coupon.html", {"coupons": coupons})



@user_passes_test(is_superuser, login_url='admin_login')
@require_POST
@csrf_exempt
def update_coupon_status(request):
    import json
    try:
        data = json.loads(request.body)
        coupon_id = data.get("coupon_id")
        is_active = data.get("is_active")

        coupon = Coupon.objects.get(id=coupon_id)
        coupon.is_active = is_active
        print(coupon)
        coupon.save()

        return JsonResponse({"success": True, "new_status": coupon.is_active})
    except Coupon.DoesNotExist:
        return JsonResponse({"success": False, "error": "Coupon not found"}, status=404)
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)
    
    


@user_passes_test(is_superuser, login_url='admin_login')    
def admin_order_list(request):
    orders = Order.objects.all()
    context = {
        'orders': orders,
    }
    return render(request, 'admin/admin_list_orders.html', context)




@user_passes_test(is_superuser, login_url='admin_login')
def admin_order_details(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    order_items = order.order_items.all()
    for item in order_items:
        item.total_price = item.quantity * item.price
    status_choices = Order.STATUS_CHOICES
    
    context = {
        'order': order,
        'order_items': order_items,
        'status_choices': status_choices,
    }
    return render(request, 'admin/admin_order_details.html', context)




@user_passes_test(is_superuser, login_url='admin_login')
def update_order_status(request, order_id):
    if request.method == "POST":
        new_status = request.POST.get("status")
        order = get_object_or_404(Order, id=order_id)
        order.status = new_status
        order.save()
        return redirect(reverse('admin_order_details', args=[order_id]))
    
    
    
    
    
@user_passes_test(is_superuser, login_url='admin_login')
def add_category_offer(request):
    if request.method == "POST":
        category_id = request.POST.get("category")
        percentage = request.POST.get("percentage")
        expiry_date = request.POST.get("expiry_date")
        print(category_id, percentage, expiry_date, "jhfvuviiii")

        # Validate data
        if not (category_id and percentage and expiry_date):
            messages.error(request, "All fields are required.")
            return redirect("add_category_offer")

        try:
            # Check if the category already has an offer
            category = Category.objects.get(uid=category_id)
            if CategoryOffer.objects.filter(category=category).exists():
                messages.error(request, "This category already has an offer.")
                return redirect("add_category_offer")

            # Save the offer
            CategoryOffer.objects.create(
                category=category,
                percentage=float(percentage),
                expiry_date=expiry_date,
                is_active=True
            )
            messages.success(request, "Category offer added successfully!")
            return redirect("add_category_offer")

        except Category.DoesNotExist:
            messages.error(request, "Invalid category selected.")
            return redirect("add_category_offer")
    else:
        categories = Category.objects.filter(is_active=True)
    
    context = {'categories': categories}
    return render(request, 'admin/admin_add_category_offer.html', context)





def list_category_offer(request):
    offers = CategoryOffer.objects.all()
    
    context = {
        'offers': offers
    }
    return render(request, 'admin/admin_list_offer.html', context)




def update_category_offer_status(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            offer_id = data.get("offer_id")
            is_active = data.get("is_active")

            # Fetch the CategoryOffer object
            offer = CategoryOffer.objects.get(id=offer_id)
            offer.is_active = is_active
            offer.save()

            return JsonResponse({"success": True})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})
    return JsonResponse({"success": False, "error": "Invalid request method."})




def admin_sales_report(request):
    return render(request, 'admin/admin_sales_report.html')


class SalesReportPDFView(View):
    def save_pdf(self, params: dict):
        template = get_template("admin/sales_report.html")
        html = template.render(params)
        response = BytesIO()
        pdf = pisa.pisaDocument(BytesIO(html.encode('UTF-8')), response)
        if not pdf.err:
            return response.getvalue(), True
        return '', False

    def get(self, request, *args, **kwargs):
        

        total_users = Profile.objects.count()
        new_orders = Order.objects.exclude(status="Pending").count()

        # Calculate total revenue from successful payments
        payments = Order.objects.filter(is_paid=True)
        revenue_total = payments.aggregate(Sum('total_amount'))['total_amount__sum'] or 0

        # Calculate monthly revenue
        current_month = datetime.now().month
        monthly_payments = payments.filter(order_date__month=current_month)
        monthly_revenue = monthly_payments.aggregate(Sum('total_amount'))['total_amount__sum'] or 0

        # Filter orders based on date range and status
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        status = request.GET.get('status')

        start_date = make_aware(datetime.strptime(start_date, '%Y-%m-%d')) if start_date else None
        end_date = make_aware(datetime.strptime(end_date, '%Y-%m-%d')) + timedelta(days=1) - timedelta(seconds=1) if end_date else None

        orders = Order.objects.all()
        if start_date and end_date:
            orders = orders.filter(order_date__gte=start_date, order_date__lt=end_date)
        elif start_date:
            orders = orders.filter(order_date__gte=start_date)
        elif end_date:
            orders = orders.filter(order_date__lt=end_date)

        if status and status != 'Status':
            orders = orders.filter(status=status)

        # Prepare data for the PDF
        params = {
            'total_users': total_users,
            'new_orders': new_orders,
            'revenue_total': revenue_total,
            'd_month_len': monthly_payments.count(),
            'revenue_this_month': monthly_revenue,
            'all_orders': orders,  # Pass filtered orders to the template
        }

        # Generate the PDF
        file_data, success = self.save_pdf(params)
        if success:
            response = HttpResponse(file_data, content_type='application/pdf')
            response['Content-Disposition'] = 'attachment; filename="sales_report.pdf"'
            return response
        else:
            return HttpResponse("Failed to generate the sales report.", status=500)