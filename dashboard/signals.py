from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

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


@receiver(post_save, sender='dashboard.Order')
def deduct_warehouse_stock_on_confirm(sender, instance, **kwargs):
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