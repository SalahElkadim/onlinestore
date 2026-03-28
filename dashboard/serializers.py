"""
============================================================
  DASHBOARD APPLICATION — serializers.py
  
  التغيير الأساسي في OrderCreateSerializer.create():
  - إزالة السطرين دول:
        variant.stock -= item['quantity']
        variant.save()
  - دلوقتي الخصم بيحصل بس من WarehouseStock عند الـ confirm
    عن طريق dashboard/signals.py → deduct_warehouse_stock_on_confirm
============================================================
"""

from rest_framework import serializers
from django.contrib.auth import authenticate
from django.utils import timezone
from .models import (
    User, AdminRole, StaffProfile,
    Category,
    Product, ProductImage, Attribute, AttributeValue, ProductVariant,
    Coupon,
    Order, OrderItem,
    Payment,
    Notification,
    ActivityLog, ProductVideo
)


# ============================================================
# HELPERS
# ============================================================

class TimestampMixin(serializers.Serializer):
    """Re-usable human-readable timestamps."""
    created_at = serializers.DateTimeField(read_only=True, format="%Y-%m-%d %H:%M")
    updated_at = serializers.DateTimeField(read_only=True, format="%Y-%m-%d %H:%M", required=False)


# ============================================================
# 1. AUTH SERIALIZERS
# ============================================================

class LoginSerializer(serializers.Serializer):
    email    = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        user = authenticate(username=data['email'], password=data['password'])
        if not user:
            raise serializers.ValidationError("Invalid email or password.")
        if user.is_blocked:
            raise serializers.ValidationError("This account has been blocked.")
        if user.role not in (User.Role.ADMIN, User.Role.STAFF):
            raise serializers.ValidationError("Access denied. Admin accounts only.")
        data['user'] = user
        return data


class ChangePasswordSerializer(serializers.Serializer):
    old_password     = serializers.CharField(write_only=True)
    new_password     = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError("New passwords do not match.")
        return data

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect.")
        return value


# ============================================================
# 2. USER SERIALIZERS
# ============================================================

class AdminRoleSerializer(serializers.ModelSerializer):
    class Meta:
        model  = AdminRole
        fields = ['id', 'name', 'permissions', 'created_at']


class UserListSerializer(serializers.ModelSerializer):
    """Lightweight – used in lists/dropdowns."""
    full_name    = serializers.SerializerMethodField()
    total_orders = serializers.SerializerMethodField()
    total_spent  = serializers.SerializerMethodField()

    class Meta:
        model  = User
        fields = [
            'id', 'full_name', 'email', 'phone', 'avatar',
            'role', 'is_blocked', 'is_active',
            'total_orders', 'total_spent', 'created_at',
        ]

    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username

    def get_total_orders(self, obj):
        return obj.orders.count()

    def get_total_spent(self, obj):
        from django.db.models import Sum
        result = obj.orders.filter(
            payment_status=Order.PaymentStatus.PAID
        ).aggregate(total=Sum('total_price'))
        return result['total'] or 0


class UserDetailSerializer(serializers.ModelSerializer):
    """Full profile – used in detail/create/update."""
    full_name     = serializers.SerializerMethodField()
    total_orders  = serializers.SerializerMethodField()
    total_spent   = serializers.SerializerMethodField()
    recent_orders = serializers.SerializerMethodField()

    class Meta:
        model  = User
        fields = [
            'id', 'username', 'first_name', 'last_name', 'full_name',
            'email', 'phone', 'avatar', 'role',
            'is_blocked', 'is_active',
            'total_orders', 'total_spent', 'recent_orders',
            'date_joined', 'created_at',
        ]
        read_only_fields = ['date_joined', 'created_at']

    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username

    def get_total_orders(self, obj):
        return obj.orders.count()

    def get_total_spent(self, obj):
        from django.db.models import Sum
        result = obj.orders.filter(
            payment_status=Order.PaymentStatus.PAID
        ).aggregate(total=Sum('total_price'))
        return result['total'] or 0

    def get_recent_orders(self, obj):
        orders = obj.orders.order_by('-created_at')[:5]
        return OrderListSerializer(orders, many=True).data


class CreateAdminUserSerializer(serializers.ModelSerializer):
    """Admin creates a new staff/admin user."""
    password         = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)
    role_id          = serializers.PrimaryKeyRelatedField(
        queryset=AdminRole.objects.all(), write_only=True, required=False
    )

    class Meta:
        model  = User
        fields = [
            'username', 'first_name', 'last_name',
            'email', 'phone', 'role',
            'password', 'confirm_password', 'role_id',
        ]

    def validate(self, data):
        if data['password'] != data.pop('confirm_password'):
            raise serializers.ValidationError("Passwords do not match.")
        return data

    def create(self, validated_data):
        role_obj = validated_data.pop('role_id', None)
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        if role_obj:
            StaffProfile.objects.create(user=user, admin_role=role_obj)
        return user


# ============================================================
# 3. CATEGORY SERIALIZERS
# ============================================================

class CategoryChildSerializer(serializers.ModelSerializer):
    """Used for nested rendering (one level deep)."""
    class Meta:
        model  = Category
        fields = ['id', 'name', 'slug', 'image', 'is_active']


class CategoryListSerializer(serializers.ModelSerializer):
    children_count = serializers.SerializerMethodField()
    products_count = serializers.SerializerMethodField()
    parent_name    = serializers.CharField(source='parent.name', read_only=True)

    class Meta:
        model  = Category
        fields = [
            'id', 'name', 'slug', 'image',
            'parent', 'parent_name',
            'is_active', 'children_count', 'products_count', 'created_at',
        ]

    def get_children_count(self, obj):
        return obj.children.count()

    def get_products_count(self, obj):
        return obj.products.count()


class CategoryDetailSerializer(serializers.ModelSerializer):
    children = CategoryChildSerializer(many=True, read_only=True)

    class Meta:
        model  = Category
        fields = [
            'id', 'name', 'slug', 'image',
            'parent', 'children',
            'is_active', 'created_at',
        ]
        read_only_fields = ['slug', 'created_at']


class CategoryWriteSerializer(serializers.ModelSerializer):
    """Create / Update category."""
    class Meta:
        model  = Category
        fields = ['name', 'parent', 'image', 'is_active']

    def validate_parent(self, value):
        if self.instance and value and value.id == self.instance.id:
            raise serializers.ValidationError("A category cannot be its own parent.")
        return value


# ============================================================
# 4. PRODUCT SERIALIZERS
# ============================================================

class AttributeValueSerializer(serializers.ModelSerializer):
    attribute_name = serializers.CharField(source='attribute.name', read_only=True)

    class Meta:
        model  = AttributeValue
        fields = ['id', 'attribute', 'attribute_name', 'value']
        read_only_fields = ['attribute', 'attribute_name']


class AttributeSerializer(serializers.ModelSerializer):
    values = AttributeValueSerializer(many=True, read_only=True)

    class Meta:
        model  = Attribute
        fields = ['id', 'name', 'values']


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model  = ProductImage
        fields = ['id', 'image', 'alt_text', 'is_primary', 'order']


class ProductVariantSerializer(serializers.ModelSerializer):
    attribute_values    = AttributeValueSerializer(many=True, read_only=True)
    attribute_value_ids = serializers.PrimaryKeyRelatedField(
        queryset=AttributeValue.objects.all(),
        many=True, write_only=True, source='attribute_values'
    )
    effective_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    is_low_stock    = serializers.BooleanField(read_only=True)
    is_out_of_stock = serializers.BooleanField(read_only=True)

    class Meta:
        model  = ProductVariant
        fields = [
            'id', 'product',
            'attribute_values', 'attribute_value_ids',
            'price_override', 'effective_price',
            'stock', 'sku', 'image',
            'is_active', 'is_low_stock', 'is_out_of_stock',
        ]
        read_only_fields = ['product']


class ProductListSerializer(serializers.ModelSerializer):
    """Lightweight – used in tables/lists."""
    category_name       = serializers.CharField(source='category.name', read_only=True)
    primary_image       = serializers.SerializerMethodField()
    total_stock         = serializers.IntegerField(read_only=True)
    discount_percentage = serializers.DecimalField(max_digits=5, decimal_places=1, read_only=True)

    class Meta:
        model  = Product
        fields = [
            'id', 'name', 'slug', 'sku',
            'price', 'discount_price', 'discount_percentage', 'effective_price',
            'category', 'category_name',
            'status', 'total_stock', 'is_in_stock',
            'primary_image', 'created_at',
        ]

    def get_primary_image(self, obj):
        img = obj.images.filter(is_primary=True).first() or obj.images.first()
        if not img:
            return None
        return img.image.build_url() if hasattr(img.image, 'build_url') else img.image.url


class ProductDetailSerializer(serializers.ModelSerializer):
    """Full product detail with variants and images."""
    images              = ProductImageSerializer(many=True, read_only=True)
    variants            = ProductVariantSerializer(many=True, read_only=True)
    category_name       = serializers.CharField(source='category.name', read_only=True)
    total_stock         = serializers.IntegerField(read_only=True)
    discount_percentage = serializers.DecimalField(max_digits=5, decimal_places=1, read_only=True)
    effective_price     = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model  = Product
        fields = [
            'id', 'name', 'slug', 'description', 'sku',
            'price', 'discount_price', 'discount_percentage', 'effective_price',
            'category', 'category_name',
            'status', 'total_stock', 'is_in_stock',
            'images', 'variants',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['slug', 'created_at', 'updated_at']


class ProductWriteSerializer(serializers.ModelSerializer):
    """Create / Update product."""
    uploaded_images = serializers.ListField(
        child=serializers.CharField(), write_only=True, required=False)
    uploaded_videos = serializers.ListField(
        child=serializers.CharField(), write_only=True, required=False
    )

    class Meta:
        model  = Product
        fields = [
            'name', 'description',
            'price', 'discount_price',
            'sku', 'category', 'status',
            'uploaded_images',
            'uploaded_videos',
        ]

    def validate_discount_price(self, value):
        price = self.initial_data.get('price') or (self.instance.price if self.instance else None)
        if price and value and float(value) >= float(price):
            raise serializers.ValidationError("Discount price must be less than the original price.")
        return value

    def create(self, validated_data):
        images_data = validated_data.pop('uploaded_images', [])
        videos_data = validated_data.pop('uploaded_videos', [])
        product = Product.objects.create(**validated_data)
        for i, url in enumerate(images_data):
            ProductImage.objects.create(
                product=product,
                image=url,
                is_primary=(i == 0),
                order=i
            )
        for i, url in enumerate(videos_data):
            ProductVideo.objects.create(
                product=product,
                video=url,
                order=i
            )
        return product

    def update(self, instance, validated_data):
        images_data = validated_data.pop('uploaded_images', [])
        videos_data = validated_data.pop('uploaded_videos', [])
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if images_data:
            for i, img in enumerate(images_data):
                ProductImage.objects.create(
                    product=instance, image=img,
                    is_primary=False, order=instance.images.count() + i
                )
        for i, vid in enumerate(videos_data):
            ProductVideo.objects.create(product=instance, video=vid, order=instance.videos.count() + i)
        return instance


# ============================================================
# 5. COUPON SERIALIZERS
# ============================================================

class CouponSerializer(serializers.ModelSerializer):
    is_valid              = serializers.BooleanField(read_only=True)
    remaining_uses        = serializers.SerializerMethodField()
    discount_type_display = serializers.CharField(source='get_discount_type_display', read_only=True)

    class Meta:
        model  = Coupon
        fields = [
            'id', 'code',
            'discount_type', 'discount_type_display', 'value',
            'min_order_value', 'max_uses', 'used_count', 'remaining_uses',
            'expiry_date', 'is_active', 'is_valid',
            'created_at',
        ]
        read_only_fields = ['used_count', 'created_at']

    def get_remaining_uses(self, obj):
        if obj.max_uses is None:
            return None
        return max(0, obj.max_uses - obj.used_count)

    def validate_code(self, value):
        return value.upper().strip()

    def validate(self, data):
        if data.get('discount_type') == Coupon.DiscountType.PERCENTAGE:
            if data.get('value', 0) > 100:
                raise serializers.ValidationError("Percentage discount cannot exceed 100%.")
        return data


class ValidateCouponSerializer(serializers.Serializer):
    """Used by the checkout flow to validate a coupon code."""
    code        = serializers.CharField()
    order_total = serializers.DecimalField(max_digits=10, decimal_places=2)

    def validate(self, data):
        try:
            coupon = Coupon.objects.get(code=data['code'].upper())
        except Coupon.DoesNotExist:
            raise serializers.ValidationError("Invalid coupon code.")
        if not coupon.is_valid:
            raise serializers.ValidationError("This coupon is expired or no longer valid.")
        if data['order_total'] < coupon.min_order_value:
            raise serializers.ValidationError(
                f"Minimum order value for this coupon is {coupon.min_order_value}."
            )
        data['coupon']          = coupon
        data['discount_amount'] = coupon.calculate_discount(data['order_total'])
        data['final_total']     = data['order_total'] - data['discount_amount']
        return data


# ============================================================
# 6. ORDER SERIALIZERS
# ============================================================

class OrderItemSerializer(serializers.ModelSerializer):
    total_price   = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    product_image = serializers.SerializerMethodField()

    class Meta:
        model  = OrderItem
        fields = [
            'id', 'product', 'variant',
            'product_name', 'variant_name',
            'unit_price', 'quantity', 'total_price',
            'product_image',
        ]

    def get_product_image(self, obj):
        if obj.product:
            img = obj.product.images.filter(is_primary=True).first() or obj.product.images.first()
            if img:
                return img.image.build_url() if hasattr(img.image, 'build_url') else img.image.url
        return None


class OrderItemWriteSerializer(serializers.ModelSerializer):
    """Used when creating an order."""
    class Meta:
        model  = OrderItem
        fields = ['product', 'variant', 'quantity']

    def validate(self, data):
        variant = data.get('variant')
        product = data['product']
        qty     = data['quantity']

        if variant:
            if variant.product != product:
                raise serializers.ValidationError("Variant does not belong to this product.")
            # ✅ التحقق من المخزون بيحصل من WarehouseStock مش variant.stock
            from erp.models import WarehouseStock, Warehouse
            warehouse = Warehouse.objects.filter(is_default=True).first()
            if warehouse:
                try:
                    ws = WarehouseStock.objects.get(warehouse=warehouse, variant=variant)
                    if ws.quantity < qty:
                        raise serializers.ValidationError(
                            f"Insufficient stock for '{product.name}'. Available: {ws.quantity}"
                        )
                except WarehouseStock.DoesNotExist:
                    raise serializers.ValidationError(
                        f"No stock found for '{product.name}' in the default warehouse."
                    )
            else:
                # fallback للـ variant.stock لو مفيش warehouse
                if variant.stock < qty:
                    raise serializers.ValidationError(
                        f"Insufficient stock for '{product.name}'. Available: {variant.stock}"
                    )
        return data


class OrderListSerializer(serializers.ModelSerializer):
    """Lightweight – used in order tables."""
    customer_name          = serializers.SerializerMethodField()
    customer_email         = serializers.CharField(source='user.email', read_only=True)
    items_count            = serializers.SerializerMethodField()
    status_display         = serializers.CharField(source='get_status_display', read_only=True)
    payment_status_display = serializers.CharField(source='get_payment_status_display', read_only=True)

    class Meta:
        model  = Order
        fields = [
            'id', 'order_number',
            'customer_name', 'customer_email',
            'total_price', 'items_count',
            'status', 'status_display',
            'payment_method', 'payment_status', 'payment_status_display',
            'created_at',
        ]

    def get_customer_name(self, obj):
        return obj.shipping_name or (obj.user.get_full_name() if obj.user else 'Guest')

    def get_items_count(self, obj):
        return obj.items.count()


class OrderDetailSerializer(serializers.ModelSerializer):
    """Full order detail."""
    items                  = OrderItemSerializer(many=True, read_only=True)
    payments               = serializers.SerializerMethodField()
    customer               = UserListSerializer(source='user', read_only=True)
    coupon_code            = serializers.CharField(source='coupon.code', read_only=True)
    status_display         = serializers.CharField(source='get_status_display', read_only=True)
    payment_status_display = serializers.CharField(source='get_payment_status_display', read_only=True)

    class Meta:
        model  = Order
        fields = [
            'id', 'order_number',
            'customer', 'coupon', 'coupon_code',
            'subtotal', 'discount_amount', 'shipping_cost', 'total_price',
            'status', 'status_display',
            'payment_method', 'payment_status', 'payment_status_display',
            'shipping_name', 'shipping_phone', 'shipping_address',
            'shipping_city', 'shipping_country', 'shipping_postal_code',
            'notes',
            'items', 'payments',
            'created_at', 'updated_at',
        ]

    def get_payments(self, obj):
        return PaymentSerializer(obj.payments.all(), many=True).data


class OrderCreateSerializer(serializers.ModelSerializer):
    """
    Create a new order with items.

    ✅ التغيير الأساسي:
    - اتشالت الأسطر دي من create():
          variant.stock -= item['quantity']
          variant.save()
    - الخصم دلوقتي بيحصل بس من WarehouseStock عند الـ confirm
      عن طريق dashboard/signals.py → deduct_warehouse_stock_on_confirm
    """
    items = OrderItemWriteSerializer(many=True)

    class Meta:
        model  = Order
        fields = [
            'user', 'coupon',
            'payment_method',
            'shipping_name', 'shipping_phone', 'shipping_address',
            'shipping_city', 'shipping_country', 'shipping_postal_code',
            'notes', 'items', 'shipping_cost',
        ]

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("Order must have at least one item.")
        return value

    def create(self, validated_data):
        from decimal import Decimal
        items_data    = validated_data.pop('items')
        coupon        = validated_data.pop('coupon', None)
        shipping_cost = Decimal(str(validated_data.pop('shipping_cost', 0)))

        # Calculate pricing
        subtotal = Decimal('0')
        for item_data in items_data:
            variant = item_data.get('variant')
            product = item_data['product']
            price   = variant.effective_price if variant else product.effective_price
            subtotal += price * item_data['quantity']

        discount_amount = coupon.calculate_discount(subtotal) if coupon else Decimal('0')
        total_price     = subtotal - discount_amount + shipping_cost

        order = Order.objects.create(
            coupon=coupon,
            subtotal=subtotal,
            discount_amount=discount_amount,
            shipping_cost=shipping_cost,
            total_price=total_price,
            **validated_data
        )

        for item_data in items_data:
            variant = item_data.get('variant')
            product = item_data['product']
            price   = variant.effective_price if variant else product.effective_price

            OrderItem.objects.create(
                order=order,
                product=product,
                variant=variant,
                product_name=product.name,
                variant_name=str(variant) if variant else '',
                unit_price=price,
                quantity=item_data['quantity'],
            )

            # ✅ لا يوجد خصم من variant.stock هنا
            # الخصم بيحصل من WarehouseStock عند تحويل الأوردر لـ confirmed
            # في dashboard/signals.py → deduct_warehouse_stock_on_confirm

        # Update coupon usage
        if coupon:
            coupon.used_count += 1
            coupon.save()

        return order


class UpdateOrderStatusSerializer(serializers.ModelSerializer):
    """Admin-only: change order status."""
    class Meta:
        model  = Order
        fields = ['status', 'payment_status']

    def validate_status(self, value):
        instance = self.instance
        allowed = {
            Order.Status.PENDING:   [Order.Status.CONFIRMED, Order.Status.CANCELLED],
            Order.Status.CONFIRMED: [Order.Status.SHIPPED, Order.Status.CANCELLED],
            Order.Status.SHIPPED:   [Order.Status.DELIVERED],
            Order.Status.DELIVERED: [Order.Status.REFUNDED],
            Order.Status.CANCELLED: [],
            Order.Status.REFUNDED:  [],
        }
        if value not in allowed.get(instance.status, []):
            raise serializers.ValidationError(
                f"Cannot transition from '{instance.status}' to '{value}'."
            )
        return value


# ============================================================
# 7. PAYMENT SERIALIZERS
# ============================================================

class PaymentSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    method_display = serializers.CharField(source='get_method_display', read_only=True)

    class Meta:
        model  = Payment
        fields = [
            'id', 'order',
            'amount', 'method', 'method_display',
            'status', 'status_display',
            'transaction_id', 'created_at',
        ]
        read_only_fields = ['created_at']


# ============================================================
# 8. NOTIFICATION SERIALIZERS
# ============================================================

class NotificationSerializer(serializers.ModelSerializer):
    type_display = serializers.CharField(source='get_type_display', read_only=True)

    class Meta:
        model  = Notification
        fields = ['id', 'type', 'type_display', 'title', 'message', 'link', 'is_read', 'created_at']
        read_only_fields = ['created_at']


# ============================================================
# 9. ACTIVITY LOG SERIALIZERS
# ============================================================

class ActivityLogSerializer(serializers.ModelSerializer):
    admin_email    = serializers.CharField(source='admin.email', read_only=True)
    action_display = serializers.CharField(source='get_action_display', read_only=True)

    class Meta:
        model  = ActivityLog
        fields = [
            'id', 'admin', 'admin_email',
            'action', 'action_display',
            'model_name', 'object_id', 'object_repr',
            'changes', 'ip_address', 'created_at',
        ]
        read_only_fields = fields


# ============================================================
# 10. DASHBOARD STATS SERIALIZERS
# ============================================================

class KPICardSerializer(serializers.Serializer):
    """Single KPI card data."""
    label       = serializers.CharField()
    value       = serializers.CharField()
    change      = serializers.FloatField()
    change_type = serializers.ChoiceField(choices=['increase', 'decrease', 'neutral'])
    icon        = serializers.CharField()


class SalesChartPointSerializer(serializers.Serializer):
    date    = serializers.DateField()
    revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    orders  = serializers.IntegerField()


class TopProductSerializer(serializers.Serializer):
    id            = serializers.IntegerField()
    name          = serializers.CharField()
    image         = serializers.CharField(allow_null=True)
    total_sold    = serializers.IntegerField()
    total_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)


class TopCustomerSerializer(serializers.Serializer):
    id           = serializers.IntegerField()
    full_name    = serializers.CharField()
    email        = serializers.CharField()
    total_orders = serializers.IntegerField()
    total_spent  = serializers.DecimalField(max_digits=12, decimal_places=2)


class DashboardStatsSerializer(serializers.Serializer):
    """Full dashboard response shape."""
    total_revenue    = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_orders     = serializers.IntegerField()
    total_customers  = serializers.IntegerField()
    total_products   = serializers.IntegerField()
    pending_orders   = serializers.IntegerField()
    low_stock_count  = serializers.IntegerField()
    revenue_change   = serializers.FloatField()
    orders_change    = serializers.FloatField()
    customers_change = serializers.FloatField()
    sales_chart      = SalesChartPointSerializer(many=True)
    top_products     = TopProductSerializer(many=True)
    top_customers    = TopCustomerSerializer(many=True)
    recent_orders    = OrderListSerializer(many=True)
    recent_notifications = NotificationSerializer(many=True)


class InventoryAlertSerializer(serializers.ModelSerializer):
    """Used in inventory dashboard – highlights low/out-of-stock variants."""
    product_name  = serializers.CharField(source='product.name')
    variant_label = serializers.SerializerMethodField()
    status        = serializers.SerializerMethodField()

    class Meta:
        model  = ProductVariant
        fields = ['id', 'product', 'product_name', 'variant_label', 'stock', 'sku', 'status']

    def get_variant_label(self, obj):
        return ", ".join(av.value for av in obj.attribute_values.all())

    def get_status(self, obj):
        stock = getattr(obj, 'real_stock', obj.stock)
        if stock == 0:
            return 'out_of_stock'
        if stock <= 5:
            return 'low_stock'
        return 'ok'