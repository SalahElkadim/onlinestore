from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    # Auth
    RegisterView, LoginView, LogoutView,
    ProfileView, ChangePasswordView,

    # Categories
    CategoryListView,

    # Products
    ProductListView, ProductDetailView, FindVariantView,

    # Cart
    CartView, AddToCartView, UpdateCartItemView, ClearCartView,

    # Orders
    CheckoutView, MyOrdersView, OrderDetailView, CancelOrderView,

    # Reviews
    ProductReviewListView, CreateReviewView, DeleteReviewView,

    # Coupon
    ValidateCouponView,
)

app_name = 'store'

urlpatterns = [

    # ──────────────────────────────────────────────────────────
    # AUTH
    # POST  /api/store/auth/register/
    # POST  /api/store/auth/login/
    # POST  /api/store/auth/logout/
    # POST  /api/store/auth/token/refresh/
    # GET   /api/store/auth/profile/
    # PATCH /api/store/auth/profile/
    # POST  /api/store/auth/change-password/
    # ──────────────────────────────────────────────────────────
    path('auth/register/',        RegisterView.as_view(),       name='register'),
    path('auth/login/',           LoginView.as_view(),          name='login'),
    path('auth/logout/',          LogoutView.as_view(),         name='logout'),
    path('auth/token/refresh/',   TokenRefreshView.as_view(),   name='token_refresh'),
    path('auth/profile/',         ProfileView.as_view(),        name='profile'),
    path('auth/change-password/', ChangePasswordView.as_view(), name='change_password'),

    # ──────────────────────────────────────────────────────────
    # CATEGORIES
    # GET /api/store/categories/
    # ──────────────────────────────────────────────────────────
    path('categories/', CategoryListView.as_view(), name='category_list'),

    # ──────────────────────────────────────────────────────────
    # PRODUCTS
    # GET /api/store/products/?category=&search=&min_price=&max_price=&in_stock=true
    # GET /api/store/products/{slug}/
    # ──────────────────────────────────────────────────────────
    path('products/',             ProductListView.as_view(),   name='product_list'),
    path('products/<str:slug>/', ProductDetailView.as_view(), name='product_detail'),

    # ──────────────────────────────────────────────────────────
    # CART
    # GET    /api/store/cart/
    # POST   /api/store/cart/add/
    # PATCH  /api/store/cart/items/{id}/
    # DELETE /api/store/cart/items/{id}/
    # DELETE /api/store/cart/clear/
    # ──────────────────────────────────────────────────────────
    path('cart/',                  CartView.as_view(),           name='cart'),
    path('cart/add/',              AddToCartView.as_view(),      name='cart_add'),
    path('cart/items/<int:item_id>/', UpdateCartItemView.as_view(), name='cart_item'),
    path('cart/clear/',            ClearCartView.as_view(),      name='cart_clear'),

    # ──────────────────────────────────────────────────────────
    # CHECKOUT & ORDERS
    # POST /api/store/checkout/
    # GET  /api/store/orders/                  ← مسجلين فقط
    # GET  /api/store/orders/{order_number}/
    # POST /api/store/orders/{order_number}/cancel/
    # ──────────────────────────────────────────────────────────
    path('checkout/',                              CheckoutView.as_view(),  name='checkout'),
    path('orders/',                                MyOrdersView.as_view(),  name='my_orders'),
    path('orders/<str:order_number>/',             OrderDetailView.as_view(),  name='order_detail'),
    path('orders/<str:order_number>/cancel/',      CancelOrderView.as_view(), name='order_cancel'),

    # ──────────────────────────────────────────────────────────
    # REVIEWS
    # GET  /api/store/products/{slug}/reviews/
    # POST /api/store/products/{slug}/reviews/
    # DELETE /api/store/products/{slug}/reviews/{id}/
    # ──────────────────────────────────────────────────────────
    path('products/<slug:slug>/reviews/',
         ProductReviewListView.as_view(), name='product_reviews'),
    path('products/<slug:slug>/reviews/add/',
         CreateReviewView.as_view(),      name='add_review'),
    path('products/<slug:slug>/reviews/<int:review_id>/delete/',
         DeleteReviewView.as_view(),      name='delete_review'),

    # ──────────────────────────────────────────────────────────
    # COUPON
    # POST /api/store/coupons/validate/
    # ──────────────────────────────────────────────────────────
    path('coupons/validate/', ValidateCouponView.as_view(), name='coupon_validate'),
    # store/urls.py — أضف السطر ده
path('products/<slug:slug>/find-variant/', FindVariantView.as_view()),
]