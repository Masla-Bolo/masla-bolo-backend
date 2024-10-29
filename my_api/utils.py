from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import ValidationError
from firebase_admin import messaging

def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    # Handle the case when no response is generated (500 errors)
    if response is None:
        return Response({
            'success': 'False',
            'message': 'Something went wrong!',
            'data': str(exc),
            'code': status.HTTP_500_INTERNAL_SERVER_ERROR
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    if response.status_code == status.HTTP_400_BAD_REQUEST:
        if isinstance(exc, ValidationError):
            error_message = ""
            if "email" in response.data or "username" in response.data:
                error_message = "Email or Username already exists or is invalid."
            else:
                error_message = "Bad Request. Check your input data."

            return Response({
                'success': 'False',
                'message': error_message,
                'data': response.data,
                'code': status.HTTP_400_BAD_REQUEST
            })

        return Response({
            'success': 'False',
            'message': 'Bad Request',
            'data': response.data,
            'code': status.HTTP_400_BAD_REQUEST
        })

    elif response.status_code == status.HTTP_401_UNAUTHORIZED:
        return Response({
            'success': 'False',
            'message': response.data.get("detail", "Unauthorized access"),
            'data': response.data,
            'code': status.HTTP_401_UNAUTHORIZED
        })

    elif response.status_code == status.HTTP_404_NOT_FOUND:
        return Response({
            'success': 'False',
            'message': 'Resource not found',
            'data': response.data,
            'code': status.HTTP_404_NOT_FOUND
        })

    elif response.status_code == status.HTTP_403_FORBIDDEN:
        return Response({
            'success': 'False',
            'message': 'Permission Denied',
            'data': response.data,
            'code': status.HTTP_403_FORBIDDEN
        })

    elif response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED:
        return Response({
            'success': 'False',
            'message': "Method Not Allowed",
            'data': response.data.get("detail", "Method not allowed"),
            'code': status.HTTP_405_METHOD_NOT_ALLOWED
        })

    return response



def send_push_notification(tokens, title, body):
        if not isinstance(tokens, list):
            tokens = [tokens]

        tokens = [str(token) for token in tokens]   
        message = messaging.MulticastMessage(
            notification=messaging.Notification(title=str(title), body=str(body)),
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