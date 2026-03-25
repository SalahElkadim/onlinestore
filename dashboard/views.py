from django.db.models import Sum, Count, Avg, Q, F
from django.db.models.functions import TruncDate, TruncMonth
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model

from rest_framework import status, filters
from rest_framework.views import APIView
from rest_framework.generics import (
    ListAPIView, RetrieveAPIView,
    CreateAPIView, UpdateAPIView, DestroyAPIView,
    ListCreateAPIView, RetrieveUpdateDestroyAPIView,
)
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView

from django_filters.rest_framework import DjangoFilterBackend
from datetime import timedelta
from decimal import Decimal

from .models import (
    User, AdminRole, StaffProfile,
    Category,
    Product, ProductImage, ProductVariant, Attribute, AttributeValue,
    Coupon,
    Order, OrderItem,
    Payment,
    Notification,
    ActivityLog,
)
from .serializers import (
    LoginSerializer, ChangePasswordSerializer,
    AdminRoleSerializer, UserListSerializer, UserDetailSerializer, CreateAdminUserSerializer,
    CategoryListSerializer, CategoryDetailSerializer, CategoryWriteSerializer,
    ProductListSerializer, ProductDetailSerializer, ProductWriteSerializer,
    ProductVariantSerializer, AttributeSerializer, AttributeValueSerializer,
    ProductImageSerializer,
    CouponSerializer, ValidateCouponSerializer,
    OrderListSerializer, OrderDetailSerializer, OrderCreateSerializer, UpdateOrderStatusSerializer,
    PaymentSerializer,
    NotificationSerializer,
    ActivityLogSerializer,
    DashboardStatsSerializer, InventoryAlertSerializer,
    TopProductSerializer, TopCustomerSerializer, SalesChartPointSerializer,
)
from .permissions import IsAdminOrStaff, IsAdminOnly, HasModulePermission
from .utils import log_activity, create_notification, get_client_ip
from django.db.models import Sum, Count, Avg, Q, F, OuterRef, Subquery, IntegerField
from django.db.models.functions import Coalesce, TruncDate, TruncMonth
from erp.models import WarehouseStock
User = get_user_model()


# ============================================================
# MIXINS
# ============================================================

class ActivityLogMixin:
    """Auto-logs create/update/delete actions."""
    log_model = ''

    def perform_create(self, serializer):
        instance = serializer.save()
        log_activity(self.request, 'create', self.log_model, instance)

    def perform_update(self, serializer):
        instance = serializer.save()
        log_activity(self.request, 'update', self.log_model, instance)

    def perform_destroy(self, instance):
        log_activity(self.request, 'delete', self.log_model, instance)
        instance.delete()


class StandardResponseMixin:
    """Wraps responses in a consistent envelope."""

    def success(self, data=None, message='', status_code=status.HTTP_200_OK):
        return Response({
            'success': True,
            'message': message,
            'data': data,
        }, status=status_code)

    def error(self, message='', errors=None, status_code=status.HTTP_400_BAD_REQUEST):
        return Response({
            'success': False,
            'message': message,
            'errors': errors,
        }, status=status_code)


# ============================================================
# 1. AUTH VIEWS
# ============================================================

class AdminLoginView(StandardResponseMixin, APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return self.error('Login failed.', serializer.errors, status.HTTP_401_UNAUTHORIZED)

        user = serializer.validated_data['user']
        refresh = RefreshToken.for_user(user)

        log_activity(request, 'login', 'User', user)

        return self.success({
            'access':  str(refresh.access_token),
            'refresh': str(refresh),
            'user': {
                'id':    user.id,
                'name':  user.get_full_name(),
                'email': user.email,
                'role':  user.role,
                'avatar': user.avatar.url if user.avatar else None,
            }
        }, 'Login successful.')


class AdminLogoutView(StandardResponseMixin, APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            token = RefreshToken(refresh_token)
            token.blacklist()
            log_activity(request, 'logout', 'User', request.user)
            return self.success(message='Logged out successfully.')
        except Exception:
            return self.error('Invalid or expired token.')


class ChangePasswordView(StandardResponseMixin, APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        if not serializer.is_valid():
            return self.error('Password change failed.', serializer.errors)
        request.user.set_password(serializer.validated_data['new_password'])
        request.user.save()
        return self.success(message='Password changed successfully.')


class MeView(StandardResponseMixin, APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserDetailSerializer(request.user)
        return self.success(serializer.data)

    def patch(self, request):
        serializer = UserDetailSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return self.success(serializer.data, 'Profile updated.')
        return self.error('Update failed.', serializer.errors)


# ============================================================
# 2. DASHBOARD VIEWS
# ============================================================

class DashboardStatsView(StandardResponseMixin, APIView):
    permission_classes = [IsAdminOrStaff]

    def get(self, request):
        period = request.query_params.get('period', '30')  # days
        try:
            days = int(period)
        except ValueError:
            days = 30

        now        = timezone.now()
        start_date = now - timedelta(days=days)
        prev_start = start_date - timedelta(days=days)

        # ── KPIs ──────────────────────────────────────────────
        paid_orders = Order.objects.filter(payment_status=Order.PaymentStatus.PAID)

        current_revenue = paid_orders.filter(
            created_at__gte=start_date
        ).aggregate(total=Sum('total_price'))['total'] or Decimal('0')

        prev_revenue = paid_orders.filter(
            created_at__gte=prev_start, created_at__lt=start_date
        ).aggregate(total=Sum('total_price'))['total'] or Decimal('0')

        current_orders = Order.objects.filter(created_at__gte=start_date).count()
        prev_orders    = Order.objects.filter(
            created_at__gte=prev_start, created_at__lt=start_date
        ).count()

        current_customers = User.objects.filter(
            role=User.Role.CUSTOMER, created_at__gte=start_date
        ).count()
        prev_customers = User.objects.filter(
            role=User.Role.CUSTOMER,
            created_at__gte=prev_start, created_at__lt=start_date
        ).count()

        def pct_change(current, previous):
            if previous == 0:
                return 100.0 if current > 0 else 0.0
            return round(((current - previous) / previous) * 100, 1)

        # ── Sales Chart (daily) ────────────────────────────────
        chart_qs = (
            paid_orders
            .filter(created_at__gte=start_date)
            .annotate(date=TruncDate('created_at'))
            .values('date')
            .annotate(revenue=Sum('total_price'), orders=Count('id'))
            .order_by('date')
        )

        # ── Top Products ───────────────────────────────────────
        top_products_qs = (
            OrderItem.objects
            .filter(order__created_at__gte=start_date, order__payment_status=Order.PaymentStatus.PAID)
            .values('product__id', 'product__name')
            .annotate(
                total_sold=Sum('quantity'),
                total_revenue=Sum(F('unit_price') * F('quantity'))
            )
            .order_by('-total_revenue')[:10]
        )
        top_products = []
        for p in top_products_qs:
            product = Product.objects.filter(
                id=p['product__id']
            ).prefetch_related('images').first()  # ← ضيف prefetch_related

            img = None
            if product:
                img = product.images.filter(is_primary=True).first() or product.images.first()

            top_products.append({
                'id':            p['product__id'],
                'name':          p['product__name'],
                'image':         img.image.url if img else None,  # ← .url مباشرة
                'total_sold':    p['total_sold'],
                'total_revenue': p['total_revenue'],
            })

        # ── Top Customers ──────────────────────────────────────
        top_customers_qs = (
            Order.objects
            .filter(
                created_at__gte=start_date,
                payment_status=Order.PaymentStatus.PAID,
                user__isnull=False
            )
            .values('user__id', 'user__first_name', 'user__last_name', 'user__email')
            .annotate(total_orders=Count('id'), total_spent=Sum('total_price'))
            .order_by('-total_spent')[:10]
        )
        top_customers = [{
            'id':           c['user__id'],
            'full_name':    f"{c['user__first_name']} {c['user__last_name']}".strip(),
            'email':        c['user__email'],
            'total_orders': c['total_orders'],
            'total_spent':  c['total_spent'],
        } for c in top_customers_qs]

        # ── Low Stock ──────────────────────────────────────────
        stock_subquery = WarehouseStock.objects.filter(
            variant=OuterRef('pk')
        ).values('variant').annotate(
            total=Sum('quantity')
        ).values('total')

        low_stock_count = (
            ProductVariant.objects
            .annotate(
                real_stock=Coalesce(
                    Subquery(stock_subquery, output_field=IntegerField()),
                    0
                )
            )
            .filter(real_stock__gt=0, real_stock__lte=5)
            .count()
        )

        # ── Assemble Response ──────────────────────────────────
        data = {
            'total_revenue':    current_revenue,
            'total_orders':     current_orders,
            'total_customers':  current_customers,
            'total_products':   Product.objects.filter(status=Product.Status.ACTIVE).count(),
            'pending_orders':   Order.objects.filter(status=Order.Status.PENDING).count(),
            'low_stock_count':  low_stock_count,
            'revenue_change':   pct_change(current_revenue, prev_revenue),
            'orders_change':    pct_change(current_orders, prev_orders),
            'customers_change': pct_change(current_customers, prev_customers),
            'sales_chart':      list(chart_qs),
            'top_products':     top_products,
            'top_customers':    top_customers,
            'recent_orders':    OrderListSerializer(
                Order.objects.select_related('user').order_by('-created_at')[:10], many=True
            ).data,
            'recent_notifications': NotificationSerializer(
                Notification.objects.filter(is_read=False).order_by('-created_at')[:10], many=True
            ).data,
        }
        return self.success(data)

class InventoryAlertsView(StandardResponseMixin, APIView):
    permission_classes = [IsAdminOrStaff]

    def get(self, request):
        alert_type = request.query_params.get('type', 'all')

        from django.db.models import Sum, OuterRef, Subquery, IntegerField
        from django.db.models.functions import Coalesce
        from erp.models import WarehouseStock  # أو أي اسم الـ app بتاعك

        # حساب الـ stock الحقيقي من WarehouseStock
        stock_subquery = WarehouseStock.objects.filter(
            variant=OuterRef('pk')
        ).values('variant').annotate(
            total=Sum('quantity')
        ).values('total')

        qs = (
            ProductVariant.objects
            .select_related('product')
            .prefetch_related('attribute_values')
            .annotate(
                real_stock=Coalesce(
                    Subquery(stock_subquery, output_field=IntegerField()),
                    0
                )
            )
        )

        if alert_type == 'low':
            qs = qs.filter(real_stock__gt=0, real_stock__lte=5)
        elif alert_type == 'out':
            qs = qs.filter(real_stock=0)
        else:  # all
            qs = qs.filter(real_stock__lte=5)

        serializer = InventoryAlertSerializer(qs, many=True)
        return self.success(serializer.data)


# ============================================================
# 3. USER VIEWS
# ============================================================

class UserListView(StandardResponseMixin, ListAPIView):
    permission_classes = [IsAdminOrStaff]
    serializer_class   = UserListSerializer
    filter_backends    = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields   = ['role', 'is_blocked', 'is_active']
    search_fields      = ['email', 'first_name', 'last_name', 'phone']
    ordering_fields    = ['created_at', 'email']
    ordering           = ['-created_at']

    def get_queryset(self):
        return User.objects.filter(role=User.Role.CUSTOMER)


class UserDetailView(StandardResponseMixin, RetrieveAPIView):
    permission_classes = [IsAdminOrStaff]
    serializer_class   = UserDetailSerializer
    queryset           = User.objects.all()


class UserBlockToggleView(StandardResponseMixin, APIView):
    permission_classes = [IsAdminOnly]

    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        if user.is_admin:
            return self.error('Cannot block an admin account.')
        user.is_blocked = not user.is_blocked
        user.save()
        action = 'blocked' if user.is_blocked else 'unblocked'
        log_activity(request, 'update', 'User', user)
        return self.success({'is_blocked': user.is_blocked}, f'User {action} successfully.')


class AdminUserListView(StandardResponseMixin, ListCreateAPIView):
    permission_classes = [IsAdminOnly]
    filter_backends    = [filters.SearchFilter]
    search_fields      = ['email', 'first_name', 'last_name']

    def get_queryset(self):
        return User.objects.filter(role__in=[User.Role.ADMIN, User.Role.STAFF])

    def get_serializer_class(self):
        return CreateAdminUserSerializer if self.request.method == 'POST' else UserListSerializer

    def create(self, request, *args, **kwargs):
        serializer = CreateAdminUserSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            log_activity(request, 'create', 'User', user)
            return self.success(UserDetailSerializer(user).data, 'Admin user created.', status.HTTP_201_CREATED)
        return self.error('Creation failed.', serializer.errors)


class AdminRoleListView(StandardResponseMixin, ListCreateAPIView):
    permission_classes = [IsAdminOnly]
    serializer_class   = AdminRoleSerializer
    queryset           = AdminRole.objects.all()


# ============================================================
# 4. CATEGORY VIEWS
# ============================================================

class CategoryListView(StandardResponseMixin, ListCreateAPIView):
    permission_classes = [IsAdminOrStaff]
    filter_backends    = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields   = ['is_active', 'parent']
    search_fields      = ['name']

    def get_queryset(self):
        root_only = self.request.query_params.get('root_only', False)
        qs = Category.objects.prefetch_related('children').select_related('parent')
        if root_only:
            qs = qs.filter(parent__isnull=True)
        return qs

    def get_serializer_class(self):
        return CategoryWriteSerializer if self.request.method == 'POST' else CategoryListSerializer

    def create(self, request, *args, **kwargs):
        serializer = CategoryWriteSerializer(data=request.data)
        if serializer.is_valid():
            category = serializer.save()
            log_activity(request, 'create', 'Category', category)
            return self.success(CategoryDetailSerializer(category).data, 'Category created.', status.HTTP_201_CREATED)
        return self.error('Creation failed.', serializer.errors)


class CategoryDetailView(StandardResponseMixin, RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAdminOrStaff]
    queryset           = Category.objects.prefetch_related('children').select_related('parent')

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return CategoryWriteSerializer
        return CategoryDetailSerializer

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = CategoryWriteSerializer(instance, data=request.data, partial=partial)
        if serializer.is_valid():
            category = serializer.save()
            log_activity(request, 'update', 'Category', category)
            return self.success(CategoryDetailSerializer(category).data, 'Category updated.')
        return self.error('Update failed.', serializer.errors)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.products.exists():
            return self.error('Cannot delete a category that has products.')
        if instance.children.exists():
            return self.error('Cannot delete a category that has subcategories.')
        log_activity(request, 'delete', 'Category', instance)
        instance.delete()
        return self.success(message='Category deleted.')


# ============================================================
# 5. PRODUCT VIEWS
# ============================================================

class ProductListView(StandardResponseMixin, ListCreateAPIView):
    permission_classes = [IsAdminOrStaff]
    parser_classes     = [MultiPartParser, FormParser, JSONParser]
    filter_backends    = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields   = ['status', 'category']
    search_fields      = ['name', 'sku', 'description']
    ordering_fields    = ['price', 'created_at', 'name']
    ordering           = ['-created_at']

    def get_queryset(self):
        qs = Product.objects.select_related('category').prefetch_related('images', 'variants')
        # Extra filters
        in_stock = self.request.query_params.get('in_stock')
        min_price = self.request.query_params.get('min_price')
        max_price = self.request.query_params.get('max_price')
        if in_stock == 'true':
            qs = qs.filter(variants__stock__gt=0).distinct()
        if min_price:
            qs = qs.filter(price__gte=min_price)
        if max_price:
            qs = qs.filter(price__lte=max_price)
        return qs

    def get_serializer_class(self):
        return ProductWriteSerializer if self.request.method == 'POST' else ProductListSerializer

    def create(self, request, *args, **kwargs):
        serializer = ProductWriteSerializer(data=request.data)
        if serializer.is_valid():
            product = serializer.save()
            log_activity(request, 'create', 'Product', product)
            return self.success(
                ProductDetailSerializer(product).data,
                'Product created.',
                status.HTTP_201_CREATED
            )
        return self.error('Creation failed.', serializer.errors)


class ProductDetailView(StandardResponseMixin, RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAdminOrStaff]
    parser_classes     = [MultiPartParser, FormParser, JSONParser]
    queryset = Product.objects.select_related('category').prefetch_related(
        'images', 'variants__attribute_values__attribute'
    )

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return ProductWriteSerializer
        return ProductDetailSerializer

    def update(self, request, *args, **kwargs):
        partial  = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = ProductWriteSerializer(instance, data=request.data, partial=partial)
        if serializer.is_valid():
            product = serializer.save()
            log_activity(request, 'update', 'Product', product)
            return self.success(ProductDetailSerializer(product).data, 'Product updated.')
        return self.error('Update failed.', serializer.errors)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        log_activity(request, 'delete', 'Product', instance)
        instance.delete()
        return self.success(message='Product deleted.')


class ProductImageView(StandardResponseMixin, APIView):
    permission_classes = [IsAdminOrStaff]
    parser_classes     = [MultiPartParser, FormParser]

    def delete(self, request, pk, image_pk):
        image = get_object_or_404(ProductImage, pk=image_pk, product_id=pk)
        image.delete()
        return self.success(message='Image deleted.')

    def patch(self, request, pk, image_pk):
        """Set as primary image."""
        image = get_object_or_404(ProductImage, pk=image_pk, product_id=pk)
        ProductImage.objects.filter(product_id=pk).update(is_primary=False)
        image.is_primary = True
        image.save()
        return self.success(message='Primary image updated.')


# ── Variants ──────────────────────────────────────────────────

class ProductVariantListView(StandardResponseMixin, ListCreateAPIView):
    permission_classes = [IsAdminOrStaff]
    serializer_class   = ProductVariantSerializer

    def get_queryset(self):
        return ProductVariant.objects.filter(
            product_id=self.kwargs['pk']
        ).prefetch_related('attribute_values__attribute')

    def perform_create(self, serializer):
        product = get_object_or_404(Product, pk=self.kwargs['pk'])
        serializer.save(product=product)


class ProductVariantDetailView(StandardResponseMixin, RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAdminOrStaff]
    serializer_class   = ProductVariantSerializer

    def get_queryset(self):
        return ProductVariant.objects.filter(product_id=self.kwargs['pk'])

    def get_object(self):
        return get_object_or_404(
            ProductVariant,
            pk=self.kwargs['variant_pk'],
            product_id=self.kwargs['pk']
        )


class UpdateVariantStockView(StandardResponseMixin, APIView):
    permission_classes = [IsAdminOrStaff]

    def patch(self, request, pk, variant_pk):
        variant  = get_object_or_404(ProductVariant, pk=variant_pk, product_id=pk)
        new_stock = request.data.get('stock')
        if new_stock is None or int(new_stock) < 0:
            return self.error('Provide a valid non-negative stock value.')
        old_stock    = variant.stock
        variant.stock = int(new_stock)
        variant.save()

        # Notify if low or out
        if variant.is_out_of_stock:
            create_notification('out_of_stock', f'"{variant.product.name}" is out of stock!')
        elif variant.is_low_stock:
            create_notification('low_stock', f'"{variant.product.name}" stock is low ({variant.stock} left).')

        log_activity(request, 'update', 'ProductVariant', variant)
        return self.success({'old_stock': old_stock, 'new_stock': variant.stock}, 'Stock updated.')


# ── Attributes ────────────────────────────────────────────────

# ── Attributes ────────────────────────────────────────────────

class AttributeListView(StandardResponseMixin, ListCreateAPIView):
    permission_classes = [IsAdminOrStaff]
    serializer_class   = AttributeSerializer
    queryset           = Attribute.objects.prefetch_related('values')


class AttributeDetailView(StandardResponseMixin, DestroyAPIView):
    """DELETE /api/admin/attributes/{id}/"""
    permission_classes = [IsAdminOrStaff]
    queryset           = Attribute.objects.all()

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.values.filter(variants__isnull=False).exists():
            return self.error('لا يمكن حذف خاصية مرتبطة بـ variants موجودة.')
        log_activity(request, 'delete', 'Attribute', instance)
        instance.delete()
        return self.success(message='تم حذف الخاصية بنجاح.')


class AttributeValueListView(StandardResponseMixin, ListCreateAPIView):
    permission_classes = [IsAdminOrStaff]
    serializer_class   = AttributeValueSerializer

    def get_queryset(self):
        return AttributeValue.objects.filter(attribute_id=self.kwargs['pk'])

    def perform_create(self, serializer):
        attribute = get_object_or_404(Attribute, pk=self.kwargs['pk'])
        serializer.save(attribute=attribute)


class AttributeValueDetailView(StandardResponseMixin, DestroyAPIView):
    """DELETE /api/admin/attributes/{id}/values/{value_pk}/"""
    permission_classes = [IsAdminOrStaff]

    def get_object(self):
        return get_object_or_404(
            AttributeValue,
            pk=self.kwargs['value_pk'],
            attribute_id=self.kwargs['pk']
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.variants.exists():
            return self.error('لا يمكن حذف قيمة مرتبطة بـ variants موجودة.')
        log_activity(request, 'delete', 'AttributeValue', instance)
        instance.delete()
        return self.success(message='تم حذف القيمة بنجاح.')


# ============================================================
# 6. ORDER VIEWS
# ============================================================

class OrderListView(StandardResponseMixin, ListCreateAPIView):
    permission_classes = [IsAdminOrStaff]
    filter_backends    = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields   = ['status', 'payment_status', 'payment_method']
    search_fields      = ['order_number', 'shipping_name', 'shipping_phone', 'user__email']
    ordering_fields    = ['created_at', 'total_price']
    ordering           = ['-created_at']

    def get_queryset(self):
        qs = Order.objects.select_related('user', 'coupon').prefetch_related('items')

        # Date range filter
        date_from = self.request.query_params.get('date_from')
        date_to   = self.request.query_params.get('date_to')
        if date_from:
            qs = qs.filter(created_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(created_at__date__lte=date_to)

        # Price range filter
        min_price = self.request.query_params.get('min_price')
        max_price = self.request.query_params.get('max_price')
        if min_price:
            qs = qs.filter(total_price__gte=min_price)
        if max_price:
            qs = qs.filter(total_price__lte=max_price)

        return qs

    def get_serializer_class(self):
        return OrderCreateSerializer if self.request.method == 'POST' else OrderListSerializer

    def create(self, request, *args, **kwargs):
        serializer = OrderCreateSerializer(data=request.data)
        if serializer.is_valid():
            order = serializer.save()
            create_notification('new_order', f'New order #{order.order_number} received!')
            log_activity(request, 'create', 'Order', order)
            return self.success(OrderDetailSerializer(order).data, 'Order created.', status.HTTP_201_CREATED)
        return self.error('Order creation failed.', serializer.errors)


class OrderDetailView(StandardResponseMixin, RetrieveAPIView):
    permission_classes = [IsAdminOrStaff]
    serializer_class   = OrderDetailSerializer
    queryset = Order.objects.select_related('user', 'coupon').prefetch_related(
        'items__product', 'items__variant', 'payments'
    )


class UpdateOrderStatusView(StandardResponseMixin, APIView):
    permission_classes = [IsAdminOrStaff]

    def patch(self, request, pk):
        order      = get_object_or_404(Order, pk=pk)
        serializer = UpdateOrderStatusSerializer(order, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            log_activity(request, 'update', 'Order', order)
            return self.success(OrderDetailSerializer(order).data, 'Order status updated.')
        return self.error('Update failed.', serializer.errors)


class OrderStatsView(StandardResponseMixin, APIView):
    """Quick count summary by status for the sidebar/badges."""
    permission_classes = [IsAdminOrStaff]

    def get(self, request):
        data = Order.objects.values('status').annotate(count=Count('id'))
        result = {row['status']: row['count'] for row in data}
        return self.success(result)


class ExportOrdersView(StandardResponseMixin, APIView):
    """Export filtered orders as CSV."""
    permission_classes = [IsAdminOrStaff]

    def get(self, request):
        import csv
        from django.http import HttpResponse

        qs = Order.objects.select_related('user').prefetch_related('items')

        # Apply same date filters as OrderListView
        date_from = request.query_params.get('date_from')
        date_to   = request.query_params.get('date_to')
        status_f  = request.query_params.get('status')
        if date_from:
            qs = qs.filter(created_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(created_at__date__lte=date_to)
        if status_f:
            qs = qs.filter(status=status_f)

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="orders.csv"'

        writer = csv.writer(response)
        writer.writerow([
            'Order #', 'Date', 'Customer', 'Email',
            'Items', 'Subtotal', 'Discount', 'Total',
            'Payment Method', 'Payment Status', 'Status',
        ])
        for order in qs:
            writer.writerow([
                order.order_number,
                order.created_at.strftime('%Y-%m-%d %H:%M'),
                order.shipping_name,
                order.user.email if order.user else '',
                order.items.count(),
                order.subtotal,
                order.discount_amount,
                order.total_price,
                order.payment_method,
                order.payment_status,
                order.status,
            ])
        return response


# ============================================================
# 7. PAYMENT VIEWS
# ============================================================

class PaymentListView(StandardResponseMixin, ListAPIView):
    permission_classes = [IsAdminOrStaff]
    serializer_class   = PaymentSerializer
    filter_backends    = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields   = ['status', 'method']
    ordering           = ['-created_at']
    queryset           = Payment.objects.select_related('order')


class RefundView(StandardResponseMixin, APIView):
    permission_classes = [IsAdminOnly]

    def post(self, request, pk):
        payment = get_object_or_404(Payment, pk=pk)
        if payment.status == Payment.Status.REFUNDED:
            return self.error('This payment has already been refunded.')
        # Here you would call the payment gateway refund API
        # e.g., stripe.Refund.create(payment_intent=payment.transaction_id)
        payment.status = Payment.Status.REFUNDED
        payment.save()
        payment.order.payment_status = Order.PaymentStatus.REFUNDED
        payment.order.status         = Order.Status.REFUNDED
        payment.order.save()
        log_activity(request, 'update', 'Payment', payment)
        create_notification('refund', f'Refund processed for order #{payment.order.order_number}.')
        return self.success(PaymentSerializer(payment).data, 'Refund processed.')


# ============================================================
# 8. COUPON VIEWS
# ============================================================

class CouponListView(StandardResponseMixin, ListCreateAPIView):
    permission_classes = [IsAdminOrStaff]
    serializer_class   = CouponSerializer
    filter_backends    = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields   = ['is_active', 'discount_type']
    search_fields      = ['code']
    queryset           = Coupon.objects.all()

    def create(self, request, *args, **kwargs):
        serializer = CouponSerializer(data=request.data)
        if serializer.is_valid():
            coupon = serializer.save()
            log_activity(request, 'create', 'Coupon', coupon)
            return self.success(CouponSerializer(coupon).data, 'Coupon created.', status.HTTP_201_CREATED)
        return self.error('Creation failed.', serializer.errors)


class CouponDetailView(StandardResponseMixin, RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAdminOrStaff]
    serializer_class   = CouponSerializer
    queryset           = Coupon.objects.all()

    def update(self, request, *args, **kwargs):
        partial  = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = CouponSerializer(instance, data=request.data, partial=partial)
        if serializer.is_valid():
            coupon = serializer.save()
            log_activity(request, 'update', 'Coupon', coupon)
            return self.success(CouponSerializer(coupon).data, 'Coupon updated.')
        return self.error('Update failed.', serializer.errors)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        log_activity(request, 'delete', 'Coupon', instance)
        instance.delete()
        return self.success(message='Coupon deleted.')


class ValidateCouponView(StandardResponseMixin, APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ValidateCouponSerializer(data=request.data)
        if serializer.is_valid():
            return self.success({
                'coupon':          CouponSerializer(serializer.validated_data['coupon']).data,
                'discount_amount': serializer.validated_data['discount_amount'],
                'final_total':     serializer.validated_data['final_total'],
            })
        return self.error('Invalid coupon.', serializer.errors)


# ============================================================
# 9. NOTIFICATION VIEWS
# ============================================================

class NotificationListView(StandardResponseMixin, ListAPIView):
    permission_classes = [IsAdminOrStaff]
    serializer_class   = NotificationSerializer

    def get_queryset(self):
        qs = Notification.objects.order_by('-created_at')
        unread_only = self.request.query_params.get('unread')
        if unread_only == 'true':
            qs = qs.filter(is_read=False)
        return qs


class MarkNotificationReadView(StandardResponseMixin, APIView):
    permission_classes = [IsAdminOrStaff]

    def post(self, request, pk=None):
        if pk:
            notif = get_object_or_404(Notification, pk=pk)
            notif.is_read = True
            notif.save()
        else:
            # Mark all as read
            Notification.objects.filter(is_read=False).update(is_read=True)
        return self.success(message='Marked as read.')


class UnreadNotificationCountView(StandardResponseMixin, APIView):
    permission_classes = [IsAdminOrStaff]

    def get(self, request):
        count = Notification.objects.filter(is_read=False).count()
        return self.success({'unread_count': count})


# ============================================================
# 10. ACTIVITY LOG VIEW
# ============================================================

class ActivityLogListView(StandardResponseMixin, ListAPIView):
    permission_classes = [IsAdminOnly]
    serializer_class   = ActivityLogSerializer
    filter_backends    = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields   = ['action', 'model_name', 'admin']
    search_fields      = ['admin__email', 'object_repr']
    ordering           = ['-created_at']

    def get_queryset(self):
        qs = ActivityLog.objects.select_related('admin')
        date_from = self.request.query_params.get('date_from')
        date_to   = self.request.query_params.get('date_to')
        if date_from:
            qs = qs.filter(created_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(created_at__date__lte=date_to)
        return qs


# ============================================================
# 11. ANALYTICS VIEW
# ============================================================

class AnalyticsView(StandardResponseMixin, APIView):
    permission_classes = [IsAdminOrStaff]

    def get(self, request):
        period = request.query_params.get('period', '30')
        group  = request.query_params.get('group', 'day')   # day | month
        try:
            days = int(period)
        except ValueError:
            days = 30

        now        = timezone.now()
        start_date = now - timedelta(days=days)
        paid_orders = Order.objects.filter(
            payment_status=Order.PaymentStatus.PAID,
            created_at__gte=start_date
        )

        # Sales over time
        trunc_fn = TruncDate if group == 'day' else TruncMonth
        sales_over_time = (
            paid_orders
            .annotate(period=trunc_fn('created_at'))
            .values('period')
            .annotate(revenue=Sum('total_price'), orders=Count('id'))
            .order_by('period')
        )

        # Average order value
        avg_order_value = paid_orders.aggregate(avg=Avg('total_price'))['avg'] or 0

        # Orders by payment method
        by_payment_method = (
            paid_orders
            .values('payment_method')
            .annotate(count=Count('id'), total=Sum('total_price'))
        )

        # Orders by status
        by_status = (
            Order.objects
            .values('status')
            .annotate(count=Count('id'))
        )

        # Revenue by category
        by_category = (
            OrderItem.objects
            .filter(order__in=paid_orders)
            .values('product__category__name')
            .annotate(revenue=Sum(F('unit_price') * F('quantity')))
            .order_by('-revenue')[:10]
        )

        return self.success({
            'sales_over_time':     list(sales_over_time),
            'avg_order_value':     round(avg_order_value, 2),
            'by_payment_method':   list(by_payment_method),
            'by_status':           list(by_status),
            'revenue_by_category': list(by_category),
        })
    