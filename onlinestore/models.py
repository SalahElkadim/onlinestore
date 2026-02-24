from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator

from dashboard.models import Product, ProductVariant, Coupon, Order

User = get_user_model()


# ============================================================
# 1. CART
# ============================================================

class Cart(models.Model):
    """
    مرتبطة بـ User لو مسجل، أو بـ session_key لو Guest.
    """
    user        = models.OneToOneField(
        User, on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='cart'
    )
    session_key = models.CharField(
        max_length=40,
        null=True, blank=True,
        db_index=True
    )
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            # كل يوزر ليه cart واحدة بس
            models.UniqueConstraint(
                fields=['user'],
                condition=models.Q(user__isnull=False),
                name='unique_cart_per_user'
            ),
            # أو session واحدة لو guest
            models.UniqueConstraint(
                fields=['session_key'],
                condition=models.Q(session_key__isnull=False),
                name='unique_cart_per_session'
            ),
        ]

    def __str__(self):
        owner = self.user.email if self.user else f"Guest ({self.session_key})"
        return f"Cart – {owner}"

    @property
    def total_items(self):
        return sum(item.quantity for item in self.items.all())

    @property
    def subtotal(self):
        return sum(item.subtotal for item in self.items.all())

class CartItem(models.Model):
    cart     = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product  = models.ForeignKey(Product, on_delete=models.CASCADE)
    variant  = models.ForeignKey(
        ProductVariant, on_delete=models.CASCADE,
        null=True, blank=True
    )
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # بدل unique_together القديمة
        constraints = [
            # لو في variant
            models.UniqueConstraint(
                fields=['cart', 'variant'],
                condition=models.Q(variant__isnull=False),
                name='unique_cart_variant'
            ),
            # لو مفيش variant (منتج بدون اختيارات)
            models.UniqueConstraint(
                fields=['cart', 'product'],
                condition=models.Q(variant__isnull=True),
                name='unique_cart_product_no_variant'
            ),
        ]


# ============================================================
# 2. CUSTOMER ORDER (extends / wraps the admin Order model)
# ============================================================
# ملاحظة: الـ Order model الرئيسي موجود في admin_dashboard
# هنا بس بنضيف الـ cancellation logic والـ guest info

class GuestOrder(models.Model):
    """
    لو العميل مش مسجل، بنربط الأوردر ببياناته هنا.
    """
    order      = models.OneToOneField(
        Order, on_delete=models.CASCADE,
        related_name='guest_info'
    )
    name       = models.CharField(max_length=200)
    email      = models.EmailField()
    phone      = models.CharField(max_length=20)

    def __str__(self):
        return f"Guest: {self.name} ({self.email}) → Order #{self.order.order_number}"


class OrderCancellation(models.Model):
    """
    يسجّل سبب الإلغاء ومن ألغى الأوردر.
    """
    order      = models.OneToOneField(
        Order, on_delete=models.CASCADE,
        related_name='cancellation'
    )
    reason     = models.TextField()
    cancelled_by = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True  # null لو guest ألغى
    )
    cancelled_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Cancellation → Order #{self.order.order_number}"


# ============================================================
# 3. PRODUCT REVIEW
# ============================================================

class ProductReview(models.Model):
    product    = models.ForeignKey(
        Product, on_delete=models.CASCADE,
        related_name='reviews'
    )
    user       = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='reviews'
    )
    rating     = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    title      = models.CharField(max_length=200, blank=True)
    body       = models.TextField()
    is_verified_purchase = models.BooleanField(default=False)  # اشترى المنتج فعلاً؟
    is_approved = models.BooleanField(default=True)            # لو عايز moderation
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('product', 'user')  # مش ينفع يعمل أكتر من review للمنتج
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} → {self.product.name} ({self.rating}★)"


# ============================================================
# 4. PAYMENT PROCESSOR (Strategy Pattern)
# ============================================================

class PaymentProcessor:
    """
    Base class – كل payment method بتورّث منها.
    دلوقتي بس COD، بس الـ interface جاهز لـ Stripe/PayPal بعدين.
    """

    def initiate(self, order) -> dict:
        """يبدأ عملية الدفع ويرجع dict بالبيانات."""
        raise NotImplementedError

    def verify(self, order, payload: dict) -> bool:
        """يتحقق من الدفع (مهم للـ online gateways)."""
        raise NotImplementedError

    def refund(self, order, amount=None) -> bool:
        """يعمل refund."""
        raise NotImplementedError


class CODProcessor(PaymentProcessor):
    """Cash on Delivery – مفيش حاجة بتتعمل غير إنك تسجّل الأوردر."""

    def initiate(self, order) -> dict:
        # الأوردر بيتعمل وبيفضل pending لحد الاستلام
        return {
            'method': 'cod',
            'status': 'pending',
            'message': 'سيتم الدفع عند الاستلام.',
        }

    def verify(self, order, payload: dict) -> bool:
        # COD بيتأكد يدوياً من الـ Admin
        return True

    def refund(self, order, amount=None) -> bool:
        # COD مش فيه refund أوتوماتيك
        return False


class PaymentProcessorFactory:
    """
    Factory بترجع الـ processor المناسب بناءً على الـ method.
    لما تضيف Stripe مثلاً، بس تضيف الـ class وتسجّله هنا.
    """
    _registry = {
        'cod': CODProcessor,
        # 'stripe': StripeProcessor,   ← هتضيفه بعدين
        # 'paypal': PayPalProcessor,   ← هتضيفه بعدين
    }

    @classmethod
    def get(cls, method: str) -> PaymentProcessor:
        processor_class = cls._registry.get(method)
        if not processor_class:
            raise ValueError(f"Unsupported payment method: {method}")
        return processor_class()

    @classmethod
    def register(cls, method: str, processor_class):
        """تسجيل processor جديد ببساطة."""
        cls._registry[method] = processor_class