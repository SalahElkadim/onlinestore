from .models import ActivityLog, Notification


def get_client_ip(request):
    x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded:
        return x_forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def log_activity(request, action, model_name, instance=None):
    try:
        ActivityLog.objects.create(
            admin=request.user if request.user.is_authenticated else None,
            action=action,
            model_name=model_name,
            object_id=str(instance.pk) if instance else None,
            object_repr=str(instance) if instance else '',
            ip_address=get_client_ip(request),
        )
    except Exception:
        pass


def create_notification(notif_type, message, title=None, link=''):
    try:
        Notification.objects.create(
            type=notif_type,
            title=title or notif_type.replace('_', ' ').title(),
            message=message,
            link=link,
        )
    except Exception:
        pass