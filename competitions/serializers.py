from rest_framework import serializers
from accounts.serializers import ProfileSerializer
from .models import CompetitionMessage
from .models import MatchMessage
from .models import (
    Competition,
    CompetitionParticipant,
    Match,
    Standing,
    MatchDispute,
    Challenge,
    WorldChatMessage
)


# =========================
# COMPETITION LIST SERIALIZER
# =========================
class CompetitionSerializer(serializers.ModelSerializer):
    participant_count = serializers.SerializerMethodField()
    is_joined = serializers.SerializerMethodField()

    class Meta:
        model = Competition
        fields = [
            "id",
            "title",
            "game",
            "format",
            "rules",
            "max_players",
            "start_date",
            "registration_deadline",
            "status",
            "region",
            "tournament_code",
            "created_at",
            "participant_count",
            "is_joined",
        ]

    def get_participant_count(self, obj):
        return obj.participants.filter(status="approved").count()

    def get_is_joined(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False

        return obj.participants.filter(
            player=request.user.profile,
            status="approved",
        ).exists()


# =========================
# CREATE COMPETITION
# =========================
class CompetitionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Competition
        fields = [
            "id",
            "title",
            "game",
            "format",
            "rules",
            "max_players",
            "start_date",
            "registration_deadline",
            "status",
            "region",
        ]


# =========================
# PARTICIPANTS
# =========================
class CompetitionParticipantSerializer(serializers.ModelSerializer):
    player = ProfileSerializer(read_only=True)

    class Meta:
        model = CompetitionParticipant
        fields = [
            "id",
            "competition",
            "player",
            "status",
            "joined_at",
        ]


# =========================
# MATCHES
# =========================
class MatchSerializer(serializers.ModelSerializer):
    player1 = ProfileSerializer(read_only=True)
    player2 = ProfileSerializer(read_only=True)
    winner = ProfileSerializer(read_only=True)
    submitted_by = ProfileSerializer(read_only=True)
    approved_by = ProfileSerializer(read_only=True)
    open_dispute_count = serializers.SerializerMethodField()

    class Meta:
        model = Match
        fields = [
            "id",
            "competition",
            "round_number",
            "player1",
            "player2",
            "player1_score",
            "player2_score",
            "winner",
            "scheduled_at",
            "status",
            "proof_image",
            "notes",
            "submitted_by",
            "approved_by",
            "approved_at",
            "open_dispute_count",
        ]

    def get_open_dispute_count(self, obj):
        return obj.disputes.filter(status="open").count()


class MatchResultSubmitSerializer(serializers.ModelSerializer):
    class Meta:
        model = Match
        fields = [
            "player1_score",
            "player2_score",
            "proof_image",
            "notes",
        ]


class MatchApprovalSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["approve", "reject"])
    notes = serializers.CharField(required=False, allow_blank=True)


# =========================
# DISPUTES
# =========================
class MatchDisputeCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = MatchDispute
        fields = ["reason"]


class MatchDisputeSerializer(serializers.ModelSerializer):
    raised_by = ProfileSerializer(read_only=True)
    resolved_by = ProfileSerializer(read_only=True)

    class Meta:
        model = MatchDispute
        fields = [
            "id",
            "match",
            "raised_by",
            "reason",
            "status",
            "resolution_notes",
            "resolved_by",
            "created_at",
            "resolved_at",
        ]


class DisputeResolveSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["resolved", "dismissed"])
    resolution_notes = serializers.CharField(required=False, allow_blank=True)
    player1_score = serializers.IntegerField(required=False, min_value=0)
    player2_score = serializers.IntegerField(required=False, min_value=0)

    def validate(self, attrs):
        if attrs.get("action") == "resolved":
            if "player1_score" not in attrs or "player2_score" not in attrs:
                raise serializers.ValidationError(
                    "Scores required when resolving dispute."
                )
        return attrs


# =========================
# STANDINGS
# =========================
class StandingSerializer(serializers.ModelSerializer):
    player = ProfileSerializer(read_only=True)

    class Meta:
        model = Standing
        fields = [
            "id",
            "competition",
            "player",
            "played",
            "wins",
            "draws",
            "losses",
            "goals_for",
            "goals_against",
            "goal_difference",
            "points",
        ]


# =========================
# CHALLENGES
# =========================
class ChallengeSerializer(serializers.ModelSerializer):
    challenger = ProfileSerializer(read_only=True)
    opponent = ProfileSerializer(read_only=True)
    winner = ProfileSerializer(read_only=True)

    class Meta:
        model = Challenge
        fields = "__all__"


# ✅ FIXED — this was missing
class ChallengeCreateSerializer(serializers.Serializer):
    game = serializers.CharField(max_length=100, default="eFootball")
    message = serializers.CharField(required=False, allow_blank=True)
    scheduled_at = serializers.DateTimeField(required=False, allow_null=True)


class ChallengeResultSubmitSerializer(serializers.Serializer):
    challenger_score = serializers.IntegerField(min_value=0)
    opponent_score = serializers.IntegerField(min_value=0)

    def validate(self, attrs):
        if attrs["challenger_score"] == attrs["opponent_score"]:
            raise serializers.ValidationError("No draws allowed.")
        return attrs


# =========================
# ✅ FIXED DETAILS SERIALIZER
# =========================
class CompetitionDetailSerializer(serializers.ModelSerializer):
    host = ProfileSerializer(read_only=True)
    matches = MatchSerializer(many=True, read_only=True)
    participants = CompetitionParticipantSerializer(many=True, read_only=True)

    participant_count = serializers.SerializerMethodField()
    is_joined = serializers.SerializerMethodField()

    class Meta:
        model = Competition
        fields = [
            "id",
            "title",
            "game",
            "host",
            "format",
            "rules",
            "max_players",
            "start_date",
            "registration_deadline",
            "status",
            "region",
            "tournament_code",
            "participants",
            "matches",
            "participant_count",
            "is_joined",
            "created_at",
        ]

    def get_participant_count(self, obj):
        return obj.participants.filter(status="approved").count()

    def get_is_joined(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False

        return obj.participants.filter(
            player=request.user.profile,
            status="approved",
        ).exists()


# =========================
# CHAT
# =========================
class WorldChatSerializer(serializers.ModelSerializer):
    user = ProfileSerializer(read_only=True)

    class Meta:
        model = WorldChatMessage
        fields = "__all__"


class MatchMessageSerializer(serializers.ModelSerializer):
    sender_username = serializers.CharField(source="sender.username", read_only=True)

    class Meta:
        model = MatchMessage
        fields = [
            "id",
            "match",
            "sender",
            "sender_username",
            "message",
            "created_at",
        ]


class CompetitionMessageSerializer(serializers.ModelSerializer):
    sender_username = serializers.CharField(source="sender.username", read_only=True)

    class Meta:
        model = CompetitionMessage
        fields = [
            "id",
            "competition",
            "sender",
            "sender_username",
            "message",
            "created_at",
        ]