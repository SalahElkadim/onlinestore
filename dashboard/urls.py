

from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    # Auth
    AdminLoginView, AdminLogoutView, ChangePasswordView, MeView,

    # Dashboard
    DashboardStatsView, InventoryAlertsView, AnalyticsView,

    # Users
    UserListView, UserDetailView, UserBlockToggleView,
    AdminUserListView, AdminRoleListView,

    # Categories
    CategoryListView, CategoryDetailView,

    # Products
    ProductListView, ProductDetailView, ProductImageView,
    ProductVariantListView, ProductVariantDetailView, UpdateVariantStockView,
    AttributeListView, AttributeValueListView,AttributeListView, AttributeDetailView,
    AttributeValueListView, AttributeValueDetailView, GenerateVariantsView,
DeleteOrderView,
    # Orders
    OrderListView, OrderDetailView, UpdateOrderStatusView,
    OrderStatsView, ExportOrdersView,

    # Payments
    PaymentListView, RefundView,

    # Coupons
    CouponListView, CouponDetailView, ValidateCouponView,

    # Notifications
    NotificationListView, MarkNotificationReadView, UnreadNotificationCountView,

    # Activity Log
    ActivityLogListView,
)

app_name = 'admin_dashboard'

urlpatterns = [

    # ──────────────────────────────────────────────────────────
    # AUTH
    # POST   /api/admin/auth/login/
    # POST   /api/admin/auth/logout/
    # POST   /api/admin/auth/token/refresh/
    # POST   /api/admin/auth/change-password/
    # GET    /api/admin/auth/me/
    # PATCH  /api/admin/auth/me/
    # ──────────────────────────────────────────────────────────
    path('auth/login/',           AdminLoginView.as_view(),      name='login'),
    path('auth/logout/',          AdminLogoutView.as_view(),     name='logout'),
    path('auth/token/refresh/',   TokenRefreshView.as_view(),    name='token_refresh'),
    path('auth/change-password/', ChangePasswordView.as_view(),  name='change_password'),
    path('auth/me/',              MeView.as_view(),              name='me'),

    # ──────────────────────────────────────────────────────────
    # DASHBOARD
    # GET /api/admin/dashboard/stats/?period=30
    # GET /api/admin/dashboard/inventory-alerts/?type=low|out|all
    # GET /api/admin/dashboard/analytics/?period=30&group=day|month
    # ──────────────────────────────────────────────────────────
    path('dashboard/stats/',             DashboardStatsView.as_view(),   name='dashboard_stats'),
    path('dashboard/inventory-alerts/',  InventoryAlertsView.as_view(),  name='inventory_alerts'),
    path('dashboard/analytics/',         AnalyticsView.as_view(),        name='analytics'),

    # ──────────────────────────────────────────────────────────
    # CUSTOMERS
    # GET    /api/admin/customers/
    # GET    /api/admin/customers/{id}/
    # POST   /api/admin/customers/{id}/block/
    # ──────────────────────────────────────────────────────────
    path('customers/',                UserListView.as_view(),        name='customer_list'),
    path('customers/<int:pk>/',       UserDetailView.as_view(),      name='customer_detail'),
    path('customers/<int:pk>/block/', UserBlockToggleView.as_view(), name='customer_block'),

    # ──────────────────────────────────────────────────────────
    # ADMIN USERS & ROLES
    # GET    /api/admin/admins/
    # POST   /api/admin/admins/
    # GET    /api/admin/roles/
    # POST   /api/admin/roles/
    # ──────────────────────────────────────────────────────────
    path('admins/',  AdminUserListView.as_view(),  name='admin_list'),
    path('roles/',   AdminRoleListView.as_view(),  name='role_list'),

    # ──────────────────────────────────────────────────────────
    # CATEGORIES
    # GET    /api/admin/categories/?root_only=true
    # POST   /api/admin/categories/
    # GET    /api/admin/categories/{id}/
    # PUT    /api/admin/categories/{id}/
    # PATCH  /api/admin/categories/{id}/
    # DELETE /api/admin/categories/{id}/
    # ──────────────────────────────────────────────────────────
    path('categories/',         CategoryListView.as_view(),   name='category_list'),
    path('categories/<int:pk>/', CategoryDetailView.as_view(), name='category_detail'),

    # ──────────────────────────────────────────────────────────
    # PRODUCTS
    # GET    /api/admin/products/
    # POST   /api/admin/products/
    # GET    /api/admin/products/{id}/
    # PUT    /api/admin/products/{id}/
    # PATCH  /api/admin/products/{id}/
    # DELETE /api/admin/products/{id}/
    # DELETE /api/admin/products/{id}/images/{image_id}/
    # PATCH  /api/admin/products/{id}/images/{image_id}/set-primary/
    # ──────────────────────────────────────────────────────────
    path('products/',                           ProductListView.as_view(),    name='product_list'),
    path('products/<int:pk>/',                  ProductDetailView.as_view(),  name='product_detail'),
    path('products/<int:pk>/images/<int:image_pk>/',
         ProductImageView.as_view(),            name='product_image'),

    # Variants
    # GET    /api/admin/products/{id}/variants/
    # POST   /api/admin/products/{id}/variants/
    # GET    /api/admin/products/{id}/variants/{variant_id}/
    # PUT    /api/admin/products/{id}/variants/{variant_id}/
    # DELETE /api/admin/products/{id}/variants/{variant_id}/
    # PATCH  /api/admin/products/{id}/variants/{variant_id}/stock/
    path('products/<int:pk>/variants/',
         ProductVariantListView.as_view(),      name='variant_list'),
    path('products/<int:pk>/variants/<int:variant_pk>/',
         ProductVariantDetailView.as_view(),    name='variant_detail'),
    path('products/<int:pk>/variants/<int:variant_pk>/stock/',
         UpdateVariantStockView.as_view(),      name='variant_stock'),

    # Attributes
    # GET    /api/admin/attributes/
    # POST   /api/admin/attributes/
    # GET    /api/admin/attributes/{id}/values/
    # POST   /api/admin/attributes/{id}/values/
    path('attributes/',                          AttributeListView.as_view(),      name='attribute_list'),
    path('attributes/<int:pk>/values/',          AttributeValueListView.as_view(), name='attribute_value_list'),

    # ──────────────────────────────────────────────────────────
    # ORDERS
    # GET    /api/admin/orders/?status=&payment_status=&date_from=&date_to=
    # POST   /api/admin/orders/
    # GET    /api/admin/orders/{id}/
    # PATCH  /api/admin/orders/{id}/status/
    # GET    /api/admin/orders/stats/
    # GET    /api/admin/orders/export/
    # ──────────────────────────────────────────────────────────
    path('orders/',                   OrderListView.as_view(),        name='order_list'),
    path('orders/stats/',             OrderStatsView.as_view(),       name='order_stats'),
    path('orders/export/',            ExportOrdersView.as_view(),     name='order_export'),
    path('orders/<int:pk>/',          OrderDetailView.as_view(),      name='order_detail'),
    path('orders/<int:pk>/status/',   UpdateOrderStatusView.as_view(), name='order_status'),

    # ──────────────────────────────────────────────────────────
    # PAYMENTS
    # GET    /api/admin/payments/
    # POST   /api/admin/payments/{id}/refund/
    # ──────────────────────────────────────────────────────────
    path('payments/',                PaymentListView.as_view(), name='payment_list'),
    path('payments/<int:pk>/refund/', RefundView.as_view(),     name='payment_refund'),

    # ──────────────────────────────────────────────────────────
    # COUPONS
    # GET    /api/admin/coupons/
    # POST   /api/admin/coupons/
    # GET    /api/admin/coupons/{id}/
    # PUT    /api/admin/coupons/{id}/
    # DELETE /api/admin/coupons/{id}/
    # POST   /api/admin/coupons/validate/
    # ──────────────────────────────────────────────────────────
    path('coupons/',              CouponListView.as_view(),    name='coupon_list'),
    path('coupons/validate/',     ValidateCouponView.as_view(), name='coupon_validate'),
    path('coupons/<int:pk>/',     CouponDetailView.as_view(),  name='coupon_detail'),

    # ──────────────────────────────────────────────────────────
    # NOTIFICATIONS
    # GET  /api/admin/notifications/
    # GET  /api/admin/notifications/unread-count/
    # POST /api/admin/notifications/mark-all-read/
    # POST /api/admin/notifications/{id}/mark-read/
    # ──────────────────────────────────────────────────────────
    path('notifications/',                          NotificationListView.as_view(),         name='notification_list'),
    path('notifications/unread-count/',             UnreadNotificationCountView.as_view(),  name='notification_count'),
    path('notifications/mark-all-read/',            MarkNotificationReadView.as_view(),     name='notification_mark_all'),
    path('notifications/<int:pk>/mark-read/',       MarkNotificationReadView.as_view(),     name='notification_mark_one'),

    # ──────────────────────────────────────────────────────────
    # ACTIVITY LOGS
    # GET /api/admin/activity-logs/?action=&model_name=&date_from=&date_to=
    # ──────────────────────────────────────────────────────────
    path('activity-logs/', ActivityLogListView.as_view(), name='activity_logs'),
     path('attributes/',
         AttributeListView.as_view(),       name='attribute_list'),
    path('attributes/<int:pk>/',
         AttributeDetailView.as_view(),     name='attribute_detail'),
    path('attributes/<int:pk>/values/',
         AttributeValueListView.as_view(),  name='attribute_value_list'),
    path('attributes/<int:pk>/values/<int:value_pk>/',
         AttributeValueDetailView.as_view(), name='attribute_value_detail'),
         path('products/<int:pk>/generate-variants/', GenerateVariantsView.as_view()),
         path('orders/<int:pk>/delete/', DeleteOrderView.as_view()),

]