"""
============================================================
  DASHBOARD APPLICATION — signals.py
  
  التغيير الأساسي:
  - الخصم من WarehouseStock بيحصل هنا عند تحويل الأوردر لـ confirmed
  - مصدر واحد للحقيقة: WarehouseStock فقط
  - مفيش خصم من variant.stock هنا (اتشال من serializers.py)
============================================================
"""

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver


# ─────────────────────────────────────────────
#  1. احفظ الـ status القديم قبل الحفظ
# ─────────────────────────────────────────────
@receiver(pre_save, sender='dashboard.Order')
def track_order_status_before_save(sender, instance, **kwargs):
    """احفظ الـ status القديم قبل الحفظ."""
    if instance.pk:
        try:
            instance._old_status = sender.objects.get(pk=instance.pk).status
        except sender.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None


# ─────────────────────────────────────────────
#  2. خصم WarehouseStock عند تأكيد الأوردر
# ─────────────────────────────────────────────
@receiver(post_save, sender='dashboard.Order')
def deduct_warehouse_stock_on_confirm(sender, instance, **kwargs):
    """
    بيخصم من WarehouseStock فقط لما الأوردر يتحول لـ confirmed.
    ده المصدر الوحيد للحقيقة — مفيش خصم تاني في أي مكان تاني.
    """
    old_status = getattr(instance, '_old_status', None)

    # اشتغل بس لما الـ status اتغير لـ confirmed فعلاً
    if old_status == instance.status:
        return
    if instance.status != 'confirmed':
        return

    from erp.models import Warehouse, WarehouseStock, StockMovement

    warehouse = Warehouse.objects.filter(is_default=True).first()
    if not warehouse:
        return

    for item in instance.items.select_related('variant').all():
        variant = item.variant
        if not variant:
            continue

        ws, _ = WarehouseStock.objects.get_or_create(
            warehouse=warehouse,
            variant=variant,
            defaults={'quantity': 0}
        )

        stock_before = ws.quantity
        ws.quantity = max(0, ws.quantity - item.quantity)
        ws.save()

        StockMovement.objects.create(
            variant=variant,
            warehouse=warehouse,
            type=StockMovement.Type.OUT,
            quantity=-item.quantity,
            stock_before=stock_before,
            stock_after=ws.quantity,
            reason=f"Online Order: {instance.order_number}",
        )

        # تحقق من تنبيهات المخزون
        _check_stock_alert_dashboard(variant, ws.quantity)


# ─────────────────────────────────────────────
#  3. إرجاع المخزون لو الأوردر اتكنسل أو اترتجع
# ─────────────────────────────────────────────
@receiver(post_save, sender='dashboard.Order')
def restock_on_order_cancel_or_return(sender, instance, **kwargs):
    """
    لو الأوردر كان confirmed وبعدين اتكنسل أو اترتجع،
    نرجع المخزون لـ WarehouseStock.
    """
    old_status = getattr(instance, '_old_status', None)

    # لازم يكون كان confirmed قبل كدا
    if old_status != 'confirmed':
        return

    # ورجع بس لو اتكنسل أو اترتجع
    if instance.status not in ('cancelled', 'refunded'):
        return

    from erp.models import Warehouse, WarehouseStock, StockMovement

    warehouse = Warehouse.objects.filter(is_default=True).first()
    if not warehouse:
        return

    for item in instance.items.select_related('variant').all():
        variant = item.variant
        if not variant:
            continue

        ws, _ = WarehouseStock.objects.get_or_create(
            warehouse=warehouse,
            variant=variant,
            defaults={'quantity': 0}
        )

        stock_before = ws.quantity
        ws.quantity += item.quantity
        ws.save()

        StockMovement.objects.create(
            variant=variant,
            warehouse=warehouse,
            type=StockMovement.Type.RETURN,
            quantity=item.quantity,
            stock_before=stock_before,
            stock_after=ws.quantity,
            reason=f"Order Cancelled/Refunded: {instance.order_number}",
        )


# ─────────────────────────────────────────────
#  Helper: تحقق من StockAlert
# ─────────────────────────────────────────────
def _check_stock_alert_dashboard(variant, current_stock):
    from dashboard.models import Notification

    try:
        alert = variant.stock_alert
    except Exception:
        return

    if not alert.is_active:
        return

    from django.utils import timezone

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