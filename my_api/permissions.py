from rest_framework import permissions

class IsUser(permissions.BasePermission):
    """
    Permission for Users (Role 1)
    """
    message = "Only Users Can Perform This Action"
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'user'
class IsOfficial(permissions.BasePermission):
    """
    Permission for Officials (Role 2)
    """
    message = "Only Officals Can Perform This Action."
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'official'

class IsAdmin(permissions.BasePermission):
    """
    Permission for Admins (Role 3)
    """
    message = "Only Admins Can Perform This Action"
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'admin'

class IsVerified(permissions.BasePermission):
    """
    Permission for Verification
    """
    message = "Only Officals Can Perform This Action."
    def has_permission(self, request, view):
        return request.user.verified

