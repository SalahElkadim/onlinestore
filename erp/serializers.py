"""
============================================================
  ERP APPLICATION — serializers.py
============================================================
  Modules:
  1.  Sales        → Quotation, QuotationItem, SalesOrder, SalesOrderItem
  2.  Inventory    → Warehouse, WarehouseStock, StockMovement, StockAlert
  3.  Purchasing   → Supplier, PurchaseOrder, PurchaseOrderItem, GoodsReceipt
  4.  Returns      → ReturnRequest, ReturnItem
  5.  Finance      → ExpenseCategory, Expense, Revenue, FinancialSummary
  6.  Shipping     → ShippingCarrier, ShipmentRecord, ShipmentEvent
  7.  CRM          → CustomerTag, CustomerProfile, CustomerNote, CustomerSegment
  8.  Reports      → ReportSnapshot
  9.  HR           → Department, Employee, Attendance, LeaveRequest, SalesTarget
============================================================
"""

from rest_framework import serializers
from .models import (
    # Sales
    Quotation, QuotationItem, SalesOrder, SalesOrderItem,
    # Inventory
    Warehouse, WarehouseStock, StockMovement, StockAlert,
    # Purchasing
    Supplier, PurchaseOrder, PurchaseOrderItem, GoodsReceipt,
    # Returns
    ReturnRequest, ReturnItem,
    # Finance
    ExpenseCategory, Expense, Revenue, FinancialSummary,
    # Shipping
    ShippingCarrier, ShipmentRecord, ShipmentEvent,
    # CRM
    CustomerTag, CustomerProfile, CustomerNote, CustomerSegment,
    # Reports
    ReportSnapshot,
    # HR
    Department, Employee, Attendance, LeaveRequest, SalesTarget,
)


# ============================================================
#  MODULE 1 — SALES
# ============================================================

class QuotationItemSerializer(serializers.ModelSerializer):
    total_price = serializers.ReadOnlyField()

    class Meta:
        model = QuotationItem
        fields = [
            'id', 'variant', 'product_name', 'variant_name',
            'quantity', 'unit_price', 'note', 'total_price',
        ]


class QuotationSerializer(serializers.ModelSerializer):
    items      = QuotationItemSerializer(many=True, read_only=True)
    subtotal   = serializers.ReadOnlyField()
    is_expired = serializers.ReadOnlyField()

    class Meta:
        model = Quotation
        fields = [
            'id', 'quotation_number', 'customer_name', 'customer_phone',
            'customer_email', 'status', 'valid_until', 'notes',
            'created_by', 'converted_to', 'subtotal', 'is_expired',
            'items', 'created_at', 'updated_at',
        ]
        read_only_fields = ['quotation_number', 'created_at', 'updated_at']


class QuotationWriteSerializer(serializers.ModelSerializer):
    """للإنشاء والتعديل — بدون items (بيتضافوا منفصلين)."""
    class Meta:
        model = Quotation
        fields = ['id',
            'customer_name', 'customer_phone', 'customer_email',
            'status', 'valid_until', 'notes', 'created_by', 'converted_to',
        ]


class SalesOrderItemSerializer(serializers.ModelSerializer):
    total_price = serializers.ReadOnlyField()

    class Meta:
        model = SalesOrderItem
        fields = [
            'id', 'variant', 'product_name', 'variant_name',
            'unit_price', 'quantity', 'discount', 'note', 'total_price',
        ]


class SalesOrderSerializer(serializers.ModelSerializer):
    items       = SalesOrderItemSerializer(many=True, read_only=True)
    balance_due = serializers.ReadOnlyField()
    is_fully_paid = serializers.ReadOnlyField()

    class Meta:
        model = SalesOrder
        fields = [
            'id', 'order_number', 'source', 'status',
            'online_order', 'customer', 'customer_name', 'customer_phone',
            'customer_email', 'customer_note',
            'subtotal', 'discount_amount', 'tax_amount', 'shipping_cost', 'total',
            'payment_method', 'payment_status', 'amount_paid',
            'balance_due', 'is_fully_paid',
            'reference_code', 'internal_notes', 'created_by',
            'items', 'created_at', 'updated_at',
        ]
        read_only_fields = ['order_number', 'subtotal', 'total', 'created_at', 'updated_at']


from decimal import Decimal
class SalesOrderWriteSerializer(serializers.ModelSerializer):
    # ✅ اقبل subtotal وtotal من الـ frontend كـ fallback
    # الـ signal هيحسبهم تاني بعد إضافة الـ items، بس لو جم من frontend خليهم
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    total    = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
 
    class Meta:
        model = SalesOrder
        fields = [
            'id',
            'source', 'status', 'online_order', 'customer',
            'customer_name', 'customer_phone', 'customer_email', 'customer_note',
            'subtotal', 'total',                          # ✅ مضافين
            'discount_amount', 'tax_amount', 'shipping_cost',
            'payment_method', 'payment_status', 'amount_paid',
            'reference_code', 'internal_notes', 'created_by',
        ]
        read_only_fields = ['id']
 
    def _recalc_total(self, order):
        """
        يحسب الـ total من الـ subtotal الموجود.
        لو الـ subtotal جه من الـ frontend استخدمه،
        لو لأ احسبه من الـ items (لو موجودة).
        """
        items_subtotal = sum(item.total_price for item in order.items.all())
 
        # لو في items حقيقية في الـ DB، استخدمهم — أدق
        if items_subtotal > 0:
            order.subtotal = items_subtotal
 
        order.total = (
            Decimal(str(order.subtotal or 0))
            - Decimal(str(order.discount_amount or 0))
            + Decimal(str(order.tax_amount or 0))
            + Decimal(str(order.shipping_cost or 0))
        )
        order.save(update_fields=['subtotal', 'total'])
        return order
 
    def create(self, validated_data):
        order = super().create(validated_data)
        return self._recalc_total(order)
 
    def update(self, instance, validated_data):
        order = super().update(instance, validated_data)
        return self._recalc_total(order)

# ============================================================
#  MODULE 2 — INVENTORY
# ============================================================

class WarehouseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Warehouse
        fields = ['id', 'name', 'location', 'is_default', 'is_active', 'created_at']
        read_only_fields = ['created_at']


class WarehouseStockSerializer(serializers.ModelSerializer):
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)
    variant_name   = serializers.SerializerMethodField()

    class Meta:
        model = WarehouseStock
        fields = ['id', 'warehouse', 'warehouse_name', 'variant', 'variant_name', 'quantity']

    def get_variant_name(self, obj):
        return str(obj.variant) if obj.variant else None


class StockMovementSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockMovement
        fields = [
            'id', 'variant', 'warehouse', 'type', 'quantity',
            'stock_before', 'stock_after',
            'sales_order', 'purchase_order', 'return_request',
            'reason', 'created_by', 'created_at',
        ]
        read_only_fields = ['created_at']


class StockAlertSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockAlert
        fields = ['id', 'variant', 'threshold', 'is_active', 'last_triggered_at']


# ============================================================
#  MODULE 3 — PURCHASING
# ============================================================

class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = [
            'id', 'name', 'company', 'email', 'phone',
            'address', 'payment_terms', 'notes', 'is_active', 'created_at',
        ]
        read_only_fields = ['created_at']


class PurchaseOrderItemSerializer(serializers.ModelSerializer):
    total_cost        = serializers.ReadOnlyField()
    is_fully_received = serializers.ReadOnlyField()

    class Meta:
        model = PurchaseOrderItem
        fields = [
            'id', 'variant', 'product_name',
            'quantity_ordered', 'quantity_received',
            'unit_cost', 'total_cost', 'is_fully_received',
        ]


class PurchaseOrderSerializer(serializers.ModelSerializer):
    items            = PurchaseOrderItemSerializer(many=True, read_only=True)
    supplier_name    = serializers.CharField(source='supplier.name', read_only=True)

    class Meta:
        model = PurchaseOrder
        fields = [
            'id', 'po_number', 'supplier', 'supplier_name', 'status',
            'expected_date', 'warehouse', 'total_cost', 'notes',
            'created_by', 'items', 'created_at', 'updated_at',
        ]
        read_only_fields = ['po_number', 'created_at', 'updated_at']


class PurchaseOrderWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = PurchaseOrder
        fields = ['id',  
            'supplier', 'status', 'expected_date',
            'warehouse', 'notes', 'created_by',
        ]


class GoodsReceiptSerializer(serializers.ModelSerializer):
    class Meta:
        model = GoodsReceipt
        fields = [
            'id', 'purchase_order', 'warehouse',
            'received_at', 'received_by', 'notes', 'created_at',
        ]
        read_only_fields = ['created_at']


# ============================================================
#  MODULE 4 — RETURNS
# ============================================================

class ReturnItemSerializer(serializers.ModelSerializer):
    should_restock = serializers.ReadOnlyField()

    class Meta:
        model = ReturnItem
        fields = [
            'id', 'variant', 'product_name',
            'quantity', 'condition', 'should_restock',
        ]


class ReturnRequestSerializer(serializers.ModelSerializer):
    items = ReturnItemSerializer(many=True, read_only=True)

    class Meta:
        model = ReturnRequest
        fields = [
            'id', 'sales_order', 'status', 'reason',
            'customer_notes', 'staff_notes',
            'refund_amount', 'refund_method',
            'handled_by', 'items', 'created_at', 'resolved_at',
        ]
        read_only_fields = ['created_at']


class ReturnRequestWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReturnRequest
        fields = [
            'sales_order', 'status', 'reason',
            'customer_notes', 'staff_notes',
            'refund_amount', 'refund_method', 'handled_by',
        ]


# ============================================================
#  MODULE 5 — FINANCE
# ============================================================

class ExpenseCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpenseCategory
        fields = ['id', 'name', 'icon', 'color', 'is_active']


class ExpenseSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)

    class Meta:
        model = Expense
        fields = [
            'id', 'category', 'category_name', 'amount', 'currency',
            'date', 'description', 'receipt', 'is_recurring',
            'created_by', 'created_at',
        ]
        read_only_fields = ['created_at']


class RevenueSerializer(serializers.ModelSerializer):
    class Meta:
        model = Revenue
        fields = [
            'id', 'source', 'sales_order', 'amount',
            'currency', 'date', 'description', 'created_at',
        ]
        read_only_fields = ['created_at']


class FinancialSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = FinancialSummary
        fields = [
            'id', 'date', 'total_revenue', 'total_expenses',
            'net_profit', 'orders_count', 'returned_amount', 'generated_at',
        ]
        read_only_fields = ['generated_at']


# ============================================================
#  MODULE 6 — SHIPPING
# ============================================================

class ShippingCarrierSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShippingCarrier
        fields = [
            'id', 'name', 'tracking_url_template',
            'default_cost', 'phone', 'is_active',
        ]


class ShipmentEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShipmentEvent
        fields = ['id', 'status', 'description', 'location', 'event_time']


class ShipmentRecordSerializer(serializers.ModelSerializer):
    events       = ShipmentEventSerializer(many=True, read_only=True)
    tracking_url = serializers.ReadOnlyField()

    class Meta:
        model = ShipmentRecord
        fields = [
            'id', 'sales_order', 'carrier', 'tracking_number', 'status',
            'shipping_cost', 'recipient_name', 'recipient_phone',
            'address', 'city', 'country', 'postal_code',
            'shipped_at', 'delivered_at', 'estimated_delivery',
            'notes', 'tracking_url', 'events', 'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']


class ShipmentRecordWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShipmentRecord
        fields = [
            'sales_order', 'carrier', 'tracking_number', 'status',
            'shipping_cost', 'recipient_name', 'recipient_phone',
            'address', 'city', 'country', 'postal_code',
            'shipped_at', 'delivered_at', 'estimated_delivery', 'notes',
        ]


# ============================================================
#  MODULE 7 — CRM
# ============================================================

class CustomerTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerTag
        fields = ['id', 'name', 'color']


class CustomerNoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerNote
        fields = ['id', 'note', 'is_pinned', 'created_by', 'created_at']
        read_only_fields = ['created_at']


class CustomerProfileSerializer(serializers.ModelSerializer):
    tags  = CustomerTagSerializer(many=True, read_only=True)
    notes = CustomerNoteSerializer(many=True, read_only=True)

    class Meta:
        model = CustomerProfile
        fields = [
            'id', 'user', 'name', 'phone', 'email', 'source',
            'tags', 'total_orders', 'total_spent', 'avg_order_value',
            'last_order_at', 'is_blocked', 'notes', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'total_orders', 'total_spent', 'avg_order_value',
            'last_order_at', 'created_at', 'updated_at',
        ]


class CustomerProfileWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerProfile
        fields = ['user', 'name', 'phone', 'email', 'source', 'tags', 'is_blocked']


class CustomerSegmentSerializer(serializers.ModelSerializer):
    customers_count = serializers.SerializerMethodField()

    class Meta:
        model = CustomerSegment
        fields = [
            'id', 'name', 'description', 'filter_rules',
            'customers_count', 'last_refreshed_at', 'created_at',
        ]
        read_only_fields = ['last_refreshed_at', 'created_at']

    def get_customers_count(self, obj):
        return obj.customers.count()


# ============================================================
#  MODULE 8 — REPORTS
# ============================================================

class ReportSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportSnapshot
        fields = [
            'id', 'report_type', 'period_start', 'period_end',
            'data', 'generated_at', 'generated_by',
        ]
        read_only_fields = ['generated_at']


# ============================================================
#  MODULE 9 — HR
# ============================================================

class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ['id', 'name', 'manager', 'created_at']
        read_only_fields = ['created_at']


class EmployeeSerializer(serializers.ModelSerializer):
    full_name       = serializers.SerializerMethodField()
    department_name = serializers.CharField(source='department.name', read_only=True)

    class Meta:
        model = Employee
        fields = [
            'id', 'user', 'full_name', 'department', 'department_name',
            'job_title', 'employment_type', 'salary', 'hire_date',
            'national_id', 'emergency_contact', 'is_active', 'created_at',
        ]
        read_only_fields = ['created_at']

    def get_full_name(self, obj):
        return obj.user.get_full_name()


class EmployeeWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employee
        fields = [
            'user', 'department', 'job_title', 'employment_type',
            'salary', 'hire_date', 'national_id', 'emergency_contact', 'is_active',
        ]


class AttendanceSerializer(serializers.ModelSerializer):
    hours_worked = serializers.ReadOnlyField()

    class Meta:
        model = Attendance
        fields = [
            'id', 'employee', 'date', 'check_in',
            'check_out', 'status', 'notes', 'hours_worked',
        ]


class LeaveRequestSerializer(serializers.ModelSerializer):
    days_count = serializers.ReadOnlyField()

    class Meta:
        model = LeaveRequest
        fields = [
            'id', 'employee', 'type', 'start_date', 'end_date',
            'reason', 'status', 'approved_by', 'days_count', 'created_at',
        ]
        read_only_fields = ['created_at']


class SalesTargetSerializer(serializers.ModelSerializer):
    achieved_amount        = serializers.ReadOnlyField()
    achievement_percentage = serializers.ReadOnlyField()

    class Meta:
        model = SalesTarget
        fields = [
            'id', 'employee', 'period_start', 'period_end',
            'target_amount', 'achieved_amount', 'achievement_percentage',
            'notes', 'created_at',
        ]
        read_only_fields = ['created_at']