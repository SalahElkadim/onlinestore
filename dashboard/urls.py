from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import push_views
from .views import (
    # Auth
    AdminLoginView, AdminLogoutView, ChangePasswordView, MeView,

    # Dashboard
    DashboardStatsView, InventoryAlertsView, AnalyticsView, UpdateOrderView,

    # Users
    UserListView, UserDetailView, UserBlockToggleView,
    AdminUserListView, AdminRoleListView,

    # Categories
    CategoryListView, CategoryDetailView,

    # Products
    ProductListView, ProductDetailView, ProductImageView,
    ProductVariantListView, ProductVariantDetailView, UpdateVariantStockView,
    AttributeListView, AttributeDetailView,
    AttributeValueListView, AttributeValueDetailView,
    GenerateVariantsView,

    # Orders
    OrderListView, OrderDetailView, UpdateOrderStatusView,
    OrderStatsView, ExportOrdersView,
    DeleteOrderView,

    # Payments
    PaymentListView, RefundView,

    # Coupons
    CouponListView, CouponDetailView, ValidateCouponView,

    # Notifications
    NotificationListView, MarkNotificationReadView, UnreadNotificationCountView,

    # Activity Log
    ActivityLogListView,

    # Shipping
    ShippingRateListView, ShippingRateDetailView, BulkShippingRateView,
)

app_name = 'admin_dashboard'

urlpatterns = [

    # ──────────────────────────────────────────────────────────
    # AUTH
    # ──────────────────────────────────────────────────────────
    path('auth/login/',           AdminLoginView.as_view(),     name='login'),
    path('auth/logout/',          AdminLogoutView.as_view(),    name='logout'),
    path('auth/token/refresh/',   TokenRefreshView.as_view(),   name='token_refresh'),
    path('auth/change-password/', ChangePasswordView.as_view(), name='change_password'),
    path('auth/me/',              MeView.as_view(),             name='me'),

    # ──────────────────────────────────────────────────────────
    # DASHBOARD
    # ──────────────────────────────────────────────────────────
    path('dashboard/stats/',            DashboardStatsView.as_view(),  name='dashboard_stats'),
    path('dashboard/inventory-alerts/', InventoryAlertsView.as_view(), name='inventory_alerts'),
    path('dashboard/analytics/',        AnalyticsView.as_view(),       name='analytics'),

    # ──────────────────────────────────────────────────────────
    # CUSTOMERS
    # ──────────────────────────────────────────────────────────
    path('customers/',                UserListView.as_view(),        name='customer_list'),
    path('customers/<int:pk>/',       UserDetailView.as_view(),      name='customer_detail'),
    path('customers/<int:pk>/block/', UserBlockToggleView.as_view(), name='customer_block'),

    # ──────────────────────────────────────────────────────────
    # ADMIN USERS & ROLES
    # ──────────────────────────────────────────────────────────
    path('admins/', AdminUserListView.as_view(), name='admin_list'),
    path('roles/',  AdminRoleListView.as_view(),  name='role_list'),

    # ──────────────────────────────────────────────────────────
    # CATEGORIES
    # ──────────────────────────────────────────────────────────
    path('categories/',          CategoryListView.as_view(),   name='category_list'),
    path('categories/<int:pk>/', CategoryDetailView.as_view(), name='category_detail'),

    # ──────────────────────────────────────────────────────────
    # PRODUCTS
    # ──────────────────────────────────────────────────────────
    path('products/',         ProductListView.as_view(),   name='product_list'),
    path('products/<int:pk>/', ProductDetailView.as_view(), name='product_detail'),
    path('products/<int:pk>/images/<int:image_pk>/',
         ProductImageView.as_view(), name='product_image'),

    path('products/<int:pk>/generate-variants/',
         GenerateVariantsView.as_view(), name='generate_variants'),

    # Variants
    path('products/<int:pk>/variants/',
         ProductVariantListView.as_view(), name='variant_list'),
    path('products/<int:pk>/variants/<int:variant_pk>/',
         ProductVariantDetailView.as_view(), name='variant_detail'),
    path('products/<int:pk>/variants/<int:variant_pk>/stock/',
         UpdateVariantStockView.as_view(), name='variant_stock'),

    # ──────────────────────────────────────────────────────────
    # ATTRIBUTES  (تعريف واحد فقط — بدون تكرار)
    # ──────────────────────────────────────────────────────────
    path('attributes/',
         AttributeListView.as_view(), name='attribute_list'),
    path('attributes/<int:pk>/',
         AttributeDetailView.as_view(), name='attribute_detail'),
    path('attributes/<int:pk>/values/',
         AttributeValueListView.as_view(), name='attribute_value_list'),
    path('attributes/<int:pk>/values/<int:value_pk>/',
         AttributeValueDetailView.as_view(), name='attribute_value_detail'),

    # ──────────────────────────────────────────────────────────
    # ORDERS  — static routes أولاً، ثم dynamic
    # ──────────────────────────────────────────────────────────
    path('orders/',          OrderListView.as_view(),  name='order_list'),
    path('orders/stats/',    OrderStatsView.as_view(), name='order_stats'),
    path('orders/export/',   ExportOrdersView.as_view(), name='order_export'),

    path('orders/<int:pk>/',        OrderDetailView.as_view(),      name='order_detail'),
    path('orders/<int:pk>/status/', UpdateOrderStatusView.as_view(), name='order_status'),
    path('orders/<int:pk>/edit/',   UpdateOrderView.as_view(),       name='order_edit'),
    path('orders/<int:pk>/delete/', DeleteOrderView.as_view(),       name='order_delete'),

    # ──────────────────────────────────────────────────────────
    # PAYMENTS
    # ──────────────────────────────────────────────────────────
    path('payments/',                 PaymentListView.as_view(), name='payment_list'),
    path('payments/<int:pk>/refund/', RefundView.as_view(),      name='payment_refund'),

    # ──────────────────────────────────────────────────────────
    # COUPONS  — static قبل dynamic
    # ──────────────────────────────────────────────────────────
    path('coupons/',           CouponListView.as_view(),    name='coupon_list'),
    path('coupons/validate/',  ValidateCouponView.as_view(), name='coupon_validate'),
    path('coupons/<int:pk>/',  CouponDetailView.as_view(),  name='coupon_detail'),

    # ──────────────────────────────────────────────────────────
    # NOTIFICATIONS  — static قبل dynamic
    # ──────────────────────────────────────────────────────────
    path('notifications/',
         NotificationListView.as_view(), name='notification_list'),
    path('notifications/unread-count/',
         UnreadNotificationCountView.as_view(), name='notification_count'),
    path('notifications/mark-all-read/',
         MarkNotificationReadView.as_view(), name='notification_mark_all'),
    path('notifications/<int:pk>/mark-read/',
         MarkNotificationReadView.as_view(), name='notification_mark_one'),

    # ──────────────────────────────────────────────────────────
    # ACTIVITY LOGS
    # ──────────────────────────────────────────────────────────
    path('activity-logs/', ActivityLogListView.as_view(), name='activity_logs'),

    # ──────────────────────────────────────────────────────────
    # PUSH NOTIFICATIONS
    # ──────────────────────────────────────────────────────────
    path('push/register/',   push_views.RegisterPushDeviceView.as_view(),   name='push_register'),
    path('push/unregister/', push_views.UnregisterPushDeviceView.as_view(), name='push_unregister'),

    # ──────────────────────────────────────────────────────────
    # SHIPPING RATES  — static (bulk) قبل dynamic (<int:pk>)
    # ──────────────────────────────────────────────────────────
    path('shipping-rates/',         ShippingRateListView.as_view(),   name='shipping_rate_list'),
    path('shipping-rates/bulk/',    BulkShippingRateView.as_view(),   name='shipping_rate_bulk'),
    path('shipping-rates/<int:pk>/', ShippingRateDetailView.as_view(), name='shipping_rate_detail'),
]