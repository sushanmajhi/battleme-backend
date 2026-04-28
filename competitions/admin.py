from django.contrib import admin
from .models import Competition, CompetitionParticipant, Match, Standing


@admin.register(Competition)
class CompetitionAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "game", "format", "status", "max_players", "start_date")
    search_fields = ("title", "game")
    list_filter = ("format", "status", "game")


@admin.register(CompetitionParticipant)
class CompetitionParticipantAdmin(admin.ModelAdmin):
    list_display = ("id", "competition", "player", "status", "joined_at")
    search_fields = ("competition__title", "player__username")
    list_filter = ("status",)


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = ("id", "competition", "round_number", "player1", "player2", "winner", "status")
    list_filter = ("status", "competition")
    search_fields = ("competition__title", "player1__username", "player2__username")


@admin.register(Standing)
class StandingAdmin(admin.ModelAdmin):
    list_display = ("id", "competition", "player", "played", "wins", "draws", "losses", "points")
    search_fields = ("competition__title", "player__username")