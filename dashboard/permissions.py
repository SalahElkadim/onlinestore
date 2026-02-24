# ============================================================
# permissions.py
# ============================================================
from rest_framework.permissions import BasePermission
from .models import User


class IsAdminOrStaff(BasePermission):
    """Allow access to admin and staff roles only."""
    message = 'Admin or staff access required.'

    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            not request.user.is_blocked and
            request.user.role in (User.Role.ADMIN, User.Role.STAFF)
        )


class IsAdminOnly(BasePermission):
    """Allow access to admin role only."""
    message = 'Admin access required.'

    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            not request.user.is_blocked and
            request.user.role == User.Role.ADMIN
        )


class HasModulePermission(BasePermission):
    """
    Checks if the staff user has permission for a specific module/action.
    Usage: set `required_permission = ('orders', 'edit')` on the view.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.role == User.Role.ADMIN:
            return True   # Admins bypass module-level checks
        module = getattr(view, 'required_module', None)
        action = getattr(view, 'required_action', None)
        if not module or not action:
            return True
        try:
            perms = request.user.staff_profile.admin_role.permissions
            return action in perms.get(module, [])
        except Exception:
            return False


# ============================================================
# utils.py
# ============================================================
from .models import ActivityLog, Notification


def get_client_ip(request):
    x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded:
        return x_forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def log_activity(request, action, model_name, instance=None):
    """Create an ActivityLog entry."""
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
        pass   # Never let logging crash the main flow


def create_notification(notif_type, message, title=None, link=''):
    """Helper to create a Notification record."""
    try:
        Notification.objects.create(
            type=notif_type,
            title=title or notif_type.replace('_', ' ').title(),
            message=message,
            link=link,
        )
    except Exception:
        pass