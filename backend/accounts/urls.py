from django.urls import path

from accounts import views

urlpatterns = [
    path("csrf", views.CsrfView.as_view(), name="auth-csrf"),
    path("register", views.RegisterView.as_view(), name="auth-register"),
    path("login", views.LoginView.as_view(), name="auth-login"),
    path("logout", views.LogoutView.as_view(), name="auth-logout"),
    path("me", views.MeView.as_view(), name="auth-me"),
    path("change-password", views.ChangePasswordView.as_view(), name="auth-change-password"),
]
