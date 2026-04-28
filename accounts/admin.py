from django.contrib import admin
from .models import Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "username",
        "role",
        "country",
        "matches_played",
        "wins",
        "losses",
        "xp",
        "level",
        "rank_tier",
    )
    search_fields = ("username", "user__email", "country", "rank_tier")
    list_filter = ("role", "country", "rank_tier")

    fieldsets = (
        ("Basic Info", {
            "fields": ("user", "username", "role", "avatar", "bio", "favorite_team", "country")
        }),
        ("Match Stats", {
            "fields": (
                "matches_played",
                "wins",
                "losses",
                "draws",
                "goals_scored",
                "goals_conceded",
            )
        }),
        ("Ranking", {
            "fields": ("xp", "level", "rank_tier")
        }),
    )