from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import Profile
from .serializers import (
    ProfileSerializer,
    RegisterSerializer,
    CustomTokenObtainPairSerializer,
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

        return Response(
            {
                "message": "Account created successfully.",
                "user": ProfileSerializer(profile).data,
            },
            status=status.HTTP_201_CREATED,
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