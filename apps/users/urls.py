"""
URLs for user authentication and management.
"""
from django.urls import path
from .views import (
    UserLoginView, UserLogoutView, UserProfileView,
    UserListView, UserCreateView
)

app_name = 'users'

urlpatterns = [
    path('login/', UserLoginView.as_view(), name='login'),
    path('logout/', UserLogoutView.as_view(), name='logout'),
    path('profile/', UserProfileView.as_view(), name='profile'),
    path('', UserListView.as_view(), name='list'),
    path('create/', UserCreateView.as_view(), name='create'),
]
