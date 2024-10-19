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
    
    def send_push_notification(self, tokens, title, body):
        if not isinstance(tokens, list):
            tokens = [tokens]

        tokens = [str(token) for token in tokens]   
        message = messaging.MulticastMessage(
            notification=messaging.Notification(title=str(title)),
            tokens=tokens,
        )
        try:
            response = messaging.send_multicast(message)
            print(f"Notification Sent, Response is: {response}")
            return {
                'status': 'success',
                'success_count': response.success_count,
                'failure_count': response.failure_count,
                'responses': response.responses,
            }
        except Exception as e:
            print(f"Notification Not Sent, Exception is: {e}")
            return {'status': 'error', 'error': str(e)}
        
