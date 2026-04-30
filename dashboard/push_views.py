"""
dashboard/push_views.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Two endpoints to add to urls.py:

    path("push/register/",   push_views.RegisterPushDeviceView.as_view()),
    path("push/unregister/", push_views.UnregisterPushDeviceView.as_view()),
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .models import AdminPushDevice
from .permissions import IsAdminOrStaff


class RegisterPushDeviceView(APIView):
    """
    POST /api/admin/push/register/
    Body: { "player_id": "<onesignal-player-id>" }

    Called from the frontend immediately after the user allows notifications.
    Idempotent — safe to call on every login.
    """
    permission_classes = [IsAuthenticated, IsAdminOrStaff]

    def post(self, request):
        player_id = (request.data.get("player_id") or "").strip()
        if not player_id:
            return Response(
                {"success": False, "message": "player_id is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        device_info = request.META.get("HTTP_USER_AGENT", "")[:300]

        obj, created = AdminPushDevice.objects.update_or_create(
            player_id=player_id,
            defaults={
                "user": request.user,
                "device_info": device_info,
                "is_active": True,
            },
        )

        return Response(
            {
                "success": True,
                "message": "Device registered." if created else "Device updated.",
                "device_id": obj.pk,
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class UnregisterPushDeviceView(APIView):
    """
    POST /api/admin/push/unregister/
    Body: { "player_id": "<onesignal-player-id>" }

    Called when the admin explicitly disables notifications or logs out.
    """
    permission_classes = [IsAuthenticated, IsAdminOrStaff]

    def post(self, request):
        player_id = (request.data.get("player_id") or "").strip()
        if not player_id:
            return Response(
                {"success": False, "message": "player_id is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        deleted, _ = AdminPushDevice.objects.filter(
            player_id=player_id,
            user=request.user,
        ).delete()

        return Response(
            {"success": True, "message": f"Removed {deleted} device(s)."},
        )