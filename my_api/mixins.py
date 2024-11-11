from rest_framework.response import Response


class StandardResponseMixin:
    def success_response(self, message, data=None, status_code=200):
        return Response(
            {"success": "True", "message": message, "data": data, "code": status_code},
            status=status_code,
        )

    def error_response(self, message, data=None, status_code=400):
        return Response(
            {"success": "False", "message": message, "data": data, "code": status_code},
            status=status_code,
        )
