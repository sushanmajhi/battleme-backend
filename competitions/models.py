from django.db import models
from accounts.models import Profile
import uuid


class Competition(models.Model):
    FORMAT_CHOICES = [
        ("knockout", "Knockout"),
        ("league", "League"),
    ]

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("open", "Open"),
        ("live", "Live"),
        ("completed", "Completed"),
    ]

    REGION_CHOICES = [
        ("asia", "Asia"),
        ("europe", "Europe"),
        ("na", "North America"),
        ("global", "Global"),
    ]

    tournament_code = models.CharField(
        max_length=12,
        unique=True,
        blank=True,
    )

    region = models.CharField(
        max_length=20,
        choices=REGION_CHOICES,
        default="global",
    )

    title = models.CharField(max_length=200)
    game = models.CharField(max_length=100, default="eFootball")

    host = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name="hosted_competitions",
    )

    format = models.CharField(
        max_length=20,
        choices=FORMAT_CHOICES,
        default="knockout",
    )

    rules = models.TextField(blank=True)
    max_players = models.PositiveIntegerField(default=16)
    start_date = models.DateTimeField()
    registration_deadline = models.DateTimeField()

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="draft",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.tournament_code:
            self.tournament_code = str(uuid.uuid4()).split("-")[0].upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class CompetitionParticipant(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]

    competition = models.ForeignKey(
        Competition,
        on_delete=models.CASCADE,
        related_name="participants",
    )

    player = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name="competition_entries",
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="approved",
    )

    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("competition", "player")
        ordering = ["joined_at"]

    def __str__(self):
        return f"{self.player.username} - {self.competition.title}"


class Match(models.Model):
    STATUS_CHOICES = [
        ("scheduled", "Scheduled"),
        ("pending_approval", "Pending Approval"),
        ("completed", "Completed"),
        ("disputed", "Disputed"),
        ("rejected", "Rejected"),
    ]

    competition = models.ForeignKey(
        Competition,
        on_delete=models.CASCADE,
        related_name="matches",
    )

    round_number = models.PositiveIntegerField(default=1)

    player1 = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name="matches_as_player1",
    )

    player2 = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name="matches_as_player2",
    )

    player1_score = models.PositiveIntegerField(default=0)
    player2_score = models.PositiveIntegerField(default=0)

    winner = models.ForeignKey(
        Profile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="won_matches",
    )

    scheduled_at = models.DateTimeField(null=True, blank=True)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="scheduled",
    )

    proof_image = models.URLField(blank=True, null=True)
    notes = models.TextField(blank=True)

    submitted_by = models.ForeignKey(
        Profile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="submitted_matches",
    )

    approved_by = models.ForeignKey(
        Profile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_matches",
    )

    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["round_number", "id"]

    def __str__(self):
        return f"{self.player1.username} vs {self.player2.username}"


class Standing(models.Model):
    competition = models.ForeignKey(
        Competition,
        on_delete=models.CASCADE,
        related_name="standings",
    )

    player = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name="standings",
    )

    played = models.PositiveIntegerField(default=0)
    wins = models.PositiveIntegerField(default=0)
    draws = models.PositiveIntegerField(default=0)
    losses = models.PositiveIntegerField(default=0)
    goals_for = models.PositiveIntegerField(default=0)
    goals_against = models.PositiveIntegerField(default=0)
    goal_difference = models.IntegerField(default=0)
    points = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("competition", "player")
        ordering = ["-points", "-goal_difference", "-goals_for", "id"]

    def __str__(self):
        return f"{self.player.username} - {self.competition.title}"


class MatchDispute(models.Model):
    STATUS_CHOICES = [
        ("open", "Open"),
        ("resolved", "Resolved"),
        ("dismissed", "Dismissed"),
    ]

    match = models.ForeignKey(
        Match,
        on_delete=models.CASCADE,
        related_name="disputes",
    )

    raised_by = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name="raised_disputes",
    )

    reason = models.TextField()

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="open",
    )

    resolution_notes = models.TextField(blank=True)

    resolved_by = models.ForeignKey(
        Profile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="resolved_disputes",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Dispute for Match {self.match.id} by {self.raised_by.username}"


class Challenge(models.Model):
    STATUS_CHOICES = [
        ("open", "Open"),
        ("accepted", "Accepted"),
        ("cancelled", "Cancelled"),
        ("completed", "Completed"),
    ]

    challenger = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name="sent_challenges",
    )

    opponent = models.ForeignKey(
        Profile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="received_challenges",
    )

    game = models.CharField(max_length=100, default="eFootball")
    message = models.TextField(blank=True)
    scheduled_at = models.DateTimeField(null=True, blank=True)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="open",
    )

    challenger_score = models.PositiveIntegerField(null=True, blank=True)
    opponent_score = models.PositiveIntegerField(null=True, blank=True)

    winner = models.ForeignKey(
        Profile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="won_challenges",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        opponent_name = self.opponent.username if self.opponent else "Open"
        return f"{self.challenger.username} vs {opponent_name}"


class WorldChatMessage(models.Model):
    MESSAGE_TYPE_CHOICES = [
        ("message", "Message"),
        ("join_request", "Join Request"),
        ("tournament_invite", "Tournament Invite"),
        ("challenge_invite", "Challenge Invite"),
    ]

    user = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name="chat_messages",
    )

    content = models.TextField(blank=True)

    message_type = models.CharField(
        max_length=30,
        choices=MESSAGE_TYPE_CHOICES,
        default="message",
    )

    competition = models.ForeignKey(
        Competition,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="chat_messages",
    )

    challenge = models.ForeignKey(
        Challenge,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="chat_messages",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username}: {self.message_type}"


class MatchMessage(models.Model):
    match = models.ForeignKey(
        Match,
        on_delete=models.CASCADE,
        related_name="messages",
    )

    sender = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name="match_messages",
    )

    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.sender.username}: Match {self.match.id}"


class CompetitionMessage(models.Model):
    competition = models.ForeignKey(
        Competition,
        on_delete=models.CASCADE,
        related_name="messages",
    )

    sender = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name="competition_messages",
    )

    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.sender.username}: {self.competition.title}"

class Notification(models.Model):
    TYPE_CHOICES = [
        ("join", "Join"),
        ("challenge", "Challenge"),
        ("match", "Match"),
        ("system", "System"),
    ]

    user = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name="notifications",
    )

    message = models.TextField()

    type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default="system",
    )

    is_read = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} - {self.message[:30]}"