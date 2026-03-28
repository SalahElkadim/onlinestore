from rest_framework import status, filters
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken

from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404
from django.db.models import Avg

from dashboard.models import Product, Category, Order, OrderItem
from .models import Cart, CartItem, ProductReview, OrderCancellation
from .serializers import (
    CustomerRegisterSerializer, CustomerLoginSerializer,
    CustomerProfileSerializer, ChangePasswordSerializer,
    StoreCategorySerializer,
    StoreProductListSerializer, StoreProductDetailSerializer,
    CartSerializer, AddToCartSerializer, UpdateCartItemSerializer,
    CheckoutSerializer, StoreOrderListSerializer, StoreOrderDetailSerializer,
    CancelOrderSerializer,
    ProductReviewSerializer, CreateReviewSerializer,
    StoreCouponValidateSerializer,
)
from .permissions import IsCustomer


# ============================================================
# MIXINS
# ============================================================

class StandardResponseMixin:
    def success(self, data=None, message='', status_code=status.HTTP_200_OK):
        return Response({'success': True, 'message': message, 'data': data}, status=status_code)

    def error(self, message='', errors=None, status_code=status.HTTP_400_BAD_REQUEST):
        return Response({'success': False, 'message': message, 'errors': errors}, status=status_code)


class CartMixin:
    def get_cart(self, request, cart_id=None):
        if request.user.is_authenticated:
            cart, _ = Cart.objects.get_or_create(user=request.user)
            return cart

        # Guest
        if cart_id:
            try:
                return Cart.objects.get(id=cart_id, user=None)
            except Cart.DoesNotExist:
                pass

        return Cart.objects.create()


# ============================================================
# 1. AUTH VIEWS
# ============================================================

class RegisterView(StandardResponseMixin, APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = CustomerRegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return self.error('فشل التسجيل.', serializer.errors)
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        return self.success({
            'access':  str(refresh.access_token),
            'refresh': str(refresh),
            'user': {
                'id':    user.id,
                'name':  user.get_full_name(),
                'email': user.email,
            }
        }, 'تم التسجيل بنجاح.', status.HTTP_201_CREATED)


class LoginView(StandardResponseMixin, APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = CustomerLoginSerializer(data=request.data)
        if not serializer.is_valid():
            return self.error('فشل تسجيل الدخول.', serializer.errors, status.HTTP_401_UNAUTHORIZED)
        user = serializer.validated_data['user']
        refresh = RefreshToken.for_user(user)
        return self.success({
            'access':  str(refresh.access_token),
            'refresh': str(refresh),
            'user': {
                'id':     user.id,
                'name':   user.get_full_name(),
                'email':  user.email,
                'avatar': user.avatar.url if user.avatar else None,
            }
        }, 'تم تسجيل الدخول بنجاح.')


class LogoutView(StandardResponseMixin, APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            token = RefreshToken(request.data.get('refresh'))
            token.blacklist()
            return self.success(message='تم تسجيل الخروج بنجاح.')
        except Exception:
            return self.error('رمز غير صالح.')


class ProfileView(StandardResponseMixin, APIView):
    permission_classes = [IsAuthenticated, IsCustomer]

    def get(self, request):
        return self.success(CustomerProfileSerializer(request.user).data)

    def patch(self, request):
        serializer = CustomerProfileSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return self.success(serializer.data, 'تم تحديث البيانات.')
        return self.error('فشل التحديث.', serializer.errors)


class ChangePasswordView(StandardResponseMixin, APIView):
    permission_classes = [IsAuthenticated, IsCustomer]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        if not serializer.is_valid():
            return self.error('فشل تغيير كلمة المرور.', serializer.errors)
        request.user.set_password(serializer.validated_data['new_password'])
        request.user.save()
        return self.success(message='تم تغيير كلمة المرور بنجاح.')


# ============================================================
# 2. CATEGORY VIEWS
# ============================================================

class CategoryListView(StandardResponseMixin, APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        categories = Category.objects.filter(is_active=True, parent__isnull=True)
        serializer = StoreCategorySerializer(categories, many=True)
        return self.success(serializer.data)


# ============================================================
# 3. PRODUCT VIEWS
# ============================================================

class ProductListView(StandardResponseMixin, ListAPIView):
    permission_classes = [AllowAny]
    serializer_class   = StoreProductListSerializer
    filter_backends    = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields   = ['category']
    search_fields      = ['name', 'description']
    ordering_fields    = ['price', 'created_at']
    ordering           = ['-created_at']

    def get_queryset(self):
        qs = Product.objects.filter(
            status=Product.Status.ACTIVE
        ).select_related('category').prefetch_related('images', 'variants', 'reviews')

        min_price = self.request.query_params.get('min_price')
        max_price = self.request.query_params.get('max_price')
        in_stock  = self.request.query_params.get('in_stock')

        if min_price:
            qs = qs.filter(price__gte=min_price)
        if max_price:
            qs = qs.filter(price__lte=max_price)
        if in_stock == 'true':
            qs = qs.filter(variants__stock__gt=0).distinct()

        return qs

    def list(self, request, *args, **kwargs):
        queryset   = self.filter_queryset(self.get_queryset())
        page       = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page or queryset, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return self.success(serializer.data)


class ProductDetailView(StandardResponseMixin, APIView):
    permission_classes = [AllowAny]

    def get(self, request, slug):
        product = get_object_or_404(
            Product.objects.select_related('category').prefetch_related(
                'images', 'variants__attribute_values__attribute', 'reviews__user'
            ),
            slug=slug,
            status=Product.Status.ACTIVE
        )
        return self.success(StoreProductDetailSerializer(product).data)


# ============================================================
# 4. CART VIEWS
# ============================================================

class CartView(StandardResponseMixin, CartMixin, APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        cart_id = request.query_params.get('cart_id')
        cart = self.get_cart(request, cart_id=int(cart_id) if cart_id else None)
        return self.success(CartSerializer(cart).data)


class AddToCartView(StandardResponseMixin, CartMixin, APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = AddToCartSerializer(data=request.data)
        if not serializer.is_valid():
            return self.error('بيانات غير صحيحة.', serializer.errors)
        cart = self.get_cart(request, cart_id=serializer.validated_data.get('cart_id'))
        product = serializer.validated_data['product']
        variant = serializer.validated_data['variant']
        qty     = serializer.validated_data['quantity']

        # لو في variant
        if variant:
            item, created = CartItem.objects.get_or_create(
                cart=cart,
                variant=variant,
                defaults={'product': product, 'quantity': 0}
            )
        else:
            # منتج بدون variant
            item, created = CartItem.objects.get_or_create(
                cart=cart,
                product=product,
                variant=None,
                defaults={'quantity': 0}
            )

        item.quantity += qty
        item.save()

        # أعد جلب الـ cart عشان الـ serializer يشوف التحديثات
        cart.refresh_from_db()
        return self.success(CartSerializer(cart).data, 'تمت الإضافة للسلة.', status.HTTP_201_CREATED)

class UpdateCartItemView(StandardResponseMixin, CartMixin, APIView):
    permission_classes = [AllowAny]

    def get_cart_by_id_or_session(self, request):
        cart_id = request.query_params.get('cart_id')
        if cart_id:
            from django.shortcuts import get_object_or_404
            return get_object_or_404(Cart, id=cart_id)
        return self.get_cart(request)

    def patch(self, request, item_id):
        cart = self.get_cart_by_id_or_session(request)

        try:
            item = CartItem.objects.get(id=item_id, cart=cart)
        except CartItem.DoesNotExist:
            return self.error('المنتج غير موجود في السلة.')

        serializer = UpdateCartItemSerializer(data=request.data)
        if not serializer.is_valid():
            return self.error('بيانات غير صحيحة.', serializer.errors)

        new_qty = serializer.validated_data['quantity']

        if item.variant and item.variant.stock < new_qty:
            return self.error(f"الكمية المتاحة: {item.variant.stock} فقط.")

        item.quantity = new_qty
        item.save()
        cart.refresh_from_db()
        return self.success(CartSerializer(cart).data, 'تم تحديث الكمية.')

    def delete(self, request, item_id):
        cart = self.get_cart_by_id_or_session(request)

        try:
            item = CartItem.objects.get(id=item_id, cart=cart)
        except CartItem.DoesNotExist:
            return self.error('المنتج غير موجود في السلة.')

        item.delete()
        cart.refresh_from_db()
        return self.success(CartSerializer(cart).data, 'تم حذف الأيتم.')


class ClearCartView(StandardResponseMixin, CartMixin, APIView):
    permission_classes = [AllowAny]

    def delete(self, request):
        cart_id = request.query_params.get('cart_id')
        if cart_id:
            from django.shortcuts import get_object_or_404
            cart = get_object_or_404(Cart, id=cart_id)
        else:
            cart = self.get_cart(request)
        cart.items.all().delete()
        return self.success(message='تم تفريغ السلة.')


# ============================================================
# 5. CHECKOUT & ORDER VIEWS
# ============================================================

class CheckoutView(StandardResponseMixin, APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = CheckoutSerializer(data=request.data, context={'request': request})
        if not serializer.is_valid():
            return self.error('بيانات غير صحيحة.', serializer.errors)

        order = serializer.save()

        from dashboard.utils import create_notification
        create_notification('new_order', f'طلب جديد #{order.order_number} تم استلامه!')

        return self.success(
            StoreOrderDetailSerializer(order).data,
            'تم إنشاء الطلب بنجاح.',
            status.HTTP_201_CREATED
        )


class MyOrdersView(StandardResponseMixin, ListAPIView):
    permission_classes = [IsAuthenticated, IsCustomer]
    serializer_class   = StoreOrderListSerializer

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).order_by('-created_at')

    def list(self, request, *args, **kwargs):
        queryset   = self.get_queryset()
        page       = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page or queryset, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response({'success': True, 'data': serializer.data})


class OrderDetailView(StandardResponseMixin, APIView):
    permission_classes = [AllowAny]

    def get(self, request, order_number):
        if request.user.is_authenticated:
            order = get_object_or_404(Order, order_number=order_number, user=request.user)
        else:
            order = get_object_or_404(Order, order_number=order_number, user__isnull=True)
        return self.success(StoreOrderDetailSerializer(order).data)


class CancelOrderView(StandardResponseMixin, APIView):
    permission_classes = [AllowAny]

    def post(self, request, order_number):
        if request.user.is_authenticated:
            order = get_object_or_404(Order, order_number=order_number, user=request.user)
        else:
            order = get_object_or_404(Order, order_number=order_number, user__isnull=True)

        cancellable_statuses = [Order.Status.PENDING, Order.Status.CONFIRMED]
        if order.status not in cancellable_statuses:
            return self.error(f"لا يمكن إلغاء الطلب في حالة '{order.get_status_display()}'.")

        serializer = CancelOrderSerializer(data=request.data)
        if not serializer.is_valid():
            return self.error('بيانات غير صحيحة.', serializer.errors)

        order.status = Order.Status.CANCELLED
        order.save()

        for item in order.items.all():
            if item.variant:
                item.variant.stock += item.quantity
                item.variant.save()

        OrderCancellation.objects.create(
            order=order,
            reason=serializer.validated_data['reason'],
            cancelled_by=request.user if request.user.is_authenticated else None,
        )

        return self.success(StoreOrderDetailSerializer(order).data, 'تم إلغاء الطلب بنجاح.')


# ============================================================
# 6. REVIEW VIEWS
# ============================================================

class ProductReviewListView(StandardResponseMixin, APIView):
    permission_classes = [AllowAny]

    def get(self, request, slug):
        product = get_object_or_404(Product, slug=slug, status=Product.Status.ACTIVE)
        reviews = ProductReview.objects.filter(
            product=product, is_approved=True
        ).select_related('user').order_by('-created_at')

        avg_rating = reviews.aggregate(avg=Avg('rating'))['avg']

        return self.success({
            'avg_rating':    round(avg_rating, 1) if avg_rating else None,
            'total_reviews': reviews.count(),
            'reviews':       ProductReviewSerializer(reviews, many=True).data,
        })


class CreateReviewView(StandardResponseMixin, APIView):
    permission_classes = [IsAuthenticated, IsCustomer]

    def post(self, request, slug):
        product = get_object_or_404(Product, slug=slug, status=Product.Status.ACTIVE)
        serializer = CreateReviewSerializer(
            data=request.data,
            context={'request': request, 'product': product}
        )
        if not serializer.is_valid():
            return self.error('فشل إضافة التقييم.', serializer.errors)

        review = serializer.save()
        return self.success(
            ProductReviewSerializer(review).data,
            'تم إضافة تقييمك بنجاح.',
            status.HTTP_201_CREATED
        )


class DeleteReviewView(StandardResponseMixin, APIView):
    permission_classes = [IsAuthenticated, IsCustomer]

    def delete(self, request, slug, review_id):
        product = get_object_or_404(Product, slug=slug)
        review  = get_object_or_404(ProductReview, id=review_id, product=product, user=request.user)
        review.delete()
        return self.success(message='تم حذف التقييم بنجاح.')


# ============================================================
# 7. COUPON VIEW
# ============================================================

class ValidateCouponView(StandardResponseMixin, APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = StoreCouponValidateSerializer(data=request.data)
        if not serializer.is_valid():
            return self.error('كوبون غير صالح.', serializer.errors)

        data = serializer.validated_data
        return self.success({
            'discount_amount': data['discount_amount'],
            'final_total':     data['final_total'],
            'coupon': {
                'code':          data['coupon'].code,
                'discount_type': data['coupon'].discount_type,
                'value':         data['coupon'].value,
            }
        })