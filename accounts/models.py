from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone
from datetime import timedelta
import random


def get_rank_tier_from_xp(xp):
    if xp >= 1200:
        return "Champion"
    if xp >= 800:
        return "Diamond"
    if xp >= 500:
        return "Platinum"
    if xp >= 250:
        return "Gold"
    if xp >= 100:
        return "Silver"
    return "Bronze"


def get_level_from_xp(xp):
    return (xp // 100) + 1


class Profile(models.Model):
    ROLE_CHOICES = [
        ("player", "Player"),
        ("host", "Host"),
        ("admin", "Admin"),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile"
    )

    username = models.CharField(max_length=50, unique=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="player")

    avatar = models.URLField(blank=True, null=True)
    bio = models.TextField(blank=True)
    favorite_team = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)

    # email verification
    is_email_verified = models.BooleanField(default=False)
    email_verification_code = models.CharField(max_length=6, blank=True, null=True)
    email_code_created_at = models.DateTimeField(blank=True, null=True)

    # online status tracking
    last_seen = models.DateTimeField(auto_now=True)

    # player stats
    matches_played = models.PositiveIntegerField(default=0)
    wins = models.PositiveIntegerField(default=0)
    losses = models.PositiveIntegerField(default=0)
    draws = models.PositiveIntegerField(default=0)
    goals_scored = models.PositiveIntegerField(default=0)
    goals_conceded = models.PositiveIntegerField(default=0)

    xp = models.PositiveIntegerField(default=0)
    level = models.PositiveIntegerField(default=1)
    rank_tier = models.CharField(max_length=30, default="Bronze")

    created_at = models.DateTimeField(auto_now_add=True)

    def refresh_rank_data(self):
        self.level = get_level_from_xp(self.xp)
        self.rank_tier = get_rank_tier_from_xp(self.xp)

    def generate_email_code(self):
        code = str(random.randint(100000, 999999))
        self.email_verification_code = code
        self.email_code_created_at = timezone.now()
        self.save()
        return code

    def is_email_code_valid(self, code):
        if not self.email_verification_code or not self.email_code_created_at:
            return False

        if self.email_verification_code != str(code):
            return False

        expiry_time = self.email_code_created_at + timedelta(minutes=10)
        return timezone.now() <= expiry_time

    @property
    def is_online(self):
        return self.last_seen >= timezone.now() - timedelta(minutes=2)

    def save(self, *args, **kwargs):
        self.refresh_rank_data()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.username