"""
Authentication and user management forms.
"""
from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm as BaseUserCreationForm
from django.contrib.auth import get_user_model
from apps.core.permissions import UserRole

User = get_user_model()


class LoginForm(AuthenticationForm):
    """Custom login form with styling hooks."""
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Username or Email',
            'autofocus': True,
            'autocomplete': 'username',
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': '••••••••',
            'autocomplete': 'current-password',
        })
    )


class UserAdminCreationForm(BaseUserCreationForm):
    """Form to create a new user from web UI with role selection."""
    class Meta(BaseUserCreationForm.Meta):
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'role', 'phone_number')
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-input'}),
            'email': forms.EmailInput(attrs={'class': 'form-input'}),
            'first_name': forms.TextInput(attrs={'class': 'form-input'}),
            'last_name': forms.TextInput(attrs={'class': 'form-input'}),
            'role': forms.Select(attrs={'class': 'form-select'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-input'}),
        }


class UserProfileForm(forms.ModelForm):
    """Form for user to edit their profile details."""
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'phone_number')
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-input'}),
            'last_name': forms.TextInput(attrs={'class': 'form-input'}),
            'email': forms.EmailInput(attrs={'class': 'form-input'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-input'}),
        }
