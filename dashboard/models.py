from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.text import slugify
import uuid


# ============================================================
# 1. USER MODEL
# ============================================================

class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN  = 'admin',   'Admin'
        STAFF  = 'staff',   'Staff'
        CUSTOMER = 'customer', 'Customer'

    email    = models.EmailField(unique=True)
    phone    = models.CharField(max_length=20, blank=True, null=True)
    avatar   = models.ImageField(upload_to='avatars/', blank=True, null=True)
    role     = models.CharField(max_length=20, choices=Role.choices, default=Role.CUSTOMER)
    is_blocked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_full_name()} ({self.email})"

    @property
    def is_admin(self):
        return self.role == self.Role.ADMIN

    @property
    def is_staff_member(self):
        return self.role == self.Role.STAFF


# ============================================================
# 2. ADMIN ROLE & PERMISSIONS
# ============================================================

class AdminRole(models.Model):
    """
    Role-based access control for admin/staff users.
    permissions stored as JSON: { "orders": ["view","edit"], "products": ["view","add","edit","delete"] }
    """
    name        = models.CharField(max_length=100, unique=True)
    permissions = models.JSONField(default=dict)
    created_at  = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class StaffProfile(models.Model):
    """Links a staff User to an AdminRole."""
    user       = models.OneToOneField(User, on_delete=models.CASCADE, related_name='staff_profile')
    admin_role = models.ForeignKey(AdminRole, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.user.email} – {self.admin_role}"


# ============================================================
# 3. CATEGORY (Nested / Self-referential)
# ============================================================

class Category(models.Model):
    name       = models.CharField(max_length=200)
    slug       = models.SlugField(max_length=220, unique=True, blank=True)
    parent     = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='children'
    )
    image      = models.ImageField(upload_to='categories/', blank=True, null=True)
    is_active  = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            while Category.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.parent} > {self.name}" if self.parent else self.name

    @property
    def is_root(self):
        return self.parent is None

    def get_all_children(self):
        """Recursively returns all subcategory IDs."""
        children = list(self.children.all())
        result = []
        for child in children:
            result.append(child)
            result.extend(child.get_all_children())
        return result

# ============================================================
# 4. PRODUCT
# ============================================================
class Product(models.Model):
    class Status(models.TextChoices):
        ACTIVE   = 'active',   'Active'
        HIDDEN   = 'hidden',   'Hidden'
        ARCHIVED = 'archived', 'Archived'

    name           = models.CharField(max_length=300)
    slug           = models.SlugField(max_length=320, unique=True, blank=True)
    description    = models.TextField(blank=True)
    price          = models.DecimalField(max_digits=10, decimal_places=2)
    discount_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    sku            = models.CharField(max_length=100, unique=True, blank=True, null=True)
    category       = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='products')
    status         = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            while Product.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    @property
    def effective_price(self):
        return self.discount_price if self.discount_price else self.price

    @property
    def discount_percentage(self):
        if self.discount_price:
            return round((1 - self.discount_price / self.price) * 100, 1)
        return 0

    @property
    def total_stock(self):
        return sum(v.stock for v in self.variants.all())

    @property
    def is_in_stock(self):
        return self.total_stock > 0

from cloudinary.models import CloudinaryField

class ProductImage(models.Model):
    product    = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = CloudinaryField('image', folder='products/')
    alt_text   = models.CharField(max_length=200, blank=True)
    is_primary = models.BooleanField(default=False)
    order      = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"Image for {self.product.name} ({'Primary' if self.is_primary else 'Secondary'})"
    
class ProductVideo(models.Model):
    product    = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='videos')
    video      = CloudinaryField('video', resource_type='video', folder='products/videos/')
    title      = models.CharField(max_length=200, blank=True)
    is_primary = models.BooleanField(default=False)
    order      = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

# ============================================================
# 5. PRODUCT VARIANTS (Size / Color / etc.)
# ============================================================

class Attribute(models.Model):
    """e.g., Color, Size, Material"""
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class AttributeValue(models.Model):
    """e.g., Red, XL, Cotton"""
    attribute = models.ForeignKey(Attribute, on_delete=models.CASCADE, related_name='values')
    value     = models.CharField(max_length=100)

    class Meta:
        unique_together = ('attribute', 'value')

    def __str__(self):
        return f"{self.attribute.name}: {self.value}"


class ProductVariant(models.Model):
    """
    A specific sellable combination: e.g., Red + XL.
    Each variant has its own stock, price override (optional), and SKU.
    """
    product         = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    attribute_values = models.ManyToManyField(AttributeValue, related_name='variants')
    price_override  = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    stock           = models.PositiveIntegerField(default=0)
    sku             = models.CharField(max_length=100, unique=True, blank=True, null=True)
    image           = models.ImageField(upload_to='variants/', blank=True, null=True)
    is_active       = models.BooleanField(default=True)

    def __str__(self):
        attrs = ", ".join(str(av) for av in self.attribute_values.all())
        return f"{self.product.name} [{attrs}]"

    @property
    def effective_price(self):
        return self.price_override if self.price_override else self.product.effective_price

    @property
    def is_low_stock(self):
        """Threshold: 5 units."""
        return 0 < self.stock <= 5

    @property
    def is_out_of_stock(self):
        return self.stock == 0


# ============================================================
# 6. COUPON / DISCOUNT
# ============================================================

class Coupon(models.Model):
    class DiscountType(models.TextChoices):
        PERCENTAGE = 'percentage', 'Percentage'
        FIXED      = 'fixed',      'Fixed Amount'

    code            = models.CharField(max_length=50, unique=True)
    discount_type   = models.CharField(max_length=20, choices=DiscountType.choices)
    value           = models.DecimalField(max_digits=10, decimal_places=2)
    min_order_value = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    max_uses        = models.PositiveIntegerField(null=True, blank=True)
    used_count      = models.PositiveIntegerField(default=0)
    expiry_date     = models.DateTimeField(null=True, blank=True)
    is_active       = models.BooleanField(default=True)
    created_at      = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.code} ({self.value}{'%' if self.discount_type == 'percentage' else '$'})"

    @property
    def is_valid(self):
        from django.utils import timezone
        if not self.is_active:
            return False
        if self.max_uses and self.used_count >= self.max_uses:
            return False
        if self.expiry_date and self.expiry_date < timezone.now():
            return False
        return True

    def calculate_discount(self, order_total):
        if self.discount_type == self.DiscountType.PERCENTAGE:
            return round(order_total * self.value / 100, 2)
        return min(self.value, order_total)


# ============================================================
# 7. ORDER
# ============================================================

class Order(models.Model):
    class Status(models.TextChoices):
        PENDING   = 'pending',   'Pending'
        CONFIRMED = 'confirmed', 'Confirmed'
        SHIPPED   = 'shipped',   'Shipped'
        DELIVERED = 'delivered', 'Delivered'
        CANCELLED = 'cancelled', 'Cancelled'
        REFUNDED  = 'refunded',  'Refunded'

    class PaymentMethod(models.TextChoices):
        STRIPE  = 'stripe',  'Stripe'
        PAYPAL  = 'paypal',  'PayPal'
        COD     = 'cod',     'Cash on Delivery'

    class PaymentStatus(models.TextChoices):
        PENDING  = 'pending',  'Pending'
        PAID     = 'paid',     'Paid'
        FAILED   = 'failed',   'Failed'
        REFUNDED = 'refunded', 'Refunded'

    # Core
    order_number    = models.CharField(max_length=20, unique=True, blank=True)
    user            = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='orders')
    coupon          = models.ForeignKey(Coupon, on_delete=models.SET_NULL, null=True, blank=True)

    # Pricing
    subtotal        = models.DecimalField(max_digits=10, decimal_places=2)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    shipping_cost   = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_price     = models.DecimalField(max_digits=10, decimal_places=2)

    # Status
    status          = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    payment_method  = models.CharField(max_length=20, choices=PaymentMethod.choices)
    payment_status  = models.CharField(max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.PENDING)

    # Shipping Address (embedded – no separate model)
    shipping_name       = models.CharField(max_length=200)
    shipping_phone      = models.CharField(max_length=20)
    shipping_address    = models.CharField(max_length=500)
    shipping_city       = models.CharField(max_length=100)
    shipping_country    = models.CharField(max_length=100)
    shipping_postal_code = models.CharField(max_length=20, blank=True)

    notes      = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = self._generate_order_number()
        super().save(*args, **kwargs)

    def _generate_order_number(self):
        import random, string
        prefix = 'ORD'
        suffix = ''.join(random.choices(string.digits, k=8))
        return f"{prefix}-{suffix}"

    def __str__(self):
        return f"Order {self.order_number} – {self.user}"


class OrderItem(models.Model):
    """
    Snapshot of the product/variant at the time of purchase.
    price is stored explicitly so price changes don't affect old orders.
    """
    order   = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    variant = models.ForeignKey(ProductVariant, on_delete=models.SET_NULL, null=True, blank=True)

    # Snapshot fields
    product_name   = models.CharField(max_length=300)
    variant_name   = models.CharField(max_length=200, blank=True)
    unit_price     = models.DecimalField(max_digits=10, decimal_places=2)
    quantity       = models.PositiveIntegerField()

    class Meta:
        unique_together = ('order', 'variant')

    @property
    def total_price(self):
        return self.unit_price * self.quantity

    def __str__(self):
        return f"{self.quantity}x {self.product_name} (Order {self.order.order_number})"


# ============================================================
# 8. PAYMENT
# ============================================================

class Payment(models.Model):
    class Status(models.TextChoices):
        PENDING   = 'pending',   'Pending'
        SUCCESS   = 'success',   'Success'
        FAILED    = 'failed',    'Failed'
        REFUNDED  = 'refunded',  'Refunded'

    order          = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='payments')
    amount         = models.DecimalField(max_digits=10, decimal_places=2)
    method         = models.CharField(max_length=20, choices=Order.PaymentMethod.choices)
    status         = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    transaction_id = models.CharField(max_length=200, blank=True, null=True, unique=True)
    gateway_response = models.JSONField(default=dict, blank=True)
    created_at     = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payment {self.transaction_id} – {self.status}"


# ============================================================
# 9. NOTIFICATION
# ============================================================

class Notification(models.Model):
    class Type(models.TextChoices):
        NEW_ORDER   = 'new_order',   'New Order'
        LOW_STOCK   = 'low_stock',   'Low Stock'
        OUT_OF_STOCK = 'out_of_stock', 'Out of Stock'
        NEW_USER    = 'new_user',    'New User'
        PAYMENT     = 'payment',     'Payment'
        REFUND      = 'refund',      'Refund'
        SYSTEM      = 'system',      'System'

    type       = models.CharField(max_length=30, choices=Type.choices)
    title      = models.CharField(max_length=200)
    message    = models.TextField()
    link       = models.CharField(max_length=300, blank=True)  # e.g., /admin/orders/123
    is_read    = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.type}] {self.title}"


# ============================================================
# 10. ACTIVITY LOG
# ============================================================

class ActivityLog(models.Model):
    class Action(models.TextChoices):
        CREATE = 'create', 'Create'
        UPDATE = 'update', 'Update'
        DELETE = 'delete', 'Delete'
        VIEW   = 'view',   'View'
        LOGIN  = 'login',  'Login'
        LOGOUT = 'logout', 'Logout'

    admin      = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='activity_logs')
    action     = models.CharField(max_length=20, choices=Action.choices)
    model_name = models.CharField(max_length=100)
    object_id  = models.CharField(max_length=50, blank=True, null=True)
    object_repr = models.CharField(max_length=300, blank=True)
    changes    = models.JSONField(default=dict, blank=True)  # { "field": ["old_val", "new_val"] }
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.admin} {self.action} {self.model_name} #{self.object_id}"