"""
============================================================
  STORE APPLICATION — serializers.py

  التغيير الأساسي في CheckoutSerializer.create():
  - اتشال الخصم المباشر من warehouse_stocks:
        variant.warehouse_stocks.update(quantity=F('quantity') - item['quantity'])
  - الخصم دلوقتي بيحصل بس من WarehouseStock عند تحويل الأوردر لـ confirmed
    عن طريق dashboard/signals.py → deduct_warehouse_stock_on_confirm
  - التحقق من المخزون في CheckoutItemSerializer.validate() اتعدّل
    عشان يقرأ من WarehouseStock مش variant.stock
============================================================
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.db import transaction
from decimal import Decimal

from dashboard.models import (
    Product, ProductImage, ProductVariant, AttributeValue,
    Category, Coupon, Order, OrderItem,
)
from dashboard.serializers import (
    AttributeValueSerializer,
)
from .models import Cart, CartItem, GuestOrder, OrderCancellation, ProductReview

User = get_user_model()


# ============================================================
# 1. AUTH SERIALIZERS
# ============================================================

class CustomerRegisterSerializer(serializers.ModelSerializer):
    password         = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)

    class Meta:
        model  = User
        fields = ['first_name', 'last_name', 'email', 'phone', 'password', 'confirm_password']

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("هذا الإيميل مسجل بالفعل.")
        return value

    def validate(self, data):
        if data['password'] != data.pop('confirm_password'):
            raise serializers.ValidationError("كلمتا المرور غير متطابقتين.")
        return data

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(
            username=validated_data['email'],
            role=User.Role.CUSTOMER,
            **validated_data
        )
        user.set_password(password)
        user.save()
        return user


class CustomerLoginSerializer(serializers.Serializer):
    email    = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        from django.contrib.auth import authenticate
        user = authenticate(username=data['email'], password=data['password'])
        if not user:
            raise serializers.ValidationError("إيميل أو كلمة مرور غير صحيحة.")
        if user.is_blocked:
            raise serializers.ValidationError("هذا الحساب محظور.")
        if user.role != User.Role.CUSTOMER:
            raise serializers.ValidationError("هذا الحساب ليس حساب عميل.")
        data['user'] = user
        return data


class CustomerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model  = User
        fields = ['id', 'first_name', 'last_name', 'email', 'phone', 'avatar', 'date_joined']
        read_only_fields = ['email', 'date_joined']


class ChangePasswordSerializer(serializers.Serializer):
    old_password     = serializers.CharField(write_only=True)
    new_password     = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("كلمة المرور الحالية غير صحيحة.")
        return value

    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError("كلمتا المرور الجديدتان غير متطابقتين.")
        return data


# ============================================================
# 2. CATEGORY SERIALIZERS
# ============================================================

class StoreCategorySerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()

    class Meta:
        model  = Category
        fields = ['id', 'name', 'slug', 'image', 'children']

    def get_children(self, obj):
        active_children = obj.children.filter(is_active=True)
        return StoreCategorySerializer(active_children, many=True).data


# ============================================================
# 3. PRODUCT SERIALIZERS
# ============================================================

from dashboard.models import ProductVideo


class ProductVideoSerializer(serializers.ModelSerializer):
    video = serializers.SerializerMethodField()

    class Meta:
        model  = ProductVideo
        fields = ['id', 'video', 'order']

    def get_video(self, obj):
        url = str(obj.video)
        if 'https://' in url:
            idx = url.find('https://')
            return url[idx:]
        if obj.video and hasattr(obj.video, 'build_url'):
            return obj.video.build_url()
        return url


class StoreProductImageSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model  = ProductImage
        fields = ['id', 'image', 'alt_text', 'is_primary', 'order']

    def get_image(self, obj):
        return obj.image.build_url() if hasattr(obj.image, 'build_url') else obj.image.url


class StoreProductVariantSerializer(serializers.ModelSerializer):
    attribute_values = AttributeValueSerializer(many=True, read_only=True)
    effective_price  = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    is_out_of_stock  = serializers.BooleanField(read_only=True)

    class Meta:
        model  = ProductVariant
        fields = [
            'id', 'attribute_values',
            'effective_price', 'price_override',
            'stock', 'sku',
            'is_out_of_stock', 'is_active',
        ]


class StoreProductListSerializer(serializers.ModelSerializer):
    category_name       = serializers.CharField(source='category.name', read_only=True)
    primary_image       = serializers.SerializerMethodField()
    discount_percentage = serializers.DecimalField(max_digits=5, decimal_places=1, read_only=True)
    effective_price     = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    avg_rating          = serializers.SerializerMethodField()
    reviews_count       = serializers.SerializerMethodField()

    class Meta:
        model  = Product
        fields = [
            'id', 'name', 'slug',
            'price', 'discount_price', 'discount_percentage', 'effective_price',
            'category', 'category_name',
            'primary_image',
            'is_in_stock',
            'avg_rating', 'reviews_count',
        ]

    def get_primary_image(self, obj):
        img = obj.images.filter(is_primary=True).first() or obj.images.first()
        if not img:
            return None
        return img.image.build_url() if hasattr(img.image, 'build_url') else img.image.url

    def get_avg_rating(self, obj):
        from django.db.models import Avg
        result = obj.reviews.filter(is_approved=True).aggregate(avg=Avg('rating'))
        avg = result['avg']
        return round(avg, 1) if avg else None

    def get_reviews_count(self, obj):
        return obj.reviews.filter(is_approved=True).count()


class StoreProductDetailSerializer(serializers.ModelSerializer):
    images              = StoreProductImageSerializer(many=True, read_only=True)
    variants            = StoreProductVariantSerializer(many=True, read_only=True)
    category_name       = serializers.CharField(source='category.name', read_only=True)
    discount_percentage = serializers.DecimalField(max_digits=5, decimal_places=1, read_only=True)
    effective_price     = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    avg_rating          = serializers.SerializerMethodField()
    reviews_count       = serializers.SerializerMethodField()
    reviews             = serializers.SerializerMethodField()
    videos              = ProductVideoSerializer(many=True, read_only=True)

    class Meta:
        model  = Product
        fields = [
            'id', 'name', 'slug', 'description',
            'price', 'discount_price', 'discount_percentage', 'effective_price',
            'category', 'category_name',
            'images', 'variants',
            'is_in_stock', 'total_stock',
            'avg_rating', 'reviews_count', 'reviews',
            'created_at',
            'videos',
        ]

    def get_avg_rating(self, obj):
        from django.db.models import Avg
        result = obj.reviews.filter(is_approved=True).aggregate(avg=Avg('rating'))
        avg = result['avg']
        return round(avg, 1) if avg else None

    def get_reviews_count(self, obj):
        return obj.reviews.filter(is_approved=True).count()

    def get_reviews(self, obj):
        reviews = obj.reviews.filter(is_approved=True).order_by('-created_at')[:10]
        return ProductReviewSerializer(reviews, many=True).data


# ============================================================
# 4. CART SERIALIZERS
# ============================================================

class CartItemSerializer(serializers.ModelSerializer):
    product_name    = serializers.CharField(source='product.name', read_only=True)
    variant_label   = serializers.SerializerMethodField()
    unit_price      = serializers.SerializerMethodField()
    subtotal        = serializers.SerializerMethodField()
    primary_image   = serializers.SerializerMethodField()
    is_out_of_stock = serializers.SerializerMethodField()

    class Meta:
        model  = CartItem
        fields = [
            'id', 'product', 'product_name',
            'variant', 'variant_label',
            'quantity',
            'unit_price', 'subtotal',
            'primary_image', 'is_out_of_stock',
        ]

    def get_unit_price(self, obj):
        price = obj.variant.effective_price if obj.variant else obj.product.effective_price
        return str(price)

    def get_subtotal(self, obj):
        price = obj.variant.effective_price if obj.variant else obj.product.effective_price
        return str(price * obj.quantity)

    def get_variant_label(self, obj):
        if obj.variant:
            return ", ".join(av.value for av in obj.variant.attribute_values.all())
        return None

    def get_primary_image(self, obj):
        img = obj.product.images.filter(is_primary=True).first() or obj.product.images.first()
        if not img:
            return None
        return img.image.build_url() if hasattr(img.image, 'build_url') else img.image.url

    def get_is_out_of_stock(self, obj):
        if obj.variant:
            return obj.variant.is_out_of_stock
        return not obj.product.is_in_stock


class CartSerializer(serializers.ModelSerializer):
    items       = CartItemSerializer(many=True, read_only=True)
    subtotal    = serializers.SerializerMethodField()
    total_items = serializers.SerializerMethodField()

    class Meta:
        model  = Cart
        fields = ['id', 'items', 'total_items', 'subtotal', 'updated_at']

    def get_subtotal(self, obj):
        total = sum(
            (item.variant.effective_price if item.variant else item.product.effective_price) * item.quantity
            for item in obj.items.all()
        )
        return str(total)

    def get_total_items(self, obj):
        return sum(item.quantity for item in obj.items.all())


class AddToCartSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    variant_id = serializers.IntegerField(required=False, allow_null=True)
    quantity   = serializers.IntegerField(min_value=1, default=1)
    cart_id    = serializers.IntegerField(required=False, allow_null=True)

    def validate(self, data):
        try:
            product = Product.objects.get(id=data['product_id'], status=Product.Status.ACTIVE)
        except Product.DoesNotExist:
            raise serializers.ValidationError("المنتج غير موجود أو غير متاح.")

        variant = None
        if data.get('variant_id'):
            try:
                variant = ProductVariant.objects.get(
                    id=data['variant_id'],
                    product=product,
                    is_active=True
                )
            except ProductVariant.DoesNotExist:
                raise serializers.ValidationError("الـ variant غير موجود.")

            # ✅ التحقق من المخزون من WarehouseStock
            from erp.models import WarehouseStock, Warehouse
            warehouse = Warehouse.objects.filter(is_default=True).first()
            if warehouse:
                try:
                    ws = WarehouseStock.objects.get(warehouse=warehouse, variant=variant)
                    if ws.quantity < data['quantity']:
                        raise serializers.ValidationError(
                            f"الكمية المطلوبة غير متوفرة. المتاح: {ws.quantity}"
                        )
                except WarehouseStock.DoesNotExist:
                    raise serializers.ValidationError("المنتج غير متوفر في المخزون.")
            else:
                # fallback
                if variant.stock < data['quantity']:
                    raise serializers.ValidationError(
                        f"الكمية المطلوبة غير متوفرة. المتاح: {variant.stock}"
                    )

        data['product'] = product
        data['variant'] = variant
        return data


class UpdateCartItemSerializer(serializers.Serializer):
    quantity = serializers.IntegerField(min_value=1)


# ============================================================
# 5. ORDER SERIALIZERS
# ============================================================

class StoreOrderItemSerializer(serializers.ModelSerializer):
    total_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model  = OrderItem
        fields = [
            'id', 'product_name', 'variant_name',
            'unit_price', 'quantity', 'total_price',
        ]


class StoreOrderListSerializer(serializers.ModelSerializer):
    items_count            = serializers.SerializerMethodField()
    status_display         = serializers.CharField(source='get_status_display', read_only=True)
    payment_status_display = serializers.CharField(source='get_payment_status_display', read_only=True)
    can_cancel             = serializers.SerializerMethodField()

    class Meta:
        model  = Order
        fields = [
            'id', 'order_number',
            'total_price', 'items_count',
            'status', 'status_display',
            'payment_method', 'payment_status', 'payment_status_display',
            'can_cancel', 'created_at',
        ]

    def get_items_count(self, obj):
        return obj.items.count()

    def get_can_cancel(self, obj):
        return obj.status in [Order.Status.PENDING, Order.Status.CONFIRMED]


class StoreOrderDetailSerializer(serializers.ModelSerializer):
    items                  = StoreOrderItemSerializer(many=True, read_only=True)
    status_display         = serializers.CharField(source='get_status_display', read_only=True)
    payment_status_display = serializers.CharField(source='get_payment_status_display', read_only=True)
    can_cancel             = serializers.SerializerMethodField()
    cancellation           = serializers.SerializerMethodField()
    guest_info             = serializers.SerializerMethodField()

    class Meta:
        model  = Order
        fields = [
            'id', 'order_number',
            'subtotal', 'discount_amount', 'shipping_cost', 'total_price',
            'status', 'status_display',
            'payment_method', 'payment_status', 'payment_status_display',
            'shipping_name', 'shipping_phone', 'shipping_address',
            'shipping_city', 'shipping_country', 'shipping_postal_code',
            'notes', 'items',
            'can_cancel', 'cancellation', 'guest_info',
            'created_at', 'updated_at',
        ]

    def get_can_cancel(self, obj):
        return obj.status in [Order.Status.PENDING, Order.Status.CONFIRMED]

    def get_cancellation(self, obj):
        if hasattr(obj, 'cancellation'):
            return {
                'reason':       obj.cancellation.reason,
                'cancelled_at': obj.cancellation.cancelled_at,
            }
        return None

    def get_guest_info(self, obj):
        if hasattr(obj, 'guest_info'):
            return {
                'name':  obj.guest_info.name,
                'email': obj.guest_info.email,
                'phone': obj.guest_info.phone,
            }
        return None


class CheckoutItemSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    variant_id = serializers.IntegerField(required=False, allow_null=True)
    quantity   = serializers.IntegerField(min_value=1)

    def validate(self, data):
        try:
            product = Product.objects.get(id=data['product_id'], status=Product.Status.ACTIVE)
        except Product.DoesNotExist:
            raise serializers.ValidationError(f"المنتج #{data['product_id']} غير موجود.")

        variant = None
        if data.get('variant_id'):
            try:
                variant = ProductVariant.objects.get(
                    id=data['variant_id'], product=product, is_active=True
                )
            except ProductVariant.DoesNotExist:
                raise serializers.ValidationError("الـ variant غير موجود.")

            # ✅ التحقق من المخزون من WarehouseStock مش variant.stock
            from erp.models import WarehouseStock, Warehouse
            warehouse = Warehouse.objects.filter(is_default=True).first()
            if warehouse:
                try:
                    ws = WarehouseStock.objects.get(warehouse=warehouse, variant=variant)
                    if ws.quantity < data['quantity']:
                        raise serializers.ValidationError(
                            f"الكمية غير متوفرة للمنتج '{product.name}'. المتاح: {ws.quantity}"
                        )
                except WarehouseStock.DoesNotExist:
                    raise serializers.ValidationError(
                        f"المنتج '{product.name}' غير متوفر في المخزون."
                    )
            else:
                # fallback لـ variant.stock لو مفيش default warehouse
                if variant.stock < data['quantity']:
                    raise serializers.ValidationError(
                        f"الكمية غير متوفرة للمنتج '{product.name}'. المتاح: {variant.stock}"
                    )

        data['product'] = product
        data['variant'] = variant
        return data


class CheckoutSerializer(serializers.Serializer):
    """
    يستقبل بيانات الـ Checkout كاملة.
    يشتغل لـ User مسجل وـ Guest.

    ✅ التغيير الأساسي:
    - اتشال الخصم المباشر من warehouse_stocks في create()
    - الخصم دلوقتي بيحصل بس عند تحويل الأوردر لـ confirmed
      عن طريق dashboard/signals.py → deduct_warehouse_stock_on_confirm
    """
    # بيانات الشحن
    shipping_name        = serializers.CharField(max_length=200)
    shipping_phone       = serializers.CharField(max_length=20)
    shipping_address     = serializers.CharField(max_length=500)
    shipping_city        = serializers.CharField(max_length=100)
    shipping_country     = serializers.CharField(max_length=100)
    shipping_postal_code = serializers.CharField(max_length=20, required=False, allow_blank=True)
    notes                = serializers.CharField(required=False, allow_blank=True)
    shipping_cost        = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, default=0
    )

    # بيانات الـ Guest
    guest_email = serializers.EmailField(required=False, allow_blank=True)

    # الدفع
    payment_method = serializers.ChoiceField(choices=[('cod', 'Cash on Delivery')])

    # الكوبون
    coupon_code = serializers.CharField(required=False, allow_blank=True)

    # الأيتمز
    items = CheckoutItemSerializer(many=True)

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("الأوردر لازم يكون فيه أيتم واحد على الأقل.")
        return value

    def validate_coupon_code(self, value):
        if not value:
            return None
        try:
            coupon = Coupon.objects.get(code=value.upper(), is_active=True)
            if not coupon.is_valid:
                raise serializers.ValidationError("الكوبون منتهي أو استُنفد.")
            return coupon
        except Coupon.DoesNotExist:
            raise serializers.ValidationError("كود الكوبون غير صحيح.")

    def validate(self, data):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            if not data.get('guest_email'):
                raise serializers.ValidationError(
                    {"guest_email": "الإيميل مطلوب للطلب بدون تسجيل."}
                )
        return data

    @transaction.atomic
    def create(self, validated_data):
        from .models import PaymentProcessorFactory, GuestOrder
        from dashboard.models import Order, OrderItem, Payment

        request    = self.context.get('request')
        items_data = validated_data['items']
        coupon     = validated_data.get('coupon_code')

        # ── حساب الـ Pricing ──────────────────────────────────
        subtotal = Decimal('0')
        for item in items_data:
            variant = item.get('variant')
            product = item['product']
            price   = variant.effective_price if variant else product.effective_price
            subtotal += price * item['quantity']

        discount_amount = coupon.calculate_discount(subtotal) if coupon else Decimal('0')
        shipping_cost   = validated_data.get('shipping_cost', Decimal('0'))
        total_price     = subtotal - discount_amount + shipping_cost

        if coupon and subtotal < coupon.min_order_value:
            raise serializers.ValidationError(
                f"الحد الأدنى للطلب لاستخدام هذا الكوبون هو {coupon.min_order_value}."
            )

        # ── إنشاء الأوردر ─────────────────────────────────────
        user = request.user if (request and request.user.is_authenticated) else None

        order = Order.objects.create(
            user=user,
            coupon=coupon,
            subtotal=subtotal,
            discount_amount=discount_amount,
            shipping_cost=shipping_cost,
            total_price=total_price,
            payment_method=validated_data['payment_method'],
            shipping_name=validated_data['shipping_name'],
            shipping_phone=validated_data['shipping_phone'],
            shipping_address=validated_data['shipping_address'],
            shipping_city=validated_data['shipping_city'],
            shipping_country=validated_data['shipping_country'],
            shipping_postal_code=validated_data.get('shipping_postal_code', ''),
            notes=validated_data.get('notes', ''),
        )

        # ── Guest Info ─────────────────────────────────────────
        if not user:
            GuestOrder.objects.create(
                order=order,
                name=validated_data['shipping_name'],
                email=validated_data['guest_email'],
                phone=validated_data['shipping_phone'],
            )

        # ── Order Items ────────────────────────────────────────
        for item in items_data:
            variant = item.get('variant')
            product = item['product']
            price   = variant.effective_price if variant else product.effective_price

            OrderItem.objects.create(
                order=order,
                product=product,
                variant=variant,
                product_name=product.name,
                variant_name=str(variant) if variant else '',
                unit_price=price,
                quantity=item['quantity'],
            )

            # ✅ لا يوجد خصم من المخزون هنا
            # الخصم بيحصل من WarehouseStock عند تحويل الأوردر لـ confirmed
            # في dashboard/signals.py → deduct_warehouse_stock_on_confirm

        # ── Payment Processor ──────────────────────────────────
        processor      = PaymentProcessorFactory.get(validated_data['payment_method'])
        payment_result = processor.initiate(order)

        Payment.objects.create(
            order=order,
            amount=total_price,
            method=validated_data['payment_method'],
            status='pending',
        )

        # ── Coupon Usage ───────────────────────────────────────
        if coupon:
            coupon.used_count += 1
            coupon.save()

        # ── Clear Cart ─────────────────────────────────────────
        if user:
            Cart.objects.filter(user=user).delete()
        elif request:
            session_key = request.session.session_key
            if session_key:
                Cart.objects.filter(session_key=session_key).delete()

        return order


class CancelOrderSerializer(serializers.Serializer):
    reason = serializers.CharField(min_length=5)


# ============================================================
# 6. REVIEW SERIALIZERS
# ============================================================

class ProductReviewSerializer(serializers.ModelSerializer):
    reviewer_name = serializers.SerializerMethodField()

    class Meta:
        model  = ProductReview
        fields = [
            'id', 'reviewer_name',
            'rating', 'title', 'body',
            'is_verified_purchase',
            'created_at',
        ]

    def get_reviewer_name(self, obj):
        return obj.user.get_full_name() or obj.user.email


class CreateReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model  = ProductReview
        fields = ['rating', 'title', 'body']

    def validate(self, data):
        request = self.context['request']
        product = self.context['product']

        if ProductReview.objects.filter(product=product, user=request.user).exists():
            raise serializers.ValidationError("أنت قمت بتقييم هذا المنتج من قبل.")

        from dashboard.models import OrderItem
        is_verified = OrderItem.objects.filter(
            order__user=request.user,
            order__payment_status='paid',
            product=product,
        ).exists()

        data['is_verified_purchase'] = is_verified
        return data

    def create(self, validated_data):
        return ProductReview.objects.create(
            product=self.context['product'],
            user=self.context['request'].user,
            **validated_data
        )


# ============================================================
# 7. COUPON SERIALIZER
# ============================================================

class StoreCouponValidateSerializer(serializers.Serializer):
    code        = serializers.CharField()
    order_total = serializers.DecimalField(max_digits=10, decimal_places=2)

    def validate(self, data):
        try:
            coupon = Coupon.objects.get(code=data['code'].upper(), is_active=True)
        except Coupon.DoesNotExist:
            raise serializers.ValidationError("كود الكوبون غير صحيح.")

        if not coupon.is_valid:
            raise serializers.ValidationError("الكوبون منتهي أو استُنفد.")

        if data['order_total'] < coupon.min_order_value:
            raise serializers.ValidationError(
                f"الحد الأدنى للطلب لاستخدام هذا الكوبون هو {coupon.min_order_value}."
            )

        data['coupon']          = coupon
        data['discount_amount'] = coupon.calculate_discount(data['order_total'])
        data['final_total']     = data['order_total'] - data['discount_amount']
        return data