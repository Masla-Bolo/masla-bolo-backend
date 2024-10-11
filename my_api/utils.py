from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status

def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is None:
        return Response({
            'success': 'False',
            'message': 'Something went wrong!',
            'error': str(exc),
            'status_code': status.HTTP_500_INTERNAL_SERVER_ERROR
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    

    if response.status_code == status.HTTP_400_BAD_REQUEST:
        return Response({
            'success': 'False',
            'message': 'Bad Request',
            'error': response.data,
            'status_code': status.HTTP_400_BAD_REQUEST
        })
    
    elif response.status_code == status.HTTP_401_UNAUTHORIZED:
        return Response({
            'success': 'False',
            'message': response.data["detail"],
            'error': response.data["messages"],
            'status_code': status.HTTP_400_BAD_REQUEST
        })

    elif response.status_code == status.HTTP_404_NOT_FOUND:
        return Response({
            'success': 'False',
            'message': 'Resource not found',
            'error': response.data,
            'status_code': status.HTTP_404_NOT_FOUND
        })

    elif response.status_code == status.HTTP_403_FORBIDDEN:
        return Response({
            'success': 'False',
            'message': 'Permission Denied',
            'error': response.data,
            'status_code': status.HTTP_403_FORBIDDEN
        })
    
    elif response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED:
        return Response({
            'success': 'False',
            'message': "MethodNotAllowed",
            'error': response.data["detail"],
            'status_code': status.HTTP_405_METHOD_NOT_ALLOWED
        })

    return response