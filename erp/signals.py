from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone


# ─────────────────────────────────────────────
#  1. خصم المخزون عند إنشاء SalesOrderItem
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

    # ✅ بعد كل item يتضاف، احسب الـ total من جديد وحدّث الـ Revenue
    _recalc_and_sync_revenue(instance.sales_order)


# ─────────────────────────────────────────────
#  2. إنشاء/تحديث Revenue لما الأوردر يتأكد
#     أو لما الـ total يتغير
# ─────────────────────────────────────────────
@receiver(post_save, sender='erp.SalesOrder')
def create_revenue_on_confirmed(sender, instance, **kwargs):
    from erp.models import Revenue

    if instance.status == 'confirmed':
        # ✅ اجلب الـ total من الـ DB مش من الـ instance
        # عشان ممكن يكون stale في وقت الـ signal
        from erp.models import SalesOrder
        fresh_total = SalesOrder.objects.filter(pk=instance.pk).values_list('total', flat=True).first()
        
        Revenue.objects.update_or_create(
            sales_order=instance,
            defaults={
                'source': Revenue.Source.SALE,
                'amount': fresh_total or instance.total,
                'date': instance.created_at.date(),
                'description': f"Sale: {instance.order_number}",
            }
        )

    if instance.customer:
        try:
            instance.customer.update_stats()
        except Exception:
            pass

# ─────────────────────────────────────────────
#  Helper: احسب totals من الـ items وحدّث الـ Revenue
#  بيتاستدعى بعد كل SalesOrderItem يتضاف
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

    # ✅ لو الأوردر confirmed، update_or_create مش بس update
    if order.status == 'confirmed':
        Revenue.objects.update_or_create(
            sales_order=order,
            defaults={
                'source': Revenue.Source.SALE,
                'amount': total,
                'date': order.created_at.date(),
                'description': f"Sale: {order.order_number}",
            }
        )
    else:
        # لو مش confirmed، حدّث اللي موجود بس
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
            source=Revenue.Source.OTHER,
            amount=-instance.refund_amount,
            date=timezone.now().date(),
            description=f"Refund for Return #{instance.pk}",
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
            title=f"{'Out of Stock' if current_stock == 0 else 'Low Stock'}: {variant.product.name}",
            message=f"Variant: {variant} | Remaining: {current_stock} units",
            link=f"/erp/inventory/{variant.pk}/",
        )

        alert.last_triggered_at = timezone.now()
        alert.save(update_fields=['last_triggered_at'])

from django.db.models.signals import post_save, post_delete

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
#     عند إنشاء/تعديل/حذف Revenue أو Expense
# ─────────────────────────────────────────────
from django.db.models.signals import post_save, post_delete
from django.db.models import Sum

def _recalc_financial_summary(date):
    """
    يحسب FinancialSummary ليوم معين من Revenue و Expense الحالية في الـ DB.
    """
    from erp.models import Revenue, Expense, SalesOrder, FinancialSummary
    from decimal import Decimal

    # إجمالي الإيرادات في اليوم ده
    total_revenue = Revenue.objects.filter(date=date).aggregate(
        total=Sum('amount')
    )['total'] or Decimal('0')

    # إجمالي المصروفات في اليوم ده
    total_expenses = Expense.objects.filter(date=date).aggregate(
        total=Sum('amount')
    )['total'] or Decimal('0')

    # عدد الأوردرات المؤكدة في اليوم ده
    orders_count = SalesOrder.objects.filter(
        created_at__date=date,
        status='confirmed'
    ).count()

    # المرتجعات في اليوم ده
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