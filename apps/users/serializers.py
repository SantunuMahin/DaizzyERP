"""
DRF Serializers for User model.
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model

User = get_user_model()


class UserSummarySerializer(serializers.ModelSerializer):
    """Compact user representation for embedded references."""
    full_name = serializers.CharField(source='get_full_name', read_only=True)

    class Meta:
        model = User
        fields = ('id', 'username', 'full_name', 'role')


class UserSerializer(serializers.ModelSerializer):
    """Detailed user representation for admin endpoints."""
    full_name = serializers.CharField(source='get_full_name', read_only=True)

    class Meta:
        model = User
        fields = (
            'id', 'username', 'email', 'first_name', 'last_name',
            'full_name', 'role', 'phone_number', 'is_active',
            'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at')
