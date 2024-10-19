from firebase_admin import messaging
from rest_framework.response import Response

class StandardResponseMixin:
    def success_response(self, message, data=None, status_code=200):
        return Response({
            "success": "True",
            "message": message,
            "data": data,
            "code": status_code
        }, status=status_code)

    def error_response(self, message, data=None, status_code=400):
        return Response({
            "success": "False",
            "message": message,
            "data": data,
            "code": status_code
        }, status=status_code)
    
    def send_push_notification(token, title, body):
        message = messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            token=token,
        )
        try:
            response = messaging.send(message)
            return {'status': 'success', 'response': response}
        except Exception as e:
            return {'status': 'error', 'error': str(e)}