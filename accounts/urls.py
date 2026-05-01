from django.urls import path
from .views import (
    RegisterView,
    ProfileListView,
    ProfileDetailView,
    HealthView,
    MeView,
    LeaderboardView,
    VerifyEmailView,
    ResendVerificationCodeView,
)

urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    path("register/", RegisterView.as_view(), name="register"),
    path("profiles/", ProfileListView.as_view(), name="profiles"),
    path("leaderboard/", LeaderboardView.as_view(), name="leaderboard"),
    path("profiles/<int:pk>/", ProfileDetailView.as_view(), name="profile-detail"),
    path("me/", MeView.as_view(), name="me"),
    path("verify-email/", VerifyEmailView.as_view(), name="verify-email"),
    path("resend-code/", ResendVerificationCodeView.as_view(), name="resend-code"),
]