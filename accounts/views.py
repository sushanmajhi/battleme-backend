from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.conf import settings

from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import Profile
from .serializers import (
    ProfileSerializer,
    RegisterSerializer,
    CustomTokenObtainPairSerializer,
    VerifyEmailSerializer,
    ResendVerificationCodeSerializer,
)


def send_verification_email(profile):
    code = profile.generate_email_code()

    send_mail(
        subject="Your BattleMe verification code",
        message=f"Your BattleMe verification code is: {code}. This code expires in 10 minutes.",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[profile.user.email],
        fail_silently=False,
    )


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


class RegisterView(generics.GenericAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        profile = serializer.save()

        email_sent = False

        return Response(
            {
                "message": "Account created successfully.",
                "email_sent": email_sent,
                "email": profile.user.email,
                "user": ProfileSerializer(profile).data,
            },
            status=status.HTTP_201_CREATED,
        )


class VerifyEmailView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = VerifyEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        code = serializer.validated_data["code"]

        try:
            user = User.objects.select_related("profile").get(email=email)
        except User.DoesNotExist:
            return Response({"detail": "User not found."}, status=404)

        profile = user.profile

        if profile.is_email_verified:
            return Response({"message": "Email is already verified."})

        if not profile.is_email_code_valid(code):
            return Response({"detail": "Invalid or expired verification code."}, status=400)

        profile.is_email_verified = True
        profile.email_verification_code = None
        profile.email_code_created_at = None
        profile.save()

        return Response(
            {
                "message": "Email verified successfully. You can now log in.",
                "user": ProfileSerializer(profile).data,
            }
        )


class ResendVerificationCodeView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = ResendVerificationCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]

        try:
            user = User.objects.select_related("profile").get(email=email)
        except User.DoesNotExist:
            return Response({"detail": "User not found."}, status=404)

        profile = user.profile

        if profile.is_email_verified:
            return Response({"message": "Email is already verified."})

        email_sent = True

        try:
            send_verification_email(profile)
        except Exception as e:
            print("EMAIL ERROR:", e)
            email_sent = False

        return Response(
            {
                "message": "Verification code resend attempted.",
                "email_sent": email_sent,
            }
        )


class ProfileListView(generics.ListAPIView):
    queryset = Profile.objects.select_related("user").all().order_by("-created_at")
    serializer_class = ProfileSerializer
    permission_classes = [permissions.AllowAny]


class LeaderboardView(generics.ListAPIView):
    serializer_class = ProfileSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        return (
            Profile.objects.select_related("user")
            .all()
            .order_by("-xp", "-wins", "-goals_scored", "username")
        )


class ProfileDetailView(generics.RetrieveAPIView):
    queryset = Profile.objects.select_related("user").all()
    serializer_class = ProfileSerializer
    permission_classes = [permissions.AllowAny]


class MeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = ProfileSerializer(request.user.profile)
        return Response(serializer.data)


class HealthView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return Response({"status": "ok", "message": "BattleMe backend is running"})