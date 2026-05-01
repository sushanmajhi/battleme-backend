from django.contrib import admin
from .models import Competition, CompetitionParticipant, Match, Standing, MatchDispute, Challenge


@admin.register(Competition)
class CompetitionAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "game", "host", "status", "format", "max_players", "created_at")
    list_filter = ("status", "format", "game")
    search_fields = ("title", "game", "host__user__username")
    actions = ["mark_open", "mark_live", "mark_completed"]

    def mark_open(self, request, queryset):
        queryset.update(status="open")

    def mark_live(self, request, queryset):
        queryset.update(status="live")

    def mark_completed(self, request, queryset):
        queryset.update(status="completed")


@admin.register(CompetitionParticipant)
class CompetitionParticipantAdmin(admin.ModelAdmin):
    list_display = ("id", "competition", "player", "status", "joined_at")
    list_filter = ("status",)
    search_fields = ("competition__title", "player__user__username")
    actions = ["approve_players", "reject_players"]

    def approve_players(self, request, queryset):
        queryset.update(status="approved")

    def reject_players(self, request, queryset):
        queryset.update(status="rejected")


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = ("id", "competition", "round_number", "player1", "player2", "winner", "status")
    list_filter = ("status", "round_number")
    search_fields = ("competition__title", "player1__user__username", "player2__user__username")
    actions = ["approve_matches", "reject_matches", "mark_disputed"]

    def approve_matches(self, request, queryset):
        queryset.update(status="completed")

    def reject_matches(self, request, queryset):
        queryset.update(status="rejected")

    def mark_disputed(self, request, queryset):
        queryset.update(status="disputed")


@admin.register(MatchDispute)
class MatchDisputeAdmin(admin.ModelAdmin):
    list_display = ("id", "match", "raised_by", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("reason", "raised_by__user__username")
    actions = ["resolve_disputes", "dismiss_disputes"]

    def resolve_disputes(self, request, queryset):
        queryset.update(status="resolved")

    def dismiss_disputes(self, request, queryset):
        queryset.update(status="dismissed")


@admin.register(Standing)
class StandingAdmin(admin.ModelAdmin):
    list_display = ("competition", "player", "played", "wins", "losses", "points")


@admin.register(Challenge)
class ChallengeAdmin(admin.ModelAdmin):
    list_display = ("id", "challenger", "opponent", "status", "winner", "created_at")
    list_filter = ("status",)
    search_fields = ("challenger__user__username", "opponent__user__username")