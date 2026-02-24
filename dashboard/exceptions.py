# exceptions.py
# ضيف الملف ده في apps/dashboard/exceptions.py

from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status


def custom_exception_handler(exc, context):
    """
    Wraps all DRF errors in our standard response envelope:
    { "success": false, "message": "...", "errors": { ... } }
    """
    response = exception_handler(exc, context)

    if response is not None:
        error_data = response.data

        # استخرج message مناسبة
        if isinstance(error_data, dict):
            message = error_data.pop('detail', 'An error occurred.')
            if hasattr(message, 'code'):
                message = str(message)
        elif isinstance(error_data, list):
            message = error_data[0] if error_data else 'An error occurred.'
            error_data = {}
        else:
            message = str(error_data)
            error_data = {}

        response.data = {
            'success': False,
            'message': str(message),
            'errors':  error_data if error_data else None,
        }

    return response