from rest_framework import serializers
from accounts.serializers import ProfileSerializer
from .models import (
    Competition,
    CompetitionParticipant,
    Match,
    Standing,
    MatchDispute,
    Challenge,
    WorldChatMessage,
    MatchMessage,
    CompetitionMessage,
    Notification,
)


class CompetitionSerializer(serializers.ModelSerializer):
    participant_count = serializers.SerializerMethodField()
    is_joined = serializers.SerializerMethodField()

    class Meta:
        model = Competition
        fields = "__all__"

    def get_participant_count(self, obj):
        return obj.participants.count()

    def get_is_joined(self, obj):
        request = self.context.get("request")
        profile = getattr(request.user, "profile", None) if request else None
        return bool(profile and obj.participants.filter(player=profile).exists())


class CompetitionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Competition
        fields = "__all__"


class CompetitionParticipantSerializer(serializers.ModelSerializer):
    player = ProfileSerializer(read_only=True)

    class Meta:
        model = CompetitionParticipant
        fields = "__all__"


class MatchSerializer(serializers.ModelSerializer):
    player1 = ProfileSerializer(read_only=True)
    player2 = ProfileSerializer(read_only=True)
    winner = ProfileSerializer(read_only=True)
    submitted_by = ProfileSerializer(read_only=True)
    approved_by = ProfileSerializer(read_only=True)
    open_dispute_count = serializers.SerializerMethodField()

    class Meta:
        model = Match
        fields = "__all__"

    def get_open_dispute_count(self, obj):
        return obj.disputes.filter(status="open").count()


class MatchResultSubmitSerializer(serializers.ModelSerializer):
    class Meta:
        model = Match
        fields = ["player1_score", "player2_score", "proof_image", "notes"]


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
        fields = "__all__"


class DisputeResolveSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["resolved", "dismissed"])
    resolution_notes = serializers.CharField(required=False, allow_blank=True)
    player1_score = serializers.IntegerField(required=False, min_value=0)
    player2_score = serializers.IntegerField(required=False, min_value=0)

    def validate(self, attrs):
        if attrs.get("action") == "resolved":
            if "player1_score" not in attrs or "player2_score" not in attrs:
                raise serializers.ValidationError(
                    "player1_score and player2_score are required when resolving a dispute."
                )
        return attrs


class StandingSerializer(serializers.ModelSerializer):
    player = ProfileSerializer(read_only=True)

    class Meta:
        model = Standing
        fields = "__all__"


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
        fields = "__all__"

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
        return bool(profile and obj.status == "open" and obj.challenger_id != profile.id)

    def get_can_cancel(self, obj):
        profile = self.get_profile()
        return bool(profile and obj.status == "open" and obj.challenger_id == profile.id)

    def get_can_submit_result(self, obj):
        profile = self.get_profile()
        return bool(
            profile
            and obj.opponent_id
            and obj.status == "accepted"
            and profile.id in [obj.challenger_id, obj.opponent_id]
        )


class ChallengeCreateSerializer(serializers.Serializer):
    game = serializers.CharField(max_length=100, default="eFootball")
    message = serializers.CharField(required=False, allow_blank=True)
    scheduled_at = serializers.DateTimeField(required=False, allow_null=True)


class ChallengeResultSubmitSerializer(serializers.Serializer):
    challenger_score = serializers.IntegerField(min_value=0)
    opponent_score = serializers.IntegerField(min_value=0)

    def validate(self, attrs):
        if attrs["challenger_score"] == attrs["opponent_score"]:
            raise serializers.ValidationError("Open challenges cannot end in a draw.")
        return attrs


class CompetitionDetailSerializer(serializers.ModelSerializer):
    host = ProfileSerializer(read_only=True)
    participants = CompetitionParticipantSerializer(many=True, read_only=True)
    matches = MatchSerializer(many=True, read_only=True)
    participant_count = serializers.SerializerMethodField()
    is_joined = serializers.SerializerMethodField()

    class Meta:
        model = Competition
        fields = "__all__"

    def get_participant_count(self, obj):
        return obj.participants.count()

    def get_is_joined(self, obj):
        request = self.context.get("request")
        profile = getattr(request.user, "profile", None) if request else None
        return bool(profile and obj.participants.filter(player=profile).exists())


class WorldChatSerializer(serializers.ModelSerializer):
    user = ProfileSerializer(read_only=True)
    competition_detail = CompetitionSerializer(source="competition", read_only=True)
    challenge_detail = ChallengeSerializer(source="challenge", read_only=True)

    class Meta:
        model = WorldChatMessage
        fields = "__all__"


class MatchMessageSerializer(serializers.ModelSerializer):
    sender_username = serializers.CharField(source="sender.username", read_only=True)

    class Meta:
        model = MatchMessage
        fields = "__all__"
        read_only_fields = ["match", "sender", "created_at"]


class CompetitionMessageSerializer(serializers.ModelSerializer):
    sender_username = serializers.CharField(source="sender.username", read_only=True)

    class Meta:
        model = CompetitionMessage
        fields = "__all__"
        read_only_fields = ["competition", "sender", "created_at"]


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = "__all__"