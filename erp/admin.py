"""
============================================================
  ERP APPLICATION — admin.py
  تسجيل كل الـ Models في Django Admin
============================================================
"""

from django.contrib import admin
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


# ─────────────────────────────────────────────
#  Inline classes
# ─────────────────────────────────────────────

class QuotationItemInline(admin.TabularInline):
    model = QuotationItem
    extra = 1


class SalesOrderItemInline(admin.TabularInline):
    model = SalesOrderItem
    extra = 0
    readonly_fields = ('total_price',)


class PurchaseOrderItemInline(admin.TabularInline):
    model = PurchaseOrderItem
    extra = 1


class ReturnItemInline(admin.TabularInline):
    model = ReturnItem
    extra = 0


class ShipmentEventInline(admin.TabularInline):
    model = ShipmentEvent
    extra = 0


class CustomerNoteInline(admin.TabularInline):
    model = CustomerNote
    extra = 0


# ─────────────────────────────────────────────
#  MODULE 1 — SALES
# ─────────────────────────────────────────────

@admin.register(Quotation)
class QuotationAdmin(admin.ModelAdmin):
    list_display = ('quotation_number', 'customer_name', 'status', 'subtotal', 'valid_until', 'created_at')
    list_filter = ('status',)
    search_fields = ('quotation_number', 'customer_name', 'customer_phone')
    inlines = [QuotationItemInline]
    readonly_fields = ('quotation_number', 'subtotal')


@admin.register(SalesOrder)
class SalesOrderAdmin(admin.ModelAdmin):
    list_display  = ('order_number', 'source', 'customer_name', 'status', 'payment_status', 'total', 'created_at')
    list_filter   = ('source', 'status', 'payment_status')
    search_fields = ('order_number', 'customer_name', 'customer_phone', 'reference_code')
    inlines       = [SalesOrderItemInline]
    readonly_fields = ('order_number', 'balance_due')


# ─────────────────────────────────────────────
#  MODULE 2 — INVENTORY
# ─────────────────────────────────────────────

@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ('name', 'location', 'is_default', 'is_active')
    list_filter  = ('is_active', 'is_default')


@admin.register(WarehouseStock)
class WarehouseStockAdmin(admin.ModelAdmin):
    list_display  = ('variant', 'warehouse', 'quantity')
    list_filter   = ('warehouse',)
    search_fields = ('variant__product__name',)


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ('variant', 'type', 'quantity', 'stock_before', 'stock_after', 'warehouse', 'created_at')
    list_filter  = ('type', 'warehouse')
    search_fields = ('variant__product__name', 'reason')
    readonly_fields = ('stock_before', 'stock_after', 'created_at')


@admin.register(StockAlert)
class StockAlertAdmin(admin.ModelAdmin):
    list_display = ('variant', 'threshold', 'is_active', 'last_triggered_at')
    list_filter  = ('is_active',)


# ─────────────────────────────────────────────
#  MODULE 3 — PURCHASING
# ─────────────────────────────────────────────

@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display  = ('name', 'company', 'phone', 'email', 'is_active')
    list_filter   = ('is_active',)
    search_fields = ('name', 'company', 'email')


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ('po_number', 'supplier', 'status', 'total_cost', 'expected_date', 'created_at')
    list_filter  = ('status',)
    search_fields = ('po_number', 'supplier__name')
    inlines = [PurchaseOrderItemInline]
    readonly_fields = ('po_number',)


@admin.register(GoodsReceipt)
class GoodsReceiptAdmin(admin.ModelAdmin):
    list_display = ('purchase_order', 'warehouse', 'received_at', 'received_by')
    list_filter  = ('warehouse',)


# ─────────────────────────────────────────────
#  MODULE 4 — RETURNS
# ─────────────────────────────────────────────

@admin.register(ReturnRequest)
class ReturnRequestAdmin(admin.ModelAdmin):
    list_display = ('pk', 'sales_order', 'status', 'reason', 'refund_amount', 'refund_method', 'created_at')
    list_filter  = ('status', 'reason', 'refund_method')
    search_fields = ('sales_order__order_number',)
    inlines = [ReturnItemInline]


# ─────────────────────────────────────────────
#  MODULE 5 — FINANCE
# ─────────────────────────────────────────────

@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'icon', 'color', 'is_active')


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('description', 'category', 'amount', 'currency', 'date', 'created_by')
    list_filter  = ('category', 'currency', 'is_recurring')
    search_fields = ('description',)
    date_hierarchy = 'date'


@admin.register(Revenue)
class RevenueAdmin(admin.ModelAdmin):
    list_display = ('source', 'amount', 'currency', 'date', 'description')
    list_filter  = ('source', 'currency')
    date_hierarchy = 'date'


@admin.register(FinancialSummary)
class FinancialSummaryAdmin(admin.ModelAdmin):
    list_display = ('date', 'total_revenue', 'total_expenses', 'net_profit', 'orders_count')
    date_hierarchy = 'date'
    readonly_fields = ('generated_at',)


# ─────────────────────────────────────────────
#  MODULE 6 — SHIPPING
# ─────────────────────────────────────────────

@admin.register(ShippingCarrier)
class ShippingCarrierAdmin(admin.ModelAdmin):
    list_display = ('name', 'default_cost', 'phone', 'is_active')


@admin.register(ShipmentRecord)
class ShipmentRecordAdmin(admin.ModelAdmin):
    list_display = ('sales_order', 'carrier', 'tracking_number', 'status', 'shipped_at', 'delivered_at')
    list_filter  = ('status', 'carrier')
    search_fields = ('tracking_number', 'sales_order__order_number', 'recipient_name')
    inlines = [ShipmentEventInline]


# ─────────────────────────────────────────────
#  MODULE 7 — CRM
# ─────────────────────────────────────────────

@admin.register(CustomerTag)
class CustomerTagAdmin(admin.ModelAdmin):
    list_display = ('name', 'color')


@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    list_display  = ('name', 'phone', 'source', 'total_orders', 'total_spent', 'last_order_at', 'is_blocked')
    list_filter   = ('source', 'is_blocked', 'tags')
    search_fields = ('name', 'phone', 'email')
    inlines = [CustomerNoteInline]
    readonly_fields = ('total_orders', 'total_spent', 'avg_order_value', 'last_order_at')


@admin.register(CustomerSegment)
class CustomerSegmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'last_refreshed_at', 'created_at')


# ─────────────────────────────────────────────
#  MODULE 8 — REPORTS
# ─────────────────────────────────────────────

@admin.register(ReportSnapshot)
class ReportSnapshotAdmin(admin.ModelAdmin):
    list_display = ('report_type', 'period_start', 'period_end', 'generated_at')
    list_filter  = ('report_type',)
    readonly_fields = ('generated_at',)


# ─────────────────────────────────────────────
#  MODULE 9 — HR
# ─────────────────────────────────────────────

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'manager')


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('user', 'job_title', 'department', 'employment_type', 'salary', 'hire_date', 'is_active')
    list_filter  = ('department', 'employment_type', 'is_active')
    search_fields = ('user__email', 'user__first_name', 'user__last_name', 'job_title')


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('employee', 'date', 'check_in', 'check_out', 'status', 'hours_worked')
    list_filter  = ('status',)
    date_hierarchy = 'date'


@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = ('employee', 'type', 'start_date', 'end_date', 'days_count', 'status')
    list_filter  = ('type', 'status')


@admin.register(SalesTarget)
class SalesTargetAdmin(admin.ModelAdmin):
    list_display = ('employee', 'period_start', 'period_end', 'target_amount', 'achievement_percentage')
    readonly_fields = ('achieved_amount', 'achievement_percentage')