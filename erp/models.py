"""
============================================================
  ERP APPLICATION — models.py
  Django app: erp
  يشتغل جوا نفس مشروع Django مع store app
============================================================

Structure:
  1.  Sales Module        → SalesOrder, SalesOrderItem, Quotation, QuotationItem
  2.  Inventory Module    → Warehouse, WarehouseStock, StockMovement, StockAlert
  3.  Purchasing Module   → Supplier, PurchaseOrder, PurchaseOrderItem, GoodsReceipt
  4.  Returns Module      → ReturnRequest, ReturnItem
  5.  Finance Module      → ExpenseCategory, Expense, Revenue, FinancialSummary
  6.  Shipping Module     → ShippingCarrier, ShipmentRecord, ShipmentEvent
  7.  CRM Module          → CustomerProfile, CustomerTag, CustomerNote, CustomerSegment
  8.  Reports Module      → ReportSnapshot
  9.  HR Module           → Department, Employee, Attendance, LeaveRequest, SalesTarget

Dependencies:
  pip install django cloudinary django-cloudinary-storage
"""

from django.db import models
from django.utils import timezone
from django.utils.text import slugify
import uuid


# ──────────────────────────────────────────────────────────
#  Lazy imports من store app عشان نتجنب circular imports
#  استخدم string reference في ForeignKey
# ──────────────────────────────────────────────────────────
#  'dashboard.User'          → User model
#  'dashboard.ProductVariant' → ProductVariant model
#  'dashboard.Order'         → Online Order model
# ──────────────────────────────────────────────────────────


# ============================================================
#  MODULE 1 — SALES
#  كل عملية بيع من أي مصدر تدخل هنا
# ============================================================

class Quotation(models.Model):
    """
    عرض سعر — بيتحول لـ SalesOrder لما العميل يوافق.
    """
    class Status(models.TextChoices):
        DRAFT    = 'draft',    'Draft'
        SENT     = 'sent',     'Sent'
        ACCEPTED = 'accepted', 'Accepted'
        EXPIRED  = 'expired',  'Expired'
        REJECTED = 'rejected', 'Rejected'

    quotation_number = models.CharField(max_length=50, unique=True, blank=True)
    customer_name    = models.CharField(max_length=200)
    customer_phone   = models.CharField(max_length=20, blank=True)
    customer_email   = models.EmailField(blank=True)
    status           = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    valid_until      = models.DateField(null=True, blank=True)
    notes            = models.TextField(blank=True)
    created_by       = models.ForeignKey(
        'dashboard.User', on_delete=models.SET_NULL, null=True,
        related_name='quotations'
    )
    converted_to     = models.OneToOneField(
        'SalesOrder', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='source_quotation'
    )
    created_at       = models.DateTimeField(auto_now_add=True)
    updated_at       = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.quotation_number:
            self.quotation_number = f"QUO-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    @property
    def subtotal(self):
        return sum(item.total_price for item in self.items.all())

    @property
    def is_expired(self):
        if self.valid_until:
            return timezone.now().date() > self.valid_until
        return False

    def __str__(self):
        return f"{self.quotation_number} – {self.customer_name}"


class QuotationItem(models.Model):
    quotation  = models.ForeignKey(Quotation, on_delete=models.CASCADE, related_name='items')
    variant    = models.ForeignKey(
        'dashboard.ProductVariant', on_delete=models.SET_NULL,
        null=True, related_name='quotation_items'
    )
    product_name = models.CharField(max_length=300)
    variant_name = models.CharField(max_length=200, blank=True)
    quantity     = models.PositiveIntegerField()
    unit_price   = models.DecimalField(max_digits=10, decimal_places=2)
    note         = models.CharField(max_length=300, blank=True)

    @property
    def total_price(self):
        return self.unit_price * self.quantity

    def __str__(self):
        return f"{self.quantity}× {self.product_name}"


class SalesOrder(models.Model):
    """
    قلب الـ ERP — كل بيعة من أي مصدر تتسجل هنا.
    لو جاية من الموقع → online_order مربوط.
    لو manual/واتساب/إنستجرام → online_order = None.
    """
    class Source(models.TextChoices):
        ONLINE    = 'online',    'Online Store'
        MANUAL    = 'manual',    'Manual (Staff)'
        WHATSAPP  = 'whatsapp',  'WhatsApp'
        INSTAGRAM = 'instagram', 'Instagram'
        FACEBOOK  = 'facebook',  'Facebook'
        PHONE     = 'phone',     'Phone Call'
        POS       = 'pos',       'Point of Sale'

    class Status(models.TextChoices):
        DRAFT     = 'draft',     'Draft'
        CONFIRMED = 'confirmed', 'Confirmed'
        PROCESSING = 'processing', 'Processing'
        SHIPPED   = 'shipped',   'Shipped'
        DELIVERED = 'delivered', 'Delivered'
        CANCELLED = 'cancelled', 'Cancelled'
        RETURNED  = 'returned',  'Returned'

    class PaymentMethod(models.TextChoices):
        CASH      = 'cash',     'Cash'
        CARD      = 'card',     'Card'
        TRANSFER  = 'transfer', 'Bank Transfer'
        STRIPE    = 'stripe',   'Stripe'
        PAYPAL    = 'paypal',   'PayPal'
        COD       = 'cod',      'Cash on Delivery'
        WALLET    = 'wallet',   'Wallet'

    class PaymentStatus(models.TextChoices):
        PENDING  = 'pending',  'Pending'
        PAID     = 'paid',     'Paid'
        PARTIAL  = 'partial',  'Partial'
        FAILED   = 'failed',   'Failed'
        REFUNDED = 'refunded', 'Refunded'

    # ── تعريف الأوردر ──
    order_number   = models.CharField(max_length=50, unique=True, blank=True)
    source         = models.CharField(max_length=20, choices=Source.choices)
    status         = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)

    # ── ربط بالأوردر الأونلاين لو موجود ──
    online_order   = models.OneToOneField(
        'dashboard.Order', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='erp_sales_order'
    )

    # ── بيانات العميل (مستقلة عن User model) ──
    customer       = models.ForeignKey(
        'CustomerProfile', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='sales_orders'
    )
    customer_name  = models.CharField(max_length=200)
    customer_phone = models.CharField(max_length=20, blank=True)
    customer_email = models.EmailField(blank=True)
    customer_note  = models.TextField(blank=True)

    # ── التسعير ──
    subtotal        = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_amount      = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    shipping_cost   = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total           = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # ── الدفع ──
    payment_method  = models.CharField(max_length=20, choices=PaymentMethod.choices, default=PaymentMethod.CASH)
    payment_status  = models.CharField(max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.PENDING)
    amount_paid     = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # ── بيانات إضافية ──
    reference_code  = models.CharField(max_length=200, blank=True)  # رقم المحادثة أو رقم خارجي
    internal_notes  = models.TextField(blank=True)
    created_by      = models.ForeignKey(
        'dashboard.User', on_delete=models.SET_NULL, null=True,
        related_name='created_sales_orders'
    )
    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = f"SO-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    @property
    def balance_due(self):
        return self.total - self.amount_paid

    @property
    def is_fully_paid(self):
        return self.amount_paid >= self.total

    def calculate_totals(self):
        """يحسب الـ subtotal والـ total من الـ items."""
        self.subtotal = sum(item.total_price for item in self.items.all())
        self.total = self.subtotal - self.discount_amount + self.tax_amount + self.shipping_cost
        self.save(update_fields=['subtotal', 'total'])

    def __str__(self):
        return f"{self.order_number} ({self.get_source_display()}) – {self.customer_name}"


class SalesOrderItem(models.Model):
    sales_order  = models.ForeignKey(SalesOrder, on_delete=models.CASCADE, related_name='items')
    variant      = models.ForeignKey(
        'dashboard.ProductVariant', on_delete=models.SET_NULL,
        null=True, related_name='sales_items'
    )
    # Snapshot — عشان لو اتغير السعر بعدين محيرش القديم
    product_name = models.CharField(max_length=300)
    variant_name = models.CharField(max_length=200, blank=True)
    unit_price   = models.DecimalField(max_digits=10, decimal_places=2)
    quantity     = models.PositiveIntegerField()
    discount     = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    note         = models.CharField(max_length=300, blank=True)

    @property
    def total_price(self):
        return (self.unit_price - self.discount) * self.quantity

    def __str__(self):
        return f"{self.quantity}× {self.product_name}"


# ============================================================
#  MODULE 2 — INVENTORY
#  أي حركة مخزون تتسجل تلقائياً عن طريق Signals
# ============================================================

class Warehouse(models.Model):
    """مستودع — ممكن يكون عنده أكتر من مستودع."""
    name       = models.CharField(max_length=200)
    location   = models.CharField(max_length=300, blank=True)
    is_default = models.BooleanField(default=False)
    is_active  = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # لو اتحدد كـ default → يلغي الـ default القديم
        if self.is_default:
            Warehouse.objects.exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} {'(Default)' if self.is_default else ''}"


class WarehouseStock(models.Model):
    """الكمية الفعلية لكل variant في كل مستودع."""
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='stock_entries')
    variant   = models.ForeignKey(
        'dashboard.ProductVariant', on_delete=models.CASCADE, related_name='warehouse_stocks'
    )
    quantity  = models.IntegerField(default=0)

    class Meta:
        unique_together = ('warehouse', 'variant')

    def __str__(self):
        return f"{self.variant} @ {self.warehouse.name}: {self.quantity}"


class StockMovement(models.Model):
    """
    سجل كل حركة مخزون — المصدر واضح دايماً.
    quantity موجبة = دخل / سالبة = خرج
    """
    class Type(models.TextChoices):
        IN       = 'in',       'Stock In'
        OUT      = 'out',      'Stock Out'
        RETURN   = 'return',   'Return'
        ADJUST   = 'adjust',   'Manual Adjustment'
        TRANSFER = 'transfer', 'Warehouse Transfer'
        DAMAGE   = 'damage',   'Damage / Loss'

    variant       = models.ForeignKey(
        'dashboard.ProductVariant', on_delete=models.CASCADE, related_name='stock_movements'
    )
    warehouse     = models.ForeignKey(
        Warehouse, on_delete=models.SET_NULL, null=True, related_name='movements'
    )
    type          = models.CharField(max_length=20, choices=Type.choices)
    quantity      = models.IntegerField()          # + دخل / - خرج
    stock_before  = models.IntegerField()          # snapshot قبل الحركة
    stock_after   = models.IntegerField()          # snapshot بعد الحركة

    # مصدر الحركة (واحد منهم بيكون non-null)
    sales_order   = models.ForeignKey(
        SalesOrder, on_delete=models.SET_NULL, null=True, blank=True, related_name='stock_movements'
    )
    purchase_order = models.ForeignKey(
        'PurchaseOrder', on_delete=models.SET_NULL, null=True, blank=True, related_name='stock_movements'
    )
    return_request = models.ForeignKey(
        'ReturnRequest', on_delete=models.SET_NULL, null=True, blank=True, related_name='stock_movements'
    )

    reason      = models.CharField(max_length=300, blank=True)
    created_by  = models.ForeignKey(
        'dashboard.User', on_delete=models.SET_NULL, null=True, related_name='stock_movements'
    )
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        sign = '+' if self.quantity > 0 else ''
        return f"{self.get_type_display()} {sign}{self.quantity} × {self.variant}"


class StockAlert(models.Model):
    """تنبيه لما المخزون يوصل لحد معين."""
    variant       = models.OneToOneField(
        'dashboard.ProductVariant', on_delete=models.CASCADE, related_name='stock_alert'
    )
    threshold     = models.PositiveIntegerField(default=5)
    is_active     = models.BooleanField(default=True)
    last_triggered_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Alert: {self.variant} ≤ {self.threshold}"


# ============================================================
#  MODULE 3 — PURCHASING
#  شراء بضاعة من موردين ودخولها المخزون
# ============================================================

class Supplier(models.Model):
    """مورد — اللي بنشتري منه البضاعة."""
    name          = models.CharField(max_length=200)
    company       = models.CharField(max_length=200, blank=True)
    email         = models.EmailField(blank=True)
    phone         = models.CharField(max_length=20, blank=True)
    address       = models.TextField(blank=True)
    payment_terms = models.CharField(max_length=200, blank=True)  # مثلاً "30 يوم"
    notes         = models.TextField(blank=True)
    is_active     = models.BooleanField(default=True)
    created_at    = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class PurchaseOrder(models.Model):
    """أمر شراء من مورد."""
    class Status(models.TextChoices):
        DRAFT     = 'draft',     'Draft'
        SENT      = 'sent',      'Sent to Supplier'
        CONFIRMED = 'confirmed', 'Confirmed'
        PARTIAL   = 'partial',   'Partially Received'
        RECEIVED  = 'received',  'Fully Received'
        CANCELLED = 'cancelled', 'Cancelled'

    po_number     = models.CharField(max_length=50, unique=True, blank=True)
    supplier      = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name='purchase_orders')
    status        = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    expected_date = models.DateField(null=True, blank=True)
    warehouse     = models.ForeignKey(
        Warehouse, on_delete=models.SET_NULL, null=True, related_name='purchase_orders'
    )
    total_cost    = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    notes         = models.TextField(blank=True)
    created_by    = models.ForeignKey(
        'dashboard.User', on_delete=models.SET_NULL, null=True, related_name='purchase_orders'
    )
    created_at    = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.po_number:
            self.po_number = f"PO-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    def calculate_total(self):
        self.total_cost = sum(item.total_cost for item in self.items.all())
        self.save(update_fields=['total_cost'])

    def __str__(self):
        return f"{self.po_number} – {self.supplier.name}"


class PurchaseOrderItem(models.Model):
    purchase_order     = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='items')
    variant            = models.ForeignKey(
        'dashboard.ProductVariant', on_delete=models.SET_NULL,
        null=True, related_name='purchase_items'
    )
    product_name       = models.CharField(max_length=300)
    quantity_ordered   = models.PositiveIntegerField()
    quantity_received  = models.PositiveIntegerField(default=0)
    unit_cost          = models.DecimalField(max_digits=10, decimal_places=2)

    @property
    def total_cost(self):
        return self.unit_cost * self.quantity_ordered

    @property
    def is_fully_received(self):
        return self.quantity_received >= self.quantity_ordered

    def __str__(self):
        return f"{self.quantity_ordered}× {self.product_name}"


class GoodsReceipt(models.Model):
    """
    استلام البضاعة من المورد.
    لما يتحفظ → Signal يرفع المخزون تلقائياً.
    """
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='receipts')
    warehouse      = models.ForeignKey(Warehouse, on_delete=models.SET_NULL, null=True)
    received_at    = models.DateTimeField(default=timezone.now)
    received_by    = models.ForeignKey(
        'dashboard.User', on_delete=models.SET_NULL, null=True, related_name='goods_receipts'
    )
    notes          = models.TextField(blank=True)
    created_at     = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Receipt for {self.purchase_order.po_number} on {self.received_at.date()}"


# ============================================================
#  MODULE 4 — RETURNS
#  مرتجعات مع إرجاع المخزون التلقائي
# ============================================================

class ReturnRequest(models.Model):
    class Status(models.TextChoices):
        PENDING   = 'pending',   'Pending Review'
        APPROVED  = 'approved',  'Approved'
        REJECTED  = 'rejected',  'Rejected'
        COMPLETED = 'completed', 'Completed'

    class Reason(models.TextChoices):
        DEFECTIVE    = 'defective',    'Defective Product'
        WRONG_ITEM   = 'wrong_item',   'Wrong Item Sent'
        NOT_AS_DESC  = 'not_as_desc',  'Not As Described'
        CHANGED_MIND = 'changed_mind', 'Customer Changed Mind'
        DAMAGED      = 'damaged',      'Damaged in Shipping'
        OTHER        = 'other',        'Other'

    class RefundMethod(models.TextChoices):
        CASH     = 'cash',     'Cash Refund'
        WALLET   = 'wallet',   'Store Wallet'
        ORIGINAL = 'original', 'Original Payment Method'
        EXCHANGE = 'exchange', 'Exchange Only'

    sales_order    = models.ForeignKey(SalesOrder, on_delete=models.CASCADE, related_name='return_requests')
    status         = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    reason         = models.CharField(max_length=30, choices=Reason.choices)
    customer_notes = models.TextField(blank=True)
    staff_notes    = models.TextField(blank=True)
    refund_amount  = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    refund_method  = models.CharField(max_length=20, choices=RefundMethod.choices, default=RefundMethod.CASH)
    handled_by     = models.ForeignKey(
        'dashboard.User', on_delete=models.SET_NULL, null=True, related_name='handled_returns'
    )
    created_at     = models.DateTimeField(auto_now_add=True)
    resolved_at    = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Return #{self.pk} for {self.sales_order.order_number} – {self.status}"


class ReturnItem(models.Model):
    """كل منتج في المرتجع له condition منفصل."""
    class Condition(models.TextChoices):
        GOOD       = 'good',       'Good — يرجع للمخزون'
        DAMAGED    = 'damaged',    'Damaged — يرجع بعد إصلاح'
        UNSELLABLE = 'unsellable', 'Unsellable — لا يرجع'

    return_request = models.ForeignKey(ReturnRequest, on_delete=models.CASCADE, related_name='items')
    variant        = models.ForeignKey(
        'dashboard.ProductVariant', on_delete=models.SET_NULL,
        null=True, related_name='return_items'
    )
    product_name   = models.CharField(max_length=300)
    quantity       = models.PositiveIntegerField()
    condition      = models.CharField(max_length=20, choices=Condition.choices, default=Condition.GOOD)

    @property
    def should_restock(self):
        """يرجع المخزون بس لو الحالة good."""
        return self.condition == self.Condition.GOOD

    def __str__(self):
        return f"{self.quantity}× {self.product_name} ({self.condition})"


# ============================================================
#  MODULE 5 — FINANCE
#  مالية بسيطة: إيراد تلقائي + مصاريف يدوية = ربح
# ============================================================

class ExpenseCategory(models.Model):
    """تصنيفات المصاريف — إيجار / شحن / تسويق / مرتبات..."""
    name      = models.CharField(max_length=100, unique=True)
    icon      = models.CharField(max_length=50, blank=True)   # emoji أو icon name
    color     = models.CharField(max_length=20, blank=True)   # hex color
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = 'Expense Categories'

    def __str__(self):
        return self.name


class Expense(models.Model):
    """مصروف يدوي — موظف يدخله."""
    category    = models.ForeignKey(ExpenseCategory, on_delete=models.SET_NULL, null=True, related_name='expenses')
    amount      = models.DecimalField(max_digits=10, decimal_places=2)
    currency    = models.CharField(max_length=10, default='EGP')
    date        = models.DateField(default=timezone.now)
    description = models.CharField(max_length=500)
    receipt     = models.ImageField(upload_to='expenses/receipts/', blank=True, null=True)
    is_recurring = models.BooleanField(default=False)
    created_by  = models.ForeignKey(
        'dashboard.User', on_delete=models.SET_NULL, null=True, related_name='expenses'
    )
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f"{self.description} – {self.amount} ({self.date})"


class Revenue(models.Model):
    """
    إيراد — بيتنشأ تلقائياً من SalesOrder Signal.
    ممكن يتنشأ يدوي كمان لو في إيراد خارج المبيعات.
    """
    class Source(models.TextChoices):
        SALE         = 'sale',        'Sales Order'
        MANUAL       = 'manual',      'Manual Entry'
        OTHER        = 'other',       'Other'

    source       = models.CharField(max_length=20, choices=Source.choices)
    sales_order  = models.OneToOneField(
        SalesOrder, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='revenue_entry'
    )
    amount       = models.DecimalField(max_digits=10, decimal_places=2)
    currency     = models.CharField(max_length=10, default='EGP')
    date         = models.DateField(default=timezone.now)
    description  = models.CharField(max_length=300, blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f"Revenue {self.amount} – {self.date}"


class FinancialSummary(models.Model):
    """
    Snapshot يومي — بيتحسب ويتخزن مرة في اليوم.
    ده عشان التقارير تكون سريعة ومش بتعمل query كبيرة.
    """
    date             = models.DateField(unique=True)
    total_revenue    = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_expenses   = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    net_profit       = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    orders_count     = models.PositiveIntegerField(default=0)
    returned_amount  = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    generated_at     = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date']
        verbose_name_plural = 'Financial Summaries'

    def __str__(self):
        return f"Summary {self.date}: Revenue={self.total_revenue} Profit={self.net_profit}"


# ============================================================
#  MODULE 6 — SHIPPING
#  شركات الشحن وتتبع كل شحنة
# ============================================================

class ShippingCarrier(models.Model):
    """شركة شحن — أرامكس / Bosta / J&T / ..."""
    name                 = models.CharField(max_length=100)
    tracking_url_template = models.CharField(
        max_length=300, blank=True,
        help_text="استخدم {tracking_number} مكان الرقم. مثال: https://track.aramex.com/{tracking_number}"
    )
    default_cost         = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    phone                = models.CharField(max_length=20, blank=True)
    is_active            = models.BooleanField(default=True)

    def get_tracking_url(self, tracking_number):
        if self.tracking_url_template and tracking_number:
            return self.tracking_url_template.replace('{tracking_number}', tracking_number)
        return None

    def __str__(self):
        return self.name


class ShipmentRecord(models.Model):
    """شحنة مرتبطة بـ SalesOrder."""
    class Status(models.TextChoices):
        PENDING    = 'pending',    'Pending Pickup'
        PICKED_UP  = 'picked_up', 'Picked Up'
        IN_TRANSIT = 'in_transit', 'In Transit'
        OUT_FOR_DELIVERY = 'out_for_delivery', 'Out for Delivery'
        DELIVERED  = 'delivered',  'Delivered'
        FAILED     = 'failed',     'Delivery Failed'
        RETURNED   = 'returned',   'Returned to Sender'

    sales_order      = models.OneToOneField(SalesOrder, on_delete=models.CASCADE, related_name='shipment')
    carrier          = models.ForeignKey(ShippingCarrier, on_delete=models.SET_NULL, null=True, related_name='shipments')
    tracking_number  = models.CharField(max_length=200, blank=True)
    status           = models.CharField(max_length=30, choices=Status.choices, default=Status.PENDING)
    shipping_cost    = models.DecimalField(max_digits=8, decimal_places=2, default=0)

    # بيانات المستلم
    recipient_name   = models.CharField(max_length=200)
    recipient_phone  = models.CharField(max_length=20)
    address          = models.CharField(max_length=500)
    city             = models.CharField(max_length=100)
    country          = models.CharField(max_length=100)
    postal_code      = models.CharField(max_length=20, blank=True)

    shipped_at       = models.DateTimeField(null=True, blank=True)
    delivered_at     = models.DateTimeField(null=True, blank=True)
    estimated_delivery = models.DateField(null=True, blank=True)
    notes            = models.TextField(blank=True)
    created_at       = models.DateTimeField(auto_now_add=True)
    updated_at       = models.DateTimeField(auto_now=True)

    @property
    def tracking_url(self):
        if self.carrier:
            return self.carrier.get_tracking_url(self.tracking_number)
        return None

    def __str__(self):
        return f"Shipment for {self.sales_order.order_number} – {self.status}"


class ShipmentEvent(models.Model):
    """تاريخ تحديثات الشحنة — زي timeline."""
    shipment    = models.ForeignKey(ShipmentRecord, on_delete=models.CASCADE, related_name='events')
    status      = models.CharField(max_length=30, choices=ShipmentRecord.Status.choices)
    description = models.CharField(max_length=300)
    location    = models.CharField(max_length=200, blank=True)
    event_time  = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-event_time']

    def __str__(self):
        return f"{self.status} @ {self.event_time} – {self.shipment}"


# ============================================================
#  MODULE 7 — CRM
#  إدارة العملاء وتاريخهم وتصنيفهم
# ============================================================

class CustomerTag(models.Model):
    """تاج للعميل — VIP / منتظم / متأخر الدفع..."""
    name  = models.CharField(max_length=50, unique=True)
    color = models.CharField(max_length=20, default='#888888')

    def __str__(self):
        return self.name


class CustomerProfile(models.Model):
    """
    ملف العميل الشامل.
    ممكن يكون مربوط بـ User (لو اشترى أونلاين) أو مش مربوط (واتساب/تليفون).
    """
    class Source(models.TextChoices):
        ONLINE   = 'online',   'Online Store'
        WHATSAPP = 'whatsapp', 'WhatsApp'
        PHONE    = 'phone',    'Phone'
        WALK_IN  = 'walk_in',  'Walk-in'
        REFERRAL = 'referral', 'Referral'
        SOCIAL   = 'social',   'Social Media'

    user         = models.OneToOneField(
        'dashboard.User', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='crm_profile'
    )
    name         = models.CharField(max_length=200)
    phone        = models.CharField(max_length=20, blank=True)
    email        = models.EmailField(blank=True)
    source       = models.CharField(max_length=20, choices=Source.choices, default=Source.ONLINE)
    tags         = models.ManyToManyField(CustomerTag, blank=True, related_name='customers')

    # Cached fields — بيتحدثوا من Signal
    total_orders  = models.PositiveIntegerField(default=0)
    total_spent   = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    avg_order_value = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    last_order_at = models.DateTimeField(null=True, blank=True)

    is_blocked    = models.BooleanField(default=False)
    created_at    = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-total_spent']

    def update_stats(self):
        """يتشغل من Signal بعد أي SalesOrder."""
        orders = self.sales_orders.filter(status__in=['confirmed', 'shipped', 'delivered'])
        self.total_orders = orders.count()
        self.total_spent = sum(o.total for o in orders)
        self.avg_order_value = (self.total_spent / self.total_orders) if self.total_orders else 0
        last = orders.order_by('-created_at').first()
        self.last_order_at = last.created_at if last else None
        self.save(update_fields=['total_orders', 'total_spent', 'avg_order_value', 'last_order_at'])

    def __str__(self):
        return f"{self.name} ({self.phone})"


class CustomerNote(models.Model):
    """ملاحظات الموظفين على العميل."""
    customer   = models.ForeignKey(CustomerProfile, on_delete=models.CASCADE, related_name='notes')
    note       = models.TextField()
    is_pinned  = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        'dashboard.User', on_delete=models.SET_NULL, null=True, related_name='customer_notes'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-is_pinned', '-created_at']

    def __str__(self):
        return f"Note on {self.customer.name}: {self.note[:50]}"


class CustomerSegment(models.Model):
    """
    شريحة عملاء — بيتفلتر حسب قواعد.
    مثال: "اشترى أكتر من 3 مرات" أو "ما اشتراش من 60 يوم".
    """
    name             = models.CharField(max_length=100)
    description      = models.TextField(blank=True)
    filter_rules     = models.JSONField(default=dict)  # {"min_orders": 3, "days_inactive": 60}
    customers        = models.ManyToManyField(CustomerProfile, blank=True, related_name='segments')
    last_refreshed_at = models.DateTimeField(null=True, blank=True)
    created_at       = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.customers.count()} customers)"


# ============================================================
#  MODULE 8 — REPORTS
#  Snapshots للتقارير عشان السرعة
# ============================================================

class ReportSnapshot(models.Model):
    """
    تقرير محفوظ — بيتنشأ بـ Celery task أو يدوي.
    الداتا JSON عشان مرونة كاملة.
    """
    class ReportType(models.TextChoices):
        SALES_DAILY      = 'sales_daily',      'Daily Sales'
        SALES_MONTHLY    = 'sales_monthly',    'Monthly Sales'
        SALES_BY_SOURCE  = 'sales_by_source',  'Sales by Channel'
        TOP_PRODUCTS     = 'top_products',     'Top Products'
        INVENTORY        = 'inventory',        'Inventory Status'
        FINANCE_MONTHLY  = 'finance_monthly',  'Monthly Finance'
        CUSTOMER_VALUE   = 'customer_value',   'Customer LTV'
        STAFF_PERF       = 'staff_perf',       'Staff Performance'
        RETURN_ANALYSIS  = 'return_analysis',  'Return Analysis'

    report_type  = models.CharField(max_length=30, choices=ReportType.choices)
    period_start = models.DateField()
    period_end   = models.DateField()
    data         = models.JSONField(default=dict)  # الأرقام المحسوبة كاملة
    generated_at = models.DateTimeField(auto_now=True)
    generated_by = models.ForeignKey(
        'dashboard.User', on_delete=models.SET_NULL, null=True, related_name='generated_reports'
    )

    class Meta:
        ordering = ['-generated_at']
        unique_together = ('report_type', 'period_start', 'period_end')

    def __str__(self):
        return f"{self.get_report_type_display()} ({self.period_start} → {self.period_end})"


# ============================================================
#  MODULE 9 — HR
#  إدارة الفريق والحضور والأهداف
# ============================================================

class Department(models.Model):
    """قسم — مبيعات / مخزون / دعم..."""
    name       = models.CharField(max_length=100, unique=True)
    manager    = models.ForeignKey(
        'Employee', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='managed_departments'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Employee(models.Model):
    """ملف الموظف — مربوط بـ User."""
    class EmploymentType(models.TextChoices):
        FULL_TIME = 'full_time', 'Full Time'
        PART_TIME = 'part_time', 'Part Time'
        CONTRACT  = 'contract',  'Contract'
        FREELANCE = 'freelance', 'Freelance'

    user = models.OneToOneField(
        'dashboard.User', on_delete=models.CASCADE,
        null=True, blank=True,          # ← اختياري دلوقتي
        related_name='employee_profile'
    )
    name       = models.CharField(max_length=200)   # ← جديد
    department      = models.ForeignKey(
        Department, on_delete=models.SET_NULL, null=True, related_name='employees'
    )
    job_title       = models.CharField(max_length=200)
    employment_type = models.CharField(max_length=20, choices=EmploymentType.choices, default=EmploymentType.FULL_TIME)
    salary          = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    hire_date       = models.DateField()
    national_id     = models.CharField(max_length=50, blank=True)
    emergency_contact = models.CharField(max_length=200, blank=True)
    is_active       = models.BooleanField(default=True)
    created_at      = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.get_full_name()} – {self.job_title}"


class Attendance(models.Model):
    """سجل الحضور والانصراف."""
    class AttendanceStatus(models.TextChoices):
        PRESENT  = 'present',  'Present'
        ABSENT   = 'absent',   'Absent'
        LATE     = 'late',     'Late'
        HALF_DAY = 'half_day', 'Half Day'
        ON_LEAVE = 'on_leave', 'On Leave'

    employee  = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='attendance')
    date      = models.DateField()
    check_in  = models.TimeField(null=True, blank=True)
    check_out = models.TimeField(null=True, blank=True)
    status    = models.CharField(max_length=20, choices=AttendanceStatus.choices, default=AttendanceStatus.PRESENT)
    notes     = models.CharField(max_length=300, blank=True)

    class Meta:
        unique_together = ('employee', 'date')
        ordering = ['-date']

    @property
    def hours_worked(self):
        if self.check_in and self.check_out:
            from datetime import datetime, date
            dt_in  = datetime.combine(date.today(), self.check_in)
            dt_out = datetime.combine(date.today(), self.check_out)
            diff = dt_out - dt_in
            return round(diff.seconds / 3600, 2)
        return 0

    def __str__(self):
        return f"{self.employee} – {self.date} ({self.status})"


class LeaveRequest(models.Model):
    """طلب إجازة."""
    class LeaveType(models.TextChoices):
        ANNUAL  = 'annual',  'Annual Leave'
        SICK    = 'sick',    'Sick Leave'
        UNPAID  = 'unpaid',  'Unpaid Leave'
        MATERNITY = 'maternity', 'Maternity Leave'
        EMERGENCY = 'emergency', 'Emergency'

    class Status(models.TextChoices):
        PENDING  = 'pending',  'Pending'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'

    employee    = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='leave_requests')
    type        = models.CharField(max_length=20, choices=LeaveType.choices)
    start_date  = models.DateField()
    end_date    = models.DateField()
    reason      = models.TextField(blank=True)
    status      = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    approved_by = models.ForeignKey(
        'dashboard.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_leaves'
    )
    created_at  = models.DateTimeField(auto_now_add=True)

    @property
    def days_count(self):
        return (self.end_date - self.start_date).days + 1

    def __str__(self):
        return f"{self.employee} – {self.type} ({self.days_count} days)"


class SalesTarget(models.Model):
    """هدف مبيعات للموظف في فترة معينة."""
    employee       = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='sales_targets')
    period_start   = models.DateField()
    period_end     = models.DateField()
    target_amount  = models.DecimalField(max_digits=12, decimal_places=2)
    notes          = models.TextField(blank=True)
    created_at     = models.DateTimeField(auto_now_add=True)

    @property
    def achieved_amount(self):
        """يتحسب من الـ SalesOrders اللي عملها الموظف في الفترة دي."""
        return SalesOrder.objects.filter(
            created_by=self.employee.user,
            created_at__date__gte=self.period_start,
            created_at__date__lte=self.period_end,
            status__in=['confirmed', 'shipped', 'delivered']
        ).aggregate(
            total=models.Sum('total')
        )['total'] or 0

    @property
    def achievement_percentage(self):
        if self.target_amount:
            return round((self.achieved_amount / self.target_amount) * 100, 1)
        return 0

    def __str__(self):
        return f"{self.employee} – Target: {self.target_amount} ({self.period_start}→{self.period_end})"