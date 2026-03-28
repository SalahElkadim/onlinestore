"""
============================================================
  ERP APPLICATION — signals.py
  التعديلات:
  - إزالة الخصم من variant.stock في OrderCreateSerializer
    (ده بيحصل في dashboard/serializers.py — شوف التعليق هناك)
  - مصدر واحد للحقيقة: WarehouseStock فقط
============================================================
"""

from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.utils import timezone


# ─────────────────────────────────────────────
#  1. خصم المخزون عند إنشاء SalesOrderItem
#     (أوردرات الـ ERP الداخلية — مش Online Orders)
# ─────────────────────────────────────────────
@receiver(post_save, sender='erp.SalesOrderItem')
def deduct_stock_on_sale(sender, instance, created, **kwargs):
    if not created:
        return

    from erp.models import Warehouse, WarehouseStock, StockMovement
    from dashboard.models import Notification

    variant = instance.variant
    if not variant:
        return

    warehouse = Warehouse.objects.filter(is_default=True).first()
    if not warehouse:
        warehouse = Warehouse.objects.filter(is_active=True).first()
    if not warehouse:
        return

    ws, _ = WarehouseStock.objects.get_or_create(
        warehouse=warehouse,
        variant=variant,
        defaults={'quantity': 0}
    )

    stock_before = ws.quantity
    ws.quantity = max(0, ws.quantity - instance.quantity)
    ws.save()

    StockMovement.objects.create(
        variant=variant,
        warehouse=warehouse,
        type=StockMovement.Type.OUT,
        quantity=-instance.quantity,
        stock_before=stock_before,
        stock_after=ws.quantity,
        sales_order=instance.sales_order,
        reason=f"Sale: {instance.sales_order.order_number}",
    )

    _check_stock_alert(variant, ws.quantity)
    _recalc_and_sync_revenue(instance.sales_order)


# ─────────────────────────────────────────────
#  2. إنشاء/تحديث Revenue لأي status
# ─────────────────────────────────────────────
@receiver(post_save, sender='erp.SalesOrder')
def sync_revenue_on_order_save(sender, instance, **kwargs):
    from erp.models import Revenue

    REVENUE_STATUSES = {'confirmed', 'processing', 'shipped', 'delivered'}
    NO_REVENUE_STATUSES = {'cancelled', 'returned', 'draft'}

    if instance.status in NO_REVENUE_STATUSES:
        Revenue.objects.filter(sales_order=instance).delete()
        return

    if instance.status in REVENUE_STATUSES:
        from erp.models import SalesOrder
        fresh_total = SalesOrder.objects.filter(
            pk=instance.pk
        ).values_list('total', flat=True).first()

        Revenue.objects.update_or_create(
            sales_order=instance,
            defaults={
                'source': 'sale',
                'amount': fresh_total or instance.total,
                'date': instance.created_at.date() if instance.created_at else timezone.now().date(),
                'description': f"بيع: {instance.order_number} — {instance.customer_name}",
                'currency': 'EGP',
            }
        )

    if instance.customer:
        try:
            instance.customer.update_stats()
        except Exception:
            pass


# ─────────────────────────────────────────────
#  Helper: احسب totals من الـ items وحدّث Revenue
# ─────────────────────────────────────────────
def _recalc_and_sync_revenue(order):
    from erp.models import Revenue
    from decimal import Decimal

    subtotal = sum(item.total_price for item in order.items.all())
    total = (
        Decimal(str(subtotal))
        - Decimal(str(order.discount_amount or 0))
        + Decimal(str(order.tax_amount or 0))
        + Decimal(str(order.shipping_cost or 0))
    )

    type(order).objects.filter(pk=order.pk).update(
        subtotal=subtotal,
        total=total,
    )

    REVENUE_STATUSES = {'confirmed', 'processing', 'shipped', 'delivered'}

    if order.status in REVENUE_STATUSES:
        Revenue.objects.update_or_create(
            sales_order=order,
            defaults={
                'source': 'sale',
                'amount': total,
                'date': order.created_at.date() if order.created_at else timezone.now().date(),
                'description': f"بيع: {order.order_number} — {order.customer_name}",
                'currency': 'EGP',
            }
        )
    else:
        Revenue.objects.filter(
            sales_order=order,
            source='sale',
        ).update(amount=total)


# ─────────────────────────────────────────────
#  3. رفع المخزون عند استلام بضاعة من المورد
# ─────────────────────────────────────────────
@receiver(post_save, sender='erp.GoodsReceipt')
def increase_stock_on_goods_receipt(sender, instance, created, **kwargs):
    if not created:
        return

    from erp.models import WarehouseStock, StockMovement

    warehouse = instance.warehouse
    purchase_order = instance.purchase_order

    for item in purchase_order.items.all():
        if not item.variant:
            continue

        ws, _ = WarehouseStock.objects.get_or_create(
            warehouse=warehouse,
            variant=item.variant,
            defaults={'quantity': 0}
        )

        stock_before = ws.quantity
        ws.quantity += item.quantity_ordered
        ws.save()

        StockMovement.objects.create(
            variant=item.variant,
            warehouse=warehouse,
            type=StockMovement.Type.IN,
            quantity=item.quantity_ordered,
            stock_before=stock_before,
            stock_after=ws.quantity,
            purchase_order=purchase_order,
            reason=f"Goods Receipt: {purchase_order.po_number}",
            created_by=instance.received_by,
        )

        item.quantity_received = item.quantity_ordered
        item.save(update_fields=['quantity_received'])

    all_received = all(i.is_fully_received for i in purchase_order.items.all())
    purchase_order.status = 'received' if all_received else 'partial'
    purchase_order.save(update_fields=['status'])


# ─────────────────────────────────────────────
#  4. إرجاع المخزون عند اكتمال المرتجع
# ─────────────────────────────────────────────
@receiver(post_save, sender='erp.ReturnRequest')
def restock_on_return_completed(sender, instance, **kwargs):
    if instance.status != 'completed':
        return

    from erp.models import Warehouse, WarehouseStock, StockMovement, Revenue

    warehouse = Warehouse.objects.filter(is_default=True).first()

    for return_item in instance.items.all():
        if not return_item.should_restock or not return_item.variant:
            continue

        ws, _ = WarehouseStock.objects.get_or_create(
            warehouse=warehouse,
            variant=return_item.variant,
            defaults={'quantity': 0}
        )

        stock_before = ws.quantity
        ws.quantity += return_item.quantity
        ws.save()

        StockMovement.objects.create(
            variant=return_item.variant,
            warehouse=warehouse,
            type=StockMovement.Type.RETURN,
            quantity=return_item.quantity,
            stock_before=stock_before,
            stock_after=ws.quantity,
            return_request=instance,
            reason=f"Return #{instance.pk}",
            created_by=instance.handled_by,
        )

    if instance.refund_amount > 0:
        Revenue.objects.create(
            source='other',
            amount=-instance.refund_amount,
            date=timezone.now().date(),
            description=f"استرداد للمرتجع #{instance.pk}",
        )


# ─────────────────────────────────────────────
#  5. Helper: تحقق من StockAlert
# ─────────────────────────────────────────────
def _check_stock_alert(variant, current_stock):
    from erp.models import StockAlert
    from dashboard.models import Notification

    try:
        alert = variant.stock_alert
    except Exception:
        return

    if not alert.is_active:
        return

    if current_stock <= alert.threshold:
        if alert.last_triggered_at:
            diff = timezone.now() - alert.last_triggered_at
            if diff.seconds < 3600:
                return

        ntype = (
            Notification.Type.OUT_OF_STOCK
            if current_stock == 0
            else Notification.Type.LOW_STOCK
        )

        Notification.objects.create(
            type=ntype,
            title=f"{'نفد المخزون' if current_stock == 0 else 'مخزون منخفض'}: {variant.product.name}",
            message=f"المتغير: {variant} | المتبقي: {current_stock} وحدة",
            link=f"/erp/inventory/{variant.pk}/",
        )

        alert.last_triggered_at = timezone.now()
        alert.save(update_fields=['last_triggered_at'])


# ─────────────────────────────────────────────
#  6. إعادة حساب total للـ PurchaseOrder
# ─────────────────────────────────────────────
@receiver(post_save, sender='erp.PurchaseOrderItem')
@receiver(post_delete, sender='erp.PurchaseOrderItem')
def recalc_purchase_order_total(sender, instance, **kwargs):
    po = instance.purchase_order
    total = sum(
        item.unit_cost * item.quantity_ordered
        for item in po.items.all()
    )
    type(po).objects.filter(pk=po.pk).update(total_cost=total)


# ─────────────────────────────────────────────
#  7. تحديث FinancialSummary تلقائياً
# ─────────────────────────────────────────────
from django.db.models import Sum


def _recalc_financial_summary(date):
    from erp.models import Revenue, Expense, SalesOrder, FinancialSummary
    from decimal import Decimal

    total_revenue = Revenue.objects.filter(date=date).aggregate(
        total=Sum('amount')
    )['total'] or Decimal('0')

    total_expenses = Expense.objects.filter(date=date).aggregate(
        total=Sum('amount')
    )['total'] or Decimal('0')

    orders_count = SalesOrder.objects.filter(
        created_at__date=date,
        status__in=['confirmed', 'processing', 'shipped', 'delivered']
    ).count()

    from erp.models import ReturnRequest
    returned_amount = ReturnRequest.objects.filter(
        created_at__date=date,
        status='completed'
    ).aggregate(total=Sum('refund_amount'))['total'] or Decimal('0')

    net_profit = total_revenue - total_expenses

    FinancialSummary.objects.update_or_create(
        date=date,
        defaults={
            'total_revenue': total_revenue,
            'total_expenses': total_expenses,
            'net_profit': net_profit,
            'orders_count': orders_count,
            'returned_amount': returned_amount,
        }
    )


@receiver(post_save, sender='erp.Revenue')
@receiver(post_delete, sender='erp.Revenue')
def update_summary_on_revenue(sender, instance, **kwargs):
    _recalc_financial_summary(instance.date)


@receiver(post_save, sender='erp.Expense')
@receiver(post_delete, sender='erp.Expense')
def update_summary_on_expense(sender, instance, **kwargs):
    _recalc_financial_summary(instance.date)