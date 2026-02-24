from rest_framework.permissions import BasePermission
from dashboard.models import User


class IsCustomer(BasePermission):
    """السماح فقط للـ Customers المسجلين."""
    message = "هذا المورد متاح للعملاء فقط."

    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.role == User.Role.CUSTOMER and
            not request.user.is_blocked
        )