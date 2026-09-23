"""
User authentication and profile views.
"""
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView, UpdateView
from django.urls import reverse_lazy
from django.contrib import messages
from django.contrib.auth import get_user_model
from apps.core.mixins import RoleRequiredMixin
from apps.core.permissions import UserRole
from .forms import LoginForm, UserAdminCreationForm, UserProfileForm

User = get_user_model()


class UserLoginView(LoginView):
    """Staff authentication screen."""
    template_name = 'users/login.html'
    authentication_form = LoginForm
    redirect_authenticated_user = True

    def get_success_url(self):
        return reverse_lazy('dashboard')

    def form_invalid(self, form):
        messages.error(self.request, "Invalid username or password. Please try again.")
        return super().form_invalid(form)


class UserLogoutView(LogoutView):
    """Staff session termination."""
    next_page = reverse_lazy('users:login')

    def dispatch(self, request, *args, **kwargs):
        messages.info(request, "You have been logged out successfully.")
        return super().dispatch(request, *args, **kwargs)


class UserProfileView(LoginRequiredMixin, UpdateView):
    """Personal account profile view."""
    model = User
    form_class = UserProfileForm
    template_name = 'users/profile.html'
    success_url = reverse_lazy('users:profile')

    def get_object(self, queryset=None):
        return self.request.user

    def form_valid(self, form):
        messages.success(self.request, "Your profile has been updated.")
        return super().form_valid(form)


class UserListView(LoginRequiredMixin, RoleRequiredMixin, ListView):
    """System users administration list (Admin only)."""
    model = User
    template_name = 'users/list.html'
    context_object_name = 'users_list'
    paginate_by = 20
    allowed_roles = UserRole.ADMIN_TIER

    def get_queryset(self):
        qs = User.objects.all().order_by('-created_at')
        role_filter = self.request.GET.get('role')
        if role_filter:
            qs = qs.filter(role=role_filter)
        search_query = self.request.GET.get('q')
        if search_query:
            qs = qs.filter(username__icontains=search_query) | qs.filter(email__icontains=search_query)
        return qs


class UserCreateView(LoginRequiredMixin, RoleRequiredMixin, CreateView):
    """Create new staff / cashier account (Admin only)."""
    model = User
    form_class = UserAdminCreationForm
    template_name = 'users/create.html'
    success_url = reverse_lazy('users:list')
    allowed_roles = UserRole.ADMIN_TIER

    def form_valid(self, form):
        messages.success(self.request, f"User '{form.cleaned_data['username']}' created successfully.")
        return super().form_valid(form)
