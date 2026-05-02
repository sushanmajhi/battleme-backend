from django.db import transaction
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from accounts.models import Profile
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

from .serializers import (
    CompetitionSerializer,
    CompetitionParticipantSerializer,
    MatchSerializer,
    MatchResultSubmitSerializer,
    MatchApprovalSerializer,
    MatchDisputeCreateSerializer,
    MatchDisputeSerializer,
    DisputeResolveSerializer,
    StandingSerializer,
    ChallengeSerializer,
    ChallengeCreateSerializer,
    ChallengeResultSubmitSerializer,
    CompetitionDetailSerializer,
    WorldChatSerializer,
    MatchMessageSerializer,
    CompetitionMessageSerializer,
)

from .permissions import IsHostUser


WIN_XP = 25
LOSS_XP = 10
TOURNAMENT_WIN_BONUS_XP = 100
JOIN_COMPETITION_XP = 5
CHALLENGE_WIN_XP = 20
CHALLENGE_LOSS_XP = 8


def update_profile_rank_fields(profile):
    profile.level = (profile.xp // 100) + 1

    if profile.xp >= 1200:
        profile.rank_tier = "Champion"
    elif profile.xp >= 800:
        profile.rank_tier = "Diamond"
    elif profile.xp >= 500:
        profile.rank_tier = "Platinum"
    elif profile.xp >= 250:
        profile.rank_tier = "Gold"
    elif profile.xp >= 100:
        profile.rank_tier = "Silver"
    else:
        profile.rank_tier = "Bronze"


def append_note(existing_text, new_text):
    existing_text = (existing_text or "").strip()
    new_text = (new_text or "").strip()

    if not new_text:
        return existing_text

    if not existing_text:
        return new_text

    return f"{existing_text}\n\n{new_text}"


def award_match_xp_and_stats(match):
    player1 = match.player1
    player2 = match.player2
    winner = match.winner

    is_bye = player1.id == player2.id

    if is_bye:
        player1.matches_played += 1
        player1.wins += 1
        player1.goals_scored += match.player1_score
        player1.goals_conceded += match.player2_score
        player1.xp += WIN_XP
        update_profile_rank_fields(player1)
        player1.save()
        return

    player1.matches_played += 1
    player2.matches_played += 1

    player1.goals_scored += match.player1_score
    player1.goals_conceded += match.player2_score

    player2.goals_scored += match.player2_score
    player2.goals_conceded += match.player1_score

    if winner and winner.id == player1.id:
        player1.wins += 1
        player2.losses += 1
        player1.xp += WIN_XP
        player2.xp += LOSS_XP
    elif winner and winner.id == player2.id:
        player2.wins += 1
        player1.losses += 1
        player2.xp += WIN_XP
        player1.xp += LOSS_XP

    update_profile_rank_fields(player1)
    update_profile_rank_fields(player2)

    player1.save()
    player2.save()


def award_challenge_xp_and_stats(challenge):
    challenger = challenge.challenger
    opponent = challenge.opponent
    winner = challenge.winner

    if not opponent or not winner:
        return

    challenger.matches_played += 1
    opponent.matches_played += 1

    challenger.goals_scored += challenge.challenger_score
    challenger.goals_conceded += challenge.opponent_score

    opponent.goals_scored += challenge.opponent_score
    opponent.goals_conceded += challenge.challenger_score

    if winner.id == challenger.id:
        challenger.wins += 1
        opponent.losses += 1
        challenger.xp += CHALLENGE_WIN_XP
        opponent.xp += CHALLENGE_LOSS_XP
    else:
        opponent.wins += 1
        challenger.losses += 1
        opponent.xp += CHALLENGE_WIN_XP
        challenger.xp += CHALLENGE_LOSS_XP

    update_profile_rank_fields(challenger)
    update_profile_rank_fields(opponent)

    challenger.save()
    opponent.save()


def update_league_standing_for_match(match):
    if match.competition.format != "league":
        return

    player1_standing, _ = Standing.objects.get_or_create(
        competition=match.competition,
        player=match.player1,
    )
    player2_standing, _ = Standing.objects.get_or_create(
        competition=match.competition,
        player=match.player2,
    )

    player1_standing.played += 1
    player2_standing.played += 1

    player1_standing.goals_for += match.player1_score
    player1_standing.goals_against += match.player2_score
    player2_standing.goals_for += match.player2_score
    player2_standing.goals_against += match.player1_score

    if match.player1_score > match.player2_score:
        player1_standing.wins += 1
        player1_standing.points += 3
        player2_standing.losses += 1
    elif match.player2_score > match.player1_score:
        player2_standing.wins += 1
        player2_standing.points += 3
        player1_standing.losses += 1
    else:
        player1_standing.draws += 1
        player2_standing.draws += 1
        player1_standing.points += 1
        player2_standing.points += 1

    player1_standing.goal_difference = (
        player1_standing.goals_for - player1_standing.goals_against
    )
    player2_standing.goal_difference = (
        player2_standing.goals_for - player2_standing.goals_against
    )

    player1_standing.save()
    player2_standing.save()


def maybe_create_next_round_match(competition, completed_match):
    if competition.format != "knockout":
        return

    if not completed_match.winner:
        return

    current_round = completed_match.round_number
    next_round = current_round + 1

    current_round_matches = Match.objects.filter(
        competition=competition,
        round_number=current_round,
    ).count()

    if current_round_matches <= 1:
        competition.status = "completed"
        competition.save()

        winner = completed_match.winner
        winner.xp += TOURNAMENT_WIN_BONUS_XP
        update_profile_rank_fields(winner)
        winner.save()
        return

    completed_round_matches = Match.objects.filter(
        competition=competition,
        round_number=current_round,
        status="completed",
        winner__isnull=False,
    ).order_by("id")

    total_matches_this_round = Match.objects.filter(
        competition=competition,
        round_number=current_round,
    ).count()

    if completed_round_matches.count() != total_matches_this_round:
        return

    winners = [m.winner for m in completed_round_matches]

    Match.objects.filter(
        competition=competition,
        round_number=next_round,
    ).delete()

    index = 0
    while index < len(winners) - 1:
        Match.objects.create(
            competition=competition,
            round_number=next_round,
            player1=winners[index],
            player2=winners[index + 1],
            status="scheduled",
        )
        index += 2

    if len(winners) % 2 != 0:
        last_player = winners[-1]
        bye_match = Match.objects.create(
            competition=competition,
            round_number=next_round,
            player1=last_player,
            player2=last_player,
            player1_score=1,
            player2_score=0,
            winner=last_player,
            status="completed",
            notes="Automatic bye",
        )
        award_match_xp_and_stats(bye_match)
        maybe_create_next_round_match(competition, bye_match)

    next_round_matches = Match.objects.filter(
        competition=competition,
        round_number=next_round,
    )

    if next_round_matches.count() == 1:
        only_match = next_round_matches.first()
        if only_match.status == "completed" and only_match.winner:
            competition.status = "completed"
            competition.save()

            winner = only_match.winner
            winner.xp += TOURNAMENT_WIN_BONUS_XP
            update_profile_rank_fields(winner)
            winner.save()


class CompetitionListCreateView(generics.ListCreateAPIView):
    queryset = Competition.objects.select_related("host", "host__user").all()

    def get_serializer_class(self):
        if self.request.method == "POST":
            return CompetitionCreateSerializer
        return CompetitionSerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [permissions.IsAuthenticated(), IsHostUser()]
        return [permissions.AllowAny()]

    def perform_create(self, serializer):
        serializer.save(host=self.request.user.profile)


class CompetitionDetailView(generics.RetrieveAPIView):
    queryset = Competition.objects.select_related("host", "host__user").prefetch_related(
        "participants__player__user",
        "matches__player1__user",
        "matches__player2__user",
        "matches__winner__user",
    )
    serializer_class = CompetitionDetailSerializer
    permission_classes = [permissions.AllowAny]


class CompetitionParticipantListCreateView(generics.ListCreateAPIView):
    serializer_class = CompetitionParticipantSerializer

    def get_queryset(self):
        competition_id = self.kwargs["competition_id"]
        return CompetitionParticipant.objects.select_related(
            "player",
            "player__user",
        ).filter(competition_id=competition_id)

    def get_permissions(self):
        if self.request.method == "POST":
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    def create(self, request, *args, **kwargs):
        competition_id = self.kwargs["competition_id"]

        try:
            competition = Competition.objects.get(id=competition_id)
        except Competition.DoesNotExist:
            return Response({"detail": "Competition not found."}, status=404)

        profile = request.user.profile

        if competition.status not in ["draft", "open"]:
            return Response({"detail": "This competition is not open for joining."}, status=400)

        if timezone.now() > competition.registration_deadline:
            return Response({"detail": "Registration deadline has passed."}, status=400)

        if CompetitionParticipant.objects.filter(
            competition=competition,
            player=profile,
        ).exists():
            return Response({"detail": "You already requested or joined this competition."}, status=400)

        current_count = CompetitionParticipant.objects.filter(
            competition=competition,
            status__in=["pending", "approved"],
        ).count()

        if current_count >= competition.max_players:
            return Response({"detail": "Competition is full."}, status=400)

        participant = CompetitionParticipant.objects.create(
            competition=competition,
            player=profile,
            status="pending",
        )

        serializer = self.get_serializer(participant)
        return Response(
            {
                "message": "Join request submitted. Waiting for host approval.",
                "participant": serializer.data,
            },
            status=status.HTTP_201_CREATED,
        )


class ParticipantApprovalView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsHostUser]

    def post(self, request, pk):
        try:
            participant = CompetitionParticipant.objects.select_related(
                "competition",
                "competition__host",
                "player",
            ).get(pk=pk)
        except CompetitionParticipant.DoesNotExist:
            return Response({"detail": "Participant not found."}, status=404)

        profile = request.user.profile

        if participant.competition.host != profile and profile.role != "admin":
            return Response({"detail": "You cannot approve or reject this participant."}, status=403)

        action = request.data.get("action")

        if action not in ["approve", "reject"]:
            return Response({"detail": "Invalid action. Use approve or reject."}, status=400)

        previous_status = participant.status

        if action == "approve":
            approved_count = CompetitionParticipant.objects.filter(
                competition=participant.competition,
                status="approved",
            ).count()

            if previous_status != "approved" and approved_count >= participant.competition.max_players:
                return Response({"detail": "Competition is already full."}, status=400)

            participant.status = "approved"
            participant.save()

            if previous_status != "approved":
                player = participant.player
                player.xp += JOIN_COMPETITION_XP
                update_profile_rank_fields(player)
                player.save()

            return Response(
                {
                    "message": "Participant approved successfully.",
                    "participant": CompetitionParticipantSerializer(participant).data,
                }
            )

        participant.status = "rejected"
        participant.save()

        return Response(
            {
                "message": "Participant rejected successfully.",
                "participant": CompetitionParticipantSerializer(participant).data,
            }
        )


class MatchListCreateView(generics.ListCreateAPIView):
    serializer_class = MatchSerializer

    def get_queryset(self):
        competition_id = self.kwargs["competition_id"]
        return Match.objects.select_related(
            "player1",
            "player1__user",
            "player2",
            "player2__user",
            "winner",
            "winner__user",
            "submitted_by",
            "submitted_by__user",
            "approved_by",
            "approved_by__user",
            "competition",
        ).filter(competition_id=competition_id)

    def get_permissions(self):
        if self.request.method == "POST":
            return [permissions.IsAuthenticated(), IsHostUser()]
        return [permissions.AllowAny()]

    def perform_create(self, serializer):
        serializer.save(competition_id=self.kwargs["competition_id"])


class MatchResultSubmitView(generics.UpdateAPIView):
    queryset = Match.objects.select_related(
        "competition",
        "player1",
        "player2",
        "winner",
        "submitted_by",
        "approved_by",
    )
    serializer_class = MatchResultSubmitSerializer
    permission_classes = [permissions.IsAuthenticated]

    def update(self, request, *args, **kwargs):
        match = self.get_object()
        profile = request.user.profile

        allowed_player_ids = [match.player1.id, match.player2.id]

        if profile.id not in allowed_player_ids and profile.role not in ["host", "admin"]:
            return Response({"detail": "You cannot submit this result."}, status=403)

        if match.status == "completed":
            return Response({"detail": "This match is already completed."}, status=400)

        serializer = self.get_serializer(match, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        player1_score = serializer.validated_data.get("player1_score", match.player1_score)
        player2_score = serializer.validated_data.get("player2_score", match.player2_score)

        if match.competition.format == "knockout" and player1_score == player2_score:
            return Response({"detail": "Knockout matches cannot end in a draw."}, status=400)

        match.player1_score = player1_score
        match.player2_score = player2_score
        match.proof_image = serializer.validated_data.get("proof_image", match.proof_image)
        match.notes = serializer.validated_data.get("notes", match.notes)
        match.submitted_by = profile
        match.status = "pending_approval"
        match.winner = None
        match.approved_by = None
        match.approved_at = None
        match.save()

        return Response(
            {
                "message": "Result submitted and waiting for host approval.",
                "match": MatchSerializer(match).data,
            }
        )


class MatchApprovalView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsHostUser]

    def post(self, request, pk):
        try:
            match = Match.objects.select_related(
                "competition",
                "player1",
                "player2",
                "winner",
            ).get(pk=pk)
        except Match.DoesNotExist:
            return Response({"detail": "Match not found."}, status=404)

        if match.competition.host != request.user.profile and request.user.profile.role != "admin":
            return Response({"detail": "You cannot approve this match."}, status=403)

        serializer = MatchApprovalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        action = serializer.validated_data["action"]
        notes = serializer.validated_data.get("notes", "")

        if action == "reject":
            match.status = "rejected"

            if notes:
                match.notes = append_note(match.notes, f"Host rejection note: {notes}")

            match.save()

            return Response(
                {
                    "message": "Match result rejected.",
                    "match": MatchSerializer(match).data,
                }
            )

        player1_score = match.player1_score
        player2_score = match.player2_score

        if match.competition.format == "knockout" and player1_score == player2_score:
            return Response({"detail": "Knockout matches cannot end in a draw."}, status=400)

        winner = None

        if player1_score > player2_score:
            winner = match.player1
        elif player2_score > player1_score:
            winner = match.player2

        match.winner = winner
        match.status = "completed"
        match.approved_by = request.user.profile
        match.approved_at = timezone.now()

        if notes:
            match.notes = append_note(match.notes, f"Host approval note: {notes}")

        match.save()

        award_match_xp_and_stats(match)

        if match.competition.format == "league":
            update_league_standing_for_match(match)
        elif match.competition.format == "knockout":
            maybe_create_next_round_match(match.competition, match)

        return Response(
            {
                "message": "Match approved successfully.",
                "match": MatchSerializer(match).data,
            }
        )


class MatchDisputeCreateView(generics.CreateAPIView):
    serializer_class = MatchDisputeCreateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        try:
            match = Match.objects.select_related(
                "competition",
                "player1",
                "player2",
            ).get(pk=self.kwargs["pk"])
        except Match.DoesNotExist:
            return Response({"detail": "Match not found."}, status=404)

        profile = request.user.profile
        allowed_player_ids = [match.player1.id, match.player2.id]

        if profile.id not in allowed_player_ids and profile.role not in ["host", "admin"]:
            return Response({"detail": "You cannot raise a dispute for this match."}, status=403)

        if match.status not in ["pending_approval", "rejected"]:
            return Response(
                {"detail": "Disputes can only be raised for pending or rejected match results."},
                status=400,
            )

        if MatchDispute.objects.filter(match=match, status="open").exists():
            return Response({"detail": "There is already an open dispute for this match."}, status=400)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        dispute = MatchDispute.objects.create(
            match=match,
            raised_by=profile,
            reason=serializer.validated_data["reason"],
            status="open",
        )

        match.status = "disputed"
        match.save()

        return Response(
            {
                "message": "Dispute raised successfully.",
                "dispute": MatchDisputeSerializer(dispute).data,
                "match": MatchSerializer(match).data,
            },
            status=201,
        )


class MatchDisputeListView(generics.ListAPIView):
    serializer_class = MatchDisputeSerializer
    permission_classes = [permissions.IsAuthenticated, IsHostUser]

    def get_queryset(self):
        competition_id = self.kwargs["competition_id"]
        return MatchDispute.objects.select_related(
            "raised_by",
            "raised_by__user",
            "resolved_by",
            "resolved_by__user",
            "match",
            "match__competition",
        ).filter(match__competition_id=competition_id)


class MatchDisputeResolveView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsHostUser]

    def post(self, request, pk):
        try:
            dispute = MatchDispute.objects.select_related(
                "match",
                "match__competition",
                "match__player1",
                "match__player2",
            ).get(pk=pk)
        except MatchDispute.DoesNotExist:
            return Response({"detail": "Dispute not found."}, status=404)

        if dispute.match.competition.host != request.user.profile and request.user.profile.role != "admin":
            return Response({"detail": "You cannot resolve this dispute."}, status=403)

        if dispute.status != "open":
            return Response({"detail": "This dispute is already closed."}, status=400)

        serializer = DisputeResolveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        action = serializer.validated_data["action"]
        resolution_notes = serializer.validated_data.get("resolution_notes", "")
        match = dispute.match

        dispute.status = action
        dispute.resolution_notes = resolution_notes
        dispute.resolved_by = request.user.profile
        dispute.resolved_at = timezone.now()
        dispute.save()

        if action == "dismissed":
            match.status = "pending_approval"

            if resolution_notes:
                match.notes = append_note(match.notes, f"Dispute dismissed: {resolution_notes}")

            match.save()

            return Response(
                {
                    "message": "Dispute dismissed and match returned to pending approval.",
                    "dispute": MatchDisputeSerializer(dispute).data,
                    "match": MatchSerializer(match).data,
                }
            )

        player1_score = serializer.validated_data["player1_score"]
        player2_score = serializer.validated_data["player2_score"]

        if match.competition.format == "knockout" and player1_score == player2_score:
            return Response({"detail": "Knockout matches cannot end in a draw."}, status=400)

        winner = None

        if player1_score > player2_score:
            winner = match.player1
        elif player2_score > player1_score:
            winner = match.player2

        match.player1_score = player1_score
        match.player2_score = player2_score
        match.winner = winner
        match.status = "completed"
        match.approved_by = request.user.profile
        match.approved_at = timezone.now()

        if resolution_notes:
            match.notes = append_note(match.notes, f"Dispute resolved: {resolution_notes}")

        match.save()

        award_match_xp_and_stats(match)

        if match.competition.format == "league":
            update_league_standing_for_match(match)
        elif match.competition.format == "knockout":
            maybe_create_next_round_match(match.competition, match)

        return Response(
            {
                "message": "Dispute resolved and match finalized successfully.",
                "dispute": MatchDisputeSerializer(dispute).data,
                "match": MatchSerializer(match).data,
            }
        )


class StandingListView(generics.ListAPIView):
    serializer_class = StandingSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        competition_id = self.kwargs["competition_id"]

        return Standing.objects.select_related(
            "player",
            "player__user",
        ).filter(competition_id=competition_id)


class MyCompetitionsView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsHostUser]

    def get(self, request):
        competitions = Competition.objects.select_related(
            "host",
            "host__user",
        ).filter(host=request.user.profile)

        serializer = CompetitionSerializer(
            competitions,
            many=True,
            context={"request": request},
        )

        return Response(serializer.data)


class MyJoinedCompetitionsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        competitions = Competition.objects.filter(
            participants__player=request.user.profile,
            participants__status="approved",
        ).select_related(
            "host",
            "host__user",
        ).distinct()

        serializer = CompetitionSerializer(
            competitions,
            many=True,
            context={"request": request},
        )

        return Response(serializer.data)


class GenerateKnockoutMatchesView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsHostUser]

    def post(self, request, competition_id):
        try:
            competition = Competition.objects.get(
                id=competition_id,
                host=request.user.profile,
            )
        except Competition.DoesNotExist:
            return Response({"detail": "Competition not found."}, status=404)

        if competition.format != "knockout":
            return Response(
                {"detail": "Match generation is currently only supported for knockout competitions."},
                status=400,
            )

        existing_matches = Match.objects.filter(competition=competition).exists()

        if existing_matches:
            return Response({"detail": "Matches have already been generated for this competition."}, status=400)

        approved_participants = list(
            CompetitionParticipant.objects.select_related(
                "player",
                "player__user",
            )
            .filter(competition=competition, status="approved")
            .order_by("joined_at")
        )

        if len(approved_participants) < 2:
            return Response({"detail": "At least 2 approved participants are required."}, status=400)

        players = [entry.player for entry in approved_participants]
        created_matches = []
        index = 0

        while index < len(players) - 1:
            match = Match.objects.create(
                competition=competition,
                round_number=1,
                player1=players[index],
                player2=players[index + 1],
                status="scheduled",
            )
            created_matches.append(match)
            index += 2

        if len(players) % 2 != 0:
            last_player = players[-1]

            match = Match.objects.create(
                competition=competition,
                round_number=1,
                player1=last_player,
                player2=last_player,
                player1_score=1,
                player2_score=0,
                winner=last_player,
                status="completed",
                notes="Automatic bye",
            )

            award_match_xp_and_stats(match)
            created_matches.append(match)
            maybe_create_next_round_match(competition, match)

        competition.status = "live"
        competition.save()

        serializer = MatchSerializer(created_matches, many=True)

        return Response(
            {
                "message": "Round 1 matches generated successfully.",
                "matches": serializer.data,
            },
            status=201,
        )


class ChallengeListCreateView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_context(self):
        return {"request": self.request}

    def get(self, request, *args, **kwargs):
        challenges = Challenge.objects.select_related(
            "challenger",
            "challenger__user",
            "opponent",
            "opponent__user",
            "winner",
            "winner__user",
        ).all().order_by("-created_at")

        serializer = ChallengeSerializer(
            challenges,
            many=True,
            context=self.get_serializer_context(),
        )

        return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        serializer = ChallengeCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        challenge = Challenge.objects.create(
            challenger=request.user.profile,
            game=serializer.validated_data.get("game", "eFootball"),
            message=serializer.validated_data.get("message", ""),
            scheduled_at=serializer.validated_data.get("scheduled_at"),
            status="open",
        )

        return Response(
            {
                "message": "Open challenge created successfully.",
                "challenge": ChallengeSerializer(
                    challenge,
                    context=self.get_serializer_context(),
                ).data,
            },
            status=201,
        )


class ChallengeAcceptView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        profile = getattr(request.user, "profile", None)

        if not profile:
            return Response(
                {"detail": "Profile not found. Please log out and log in again."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            challenge = Challenge.objects.get(pk=pk)
        except Challenge.DoesNotExist:
            return Response(
                {"detail": "Challenge not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if challenge.status != "open":
            return Response(
                {"detail": "This challenge is no longer open."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if challenge.challenger_id == profile.id:
            return Response(
                {"detail": "You cannot accept your own challenge."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if challenge.opponent_id is not None:
            return Response(
                {"detail": "This challenge has already been accepted."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        challenge.opponent = profile
        challenge.status = "accepted"
        challenge.save()

        return Response(
            {"message": "Challenge accepted successfully."},
            status=status.HTTP_200_OK,
        )

class ChallengeCancelView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        try:
            challenge = Challenge.objects.select_related(
                "challenger",
                "opponent",
            ).get(pk=pk)
        except Challenge.DoesNotExist:
            return Response({"detail": "Challenge not found."}, status=404)

        if challenge.challenger != request.user.profile:
            return Response({"detail": "You can only cancel your own challenge."}, status=403)

        if challenge.status != "open":
            return Response({"detail": "Only open challenges can be cancelled."}, status=400)

        challenge.status = "cancelled"
        challenge.save()

        return Response(
            {
                "message": "Challenge cancelled.",
                "challenge": ChallengeSerializer(
                    challenge,
                    context={"request": request},
                ).data,
            }
        )


class ChallengeResultSubmitView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        try:
            challenge = Challenge.objects.select_related(
                "challenger",
                "opponent",
                "winner",
            ).get(pk=pk)
        except Challenge.DoesNotExist:
            return Response({"detail": "Challenge not found."}, status=404)

        if not challenge.opponent:
            return Response({"detail": "This challenge does not have an opponent yet."}, status=400)

        if request.user.profile not in [challenge.challenger, challenge.opponent]:
            return Response({"detail": "You cannot submit this challenge result."}, status=403)

        if challenge.status != "accepted":
            return Response({"detail": "Only accepted challenges can be completed."}, status=400)

        serializer = ChallengeResultSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        challenger_score = serializer.validated_data["challenger_score"]
        opponent_score = serializer.validated_data["opponent_score"]

        winner = challenge.challenger if challenger_score > opponent_score else challenge.opponent

        challenge.challenger_score = challenger_score
        challenge.opponent_score = opponent_score
        challenge.winner = winner
        challenge.status = "completed"
        challenge.save()

        award_challenge_xp_and_stats(challenge)

        return Response(
            {
                "message": "Challenge result submitted successfully.",
                "challenge": ChallengeSerializer(
                    challenge,
                    context={"request": request},
                ).data,
            }
        )


class WorldChatView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        messages = WorldChatMessage.objects.select_related(
            "user",
            "user__user",
            "competition",
            "competition__host",
            "competition__host__user",
            "challenge",
            "challenge__challenger",
            "challenge__challenger__user",
            "challenge__opponent",
            "challenge__opponent__user",
        ).all()[:50]

        serializer = WorldChatSerializer(
            messages,
            many=True,
            context={"request": request},
        )

        return Response(serializer.data)

    def post(self, request):
        content = request.data.get("content", "")
        message_type = request.data.get("message_type", "message")
        competition_id = request.data.get("competition")
        challenge_id = request.data.get("challenge")

        competition = None
        challenge = None

        if competition_id:
            try:
                competition = Competition.objects.get(id=competition_id)
            except Competition.DoesNotExist:
                return Response({"detail": "Competition not found."}, status=404)

        if challenge_id:
            try:
                challenge = Challenge.objects.get(id=challenge_id)
            except Challenge.DoesNotExist:
                return Response({"detail": "Challenge not found."}, status=404)

        message = WorldChatMessage.objects.create(
            user=request.user.profile,
            content=content,
            message_type=message_type,
            competition=competition,
            challenge=challenge,
        )

        serializer = WorldChatSerializer(
            message,
            context={"request": request},
        )

        return Response(serializer.data, status=201)


class MatchMessageListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        try:
            match = Match.objects.select_related(
                "competition",
                "competition__host",
                "player1",
                "player2",
            ).get(pk=pk)
        except Match.DoesNotExist:
            return Response({"detail": "Match not found."}, status=404)

        profile = request.user.profile

        allowed = [
            match.player1.id,
            match.player2.id,
            match.competition.host.id,
        ]

        if profile.id not in allowed and profile.role != "admin":
            return Response({"detail": "You cannot view these messages."}, status=403)

        messages = MatchMessage.objects.select_related(
            "sender",
            "sender__user",
        ).filter(match=match).order_by("created_at")

        serializer = MatchMessageSerializer(messages, many=True)

        return Response(serializer.data)

    def post(self, request, pk):
        try:
            match = Match.objects.select_related(
                "competition",
                "competition__host",
                "player1",
                "player2",
            ).get(pk=pk)
        except Match.DoesNotExist:
            return Response({"detail": "Match not found."}, status=404)

        profile = request.user.profile

        allowed = [
            match.player1.id,
            match.player2.id,
            match.competition.host.id,
        ]

        if profile.id not in allowed and profile.role != "admin":
            return Response({"detail": "You cannot send a message here."}, status=403)

        message_text = request.data.get("message", "").strip()

        if not message_text:
            return Response({"detail": "Message cannot be empty."}, status=400)

        message = MatchMessage.objects.create(
            match=match,
            sender=profile,
            message=message_text,
        )

        serializer = MatchMessageSerializer(message)

        return Response(serializer.data, status=201)


class CompetitionMessageListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, competition_id):
        try:
            competition = Competition.objects.get(id=competition_id)
        except Competition.DoesNotExist:
            return Response({"detail": "Competition not found."}, status=404)

        profile = request.user.profile

        is_host = competition.host == profile
        is_player = CompetitionParticipant.objects.filter(
            competition=competition,
            player=profile,
            status="approved",
        ).exists()

        if not is_host and not is_player and profile.role != "admin":
            return Response({"detail": "You cannot view this chat."}, status=403)

        messages = CompetitionMessage.objects.select_related(
            "sender",
            "sender__user",
        ).filter(competition=competition)

        serializer = CompetitionMessageSerializer(messages, many=True)

        return Response(serializer.data)

    def post(self, request, competition_id):
        try:
            competition = Competition.objects.get(id=competition_id)
        except Competition.DoesNotExist:
            return Response({"detail": "Competition not found."}, status=404)

        profile = request.user.profile

        is_host = competition.host == profile
        is_player = CompetitionParticipant.objects.filter(
            competition=competition,
            player=profile,
            status="approved",
        ).exists()

        if not is_host and not is_player and profile.role != "admin":
            return Response({"detail": "You cannot send messages here."}, status=403)

        text = request.data.get("message", "").strip()

        if not text:
            return Response({"detail": "Message cannot be empty."}, status=400)

        msg = CompetitionMessage.objects.create(
            competition=competition,
            sender=profile,
            message=text,
        )

        serializer = CompetitionMessageSerializer(msg)

        return Response(serializer.data, status=201)

class HostAddParticipantView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, competition_id):
        try:
            competition = Competition.objects.get(id=competition_id)
        except Competition.DoesNotExist:
            return Response({"detail": "Competition not found."}, status=404)

        profile = request.user.profile

        if competition.host != profile and profile.role != "admin":
            return Response({"detail": "Only the host can add players."}, status=403)

        username = request.data.get("username", "").strip()

        if not username:
            return Response({"detail": "Username is required."}, status=400)

        try:
            player = Profile.objects.get(username=username)
        except Profile.DoesNotExist:
            return Response({"detail": "Player not found."}, status=404)

        approved_count = CompetitionParticipant.objects.filter(
            competition=competition,
            status="approved",
        ).count()

        if approved_count >= competition.max_players:
            return Response({"detail": "Competition is full."}, status=400)

        participant, created = CompetitionParticipant.objects.get_or_create(
            competition=competition,
            player=player,
            defaults={"status": "approved"},
        )

        if not created:
            participant.status = "approved"
            participant.save()

        return Response(
            {
                "message": "Player added successfully.",
                "participant": CompetitionParticipantSerializer(participant).data,
            },
            status=200,
        )


class ParticipantRemoveView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, pk):
        try:
            participant = CompetitionParticipant.objects.select_related(
                "competition",
                "competition__host",
                "player",
            ).get(pk=pk)
        except CompetitionParticipant.DoesNotExist:
            return Response({"detail": "Participant not found."}, status=404)

        profile = request.user.profile

        if participant.competition.host != profile and profile.role != "admin":
            return Response({"detail": "Only the host can remove players."}, status=403)

        participant.delete()

        return Response({"message": "Player removed successfully."}, status=200)

class NotificationListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        profile = getattr(request.user, "profile", None)

        if not profile:
            return Response({"detail": "Profile not found."}, status=400)

        notifications = Notification.objects.filter(user=profile).order_by("-created_at")[:30]
        serializer = NotificationSerializer(notifications, many=True)

        return Response(serializer.data)


class NotificationMarkReadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        profile = getattr(request.user, "profile", None)

        if not profile:
            return Response({"detail": "Profile not found."}, status=400)

        try:
            notification = Notification.objects.get(pk=pk, user=profile)
        except Notification.DoesNotExist:
            return Response({"detail": "Notification not found."}, status=404)

        notification.is_read = True
        notification.save()

        return Response({"message": "Notification marked as read."})


class NotificationMarkAllReadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        profile = getattr(request.user, "profile", None)

        if not profile:
            return Response({"detail": "Profile not found."}, status=400)

        Notification.objects.filter(user=profile, is_read=False).update(is_read=True)

        return Response({"message": "All notifications marked as read."})