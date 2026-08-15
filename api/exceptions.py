from rest_framework.views import exception_handler
from rest_framework.exceptions import ValidationError, AuthenticationFailed, NotAuthenticated, PermissionDenied

def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        custom_data = {
            "success": False,
        }

        if isinstance(exc, ValidationError):
            custom_data["message"] = "Validation failed."
            custom_data["errors"] = response.data
        elif isinstance(exc, (AuthenticationFailed, NotAuthenticated)):
            custom_data["message"] = "Authentication credentials were not provided or are invalid."
        elif isinstance(exc, PermissionDenied):
            custom_data["message"] = "You do not have permission to perform this action."
        else:
            # Fallback for other DRF exceptions (like NotFound, etc.)
            custom_data["message"] = response.data.get("detail", "An error occurred.")
            if "detail" in response.data:
                del response.data["detail"]
            if response.data:
                custom_data["errors"] = response.data

        response.data = custom_data

    return response
