from django.contrib.auth.models import User
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import Profile


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "first_name", "last_name", "email"]


class ProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = Profile
        fields = [
            "id",
            "user",
            "username",
            "role",
            "avatar",
            "bio",
            "favorite_team",
            "country",
            "is_email_verified",
            "matches_played",
            "wins",
            "losses",
            "draws",
            "goals_scored",
            "goals_conceded",
            "xp",
            "level",
            "rank_tier",
            "created_at",
        ]


class RegisterSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    email = serializers.EmailField()
    username = serializers.CharField(max_length=50)
    password = serializers.CharField(write_only=True, min_length=6)
    role = serializers.ChoiceField(choices=["player", "host"], default="player")

    def validate_email(self, value):
        value = value.lower().strip()

        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already exists.")

        return value

    def validate_username(self, value):
        value = value.strip()

        if Profile.objects.filter(username=value).exists():
            raise serializers.ValidationError("Username already exists.")

        return value

    def create(self, validated_data):
        email = validated_data["email"].lower().strip()

        user = User.objects.create_user(
            username=email,
            email=email,
            password=validated_data["password"],
            first_name=validated_data.get("first_name", ""),
            last_name=validated_data.get("last_name", ""),
            is_active=True,
        )

        profile = Profile.objects.create(
            user=user,
            username=validated_data["username"].strip(),
            role=validated_data.get("role", "player"),
            is_email_verified=False,
        )

        return profile


class VerifyEmailSerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField(max_length=6, min_length=6)

    def validate_email(self, value):
        return value.lower().strip()


class ResendVerificationCodeSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        return value.lower().strip()


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    username_field = User.EMAIL_FIELD

    def validate(self, attrs):
        email = attrs.get("email")
        password = attrs.get("password")

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError("Invalid email or password.")

        if not user.check_password(password):
            raise serializers.ValidationError("Invalid email or password.")

        if not user.is_active:
            raise serializers.ValidationError("User account is disabled.")

        refresh = self.get_token(user)

        data = {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "user": {
                "id": user.id,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "profile_id": user.profile.id,
                "username": user.profile.username,
                "role": user.profile.role,
                "is_email_verified": user.profile.is_email_verified,
                "xp": user.profile.xp,
                "level": user.profile.level,
                "rank_tier": user.profile.rank_tier,
            },
        }

        return data