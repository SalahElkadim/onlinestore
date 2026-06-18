"""
dashboard/utils.py  — updated version
Adds push notification alongside every DB notification.
"""
from .models import ActivityLog, Notification


def get_client_ip(request):
    x_forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded:
        return x_forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def log_activity(request, action, model_name, instance=None):
    """Create an ActivityLog entry."""
    try:
        ActivityLog.objects.create(
            admin=request.user if request.user.is_authenticated else None,
            action=action,
            model_name=model_name,
            object_id=str(instance.pk) if instance else None,
            object_repr=str(instance) if instance else "",
            ip_address=get_client_ip(request),
        )
    except Exception:
        pass  # never let logging crash the main flow


# ── URL helpers ────────────────────────────────────────────────
_NOTIF_LINKS = {
    "new_order":    "/orders/{id}/",
    "low_stock":    "/inventory/",
    "out_of_stock": "/inventory/",
    "payment":      "/payments/",
    "refund":       "/payments/",
    "new_user":     "/customers/",
    "system":       "/",
}


def create_notification(notif_type: str, message: str, title: str = None, link: str = "", push: bool = True):
    """
    1. Save a Notification record in the DB (visible in-app bell).
    2. Optionally send a OneSignal push to all admin devices (push=True by default).
    """
    resolved_title = title or notif_type.replace("_", " ").title()
    resolved_link  = link or _NOTIF_LINKS.get(notif_type, "/")

    # ── 1. In-app notification ──────────────────────────────────
    try:
        Notification.objects.create(
            type=notif_type,
            title=resolved_title,
            message=message,
            link=resolved_link,
        )
    except Exception:
        pass

    # ── 2. Push notification (fire-and-forget) ─────────────────
    if push:
        try:
            from .onesignal_service import push_to_admins
            push_to_admins(
                title=resolved_title,
                message=message,
                url=resolved_link,
                notif_type=notif_type,
            )
        except Exception:
            pass  # push failure must never break the main request


def get_price_for_quantity(product, quantity):
    # جيب أعلى tier مناسبة للكمية
    tier = product.price_tiers.filter(
        min_quantity__lte=quantity
    ).order_by('-min_quantity').first()

    if not tier:
        # مفيش tiers خالص → ارجع effective_price
        return product.effective_price

    # لو الـ tier هي الأولى (أقل min_quantity)
    lowest_tier = product.price_tiers.order_by('min_quantity').first()
    if tier == lowest_tier:
        # دايماً effective_price (بياخد الديسكونت في الاعتبار)
        return product.effective_price

    # tiers تانية → ارجع سعر الـ tier
    return tier.unit_price


def get_prices_for_items(items_data):
    """
    items_data: list of dicts فيها 'product' و 'quantity' (ممكن يكونوا variants مختلفة لنفس المنتج)
    
    بيجمع الكمية الإجمالية لكل product_id (مهما اختلف الـ variant)،
    وبيحسب سعر الوحدة المناسب حسب التيرة بناءً على هذا الإجمالي.
    
    Returns: {product_id: unit_price}
    """
    totals = {}
    products = {}
    for item in items_data:
        product = item['product']
        totals[product.id] = totals.get(product.id, 0) + item['quantity']
        products[product.id] = product

    return {
        pid: get_price_for_quantity(products[pid], total_qty)
        for pid, total_qty in totals.items()
    }