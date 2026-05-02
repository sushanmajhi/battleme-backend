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
        action = attrs.get("action")
        if action == "resolved":
            if "player1_score" not in attrs or "player2_score" not in attrs:
                raise serializers.ValidationError(
                    "player1_score and player2_score are required when resolving a dispute."
                )
        return attrs


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


class ChallengeSerializer(serializers.ModelSerializer):
    challenger = ProfileSerializer(read_only=True)
    opponent = ProfileSerializer(read_only=True)
    winner = ProfileSerializer(read_only=True)
    is_mine = serializers.SerializerMethodField()
    can_accept = serializers.SerializerMethodField()
    can_cancel = serializers.SerializerMethodField()
    can_submit_result = serializers.SerializerMethodField()

    class Meta:
        model = Challenge
        fields = [
            "id",
            "challenger",
            "opponent",
            "game",
            "message",
            "scheduled_at",
            "status",
            "challenger_score",
            "opponent_score",
            "winner",
            "is_mine",
            "can_accept",
            "can_cancel",
            "can_submit_result",
            "created_at",
            "updated_at",
        ]

    def get_profile(self):
        request = self.context.get("request")
        if request and request.user and request.user.is_authenticated:
            return getattr(request.user, "profile", None)
        return None

    def get_is_mine(self, obj):
        profile = self.get_profile()
        return bool(profile and obj.challenger_id == profile.id)

    def get_can_accept(self, obj):
        profile = self.get_profile()
        if not profile:
            return False
        return obj.status == "open" and obj.challenger_id != profile.id

    def get_can_cancel(self, obj):
        profile = self.get_profile()
        if not profile:
            return False
        return obj.status == "open" and obj.challenger_id == profile.id

    def get_can_submit_result(self, obj):
        profile = self.get_profile()
        if not profile or not obj.opponent_id:
            return False
        return obj.status == "accepted" and profile.id in [obj.challenger_id, obj.opponent_id]


class CompetitionDetailSerializer(serializers.ModelSerializer):
    host = ProfileSerializer(read_only=True)
    matches = MatchSerializer(many=True, read_only=True)
    participants = CompetitionParticipantSerializer(many=True, read_only=True)

    # ✅ FIX ADDED
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
            "participant_count",   # ✅ ADDED
            "is_joined",           # ✅ ADDED
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


class WorldChatSerializer(serializers.ModelSerializer):
    user = ProfileSerializer(read_only=True)
    competition_detail = CompetitionSerializer(source="competition", read_only=True)
    challenge_detail = ChallengeSerializer(source="challenge", read_only=True)

    class Meta:
        model = WorldChatMessage
        fields = [
            "id",
            "user",
            "content",
            "message_type",
            "competition",
            "competition_detail",
            "challenge",
            "challenge_detail",
            "created_at",
        ]


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
        read_only_fields = ["match", "sender", "created_at"]


class CompetitionMessageSerializer(serializers.ModelSerializer):
    sender_username = serializers.CharField(source="sender.username", read_only=True)

    class Meta:
        model = CompetitionMessage
        fields = ["id", "competition", "sender", "sender_username", "message", "created_at"]
        read_only_fields = ["competition", "sender", "created_at"]