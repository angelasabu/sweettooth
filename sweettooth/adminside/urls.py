from django.urls import path
from .views import *


urlpatterns = [
    path('', admin_login, name='admin_login'),
    path('admin_logout/', admin_logout, name='admin_logout'),
    path('admin_home/', admin_home, name='admin_home'),
    path('user_management/', user_management, name='user_management'),
    path('update_status/', update_user_status, name='update_user_status'),
    path('add_product/', add_product, name='add_product'),
    path('check_product_name/', check_product_name, name='check_product_name'),
    path('add_category/', add_category, name='add_category'),
    path('check_category_name/', check_category_name, name='check_category_name'),
    path('list_category/', list_category, name='list_category'),
    path('toggle_category_status/', toggle_category_status, name='toggle_category_status'),
    path('toggle_product_status/', toggle_product_status, name='toggle_product_status'),
    path('list_product/', list_product, name='list_product'),
    path('edit_product/<str:product_id>/', edit_product, name='edit_product'),
    path('edit_product_image/<str:image_id>/', edit_product_image, name='edit_product_image'),
    path('edit_category/<str:category_uid>/', edit_category, name='edit_category'),
    path('product_detail/<str:product_id>/', product_detail, name='product_detail'),
    path('add_coupon/', add_coupon, name='add_coupon'),
    path('list_coupon/', list_coupon, name='list_coupon'),
    path("update_coupon_status/", update_coupon_status, name='update_coupon_status'),
    path("admin_order_list/", admin_order_list, name='admin_order_list'),
    path('admin_order_details/<int:order_id>/', admin_order_details, name='admin_order_details'),
    path('<int:order_id>/update_order_status/', update_order_status, name='update_order_status'),
    path('add_category_offer/', add_category_offer, name='add_category_offer'),
    path('list_category_offer/', list_category_offer, name='list_category_offer'),
    path('update_category_offer_status/', update_category_offer_status, name='update_category_offer_status'),
    path('admin_sales_report/', admin_sales_report, name='admin_sales_report'),
    path('sales_report_pdf/', SalesReportPDFView.as_view(), name='sales_report_pdf'),
]