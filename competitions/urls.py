from django.urls import path
from .views import (
    CompetitionListCreateView,
    CompetitionDetailView,
    CompetitionParticipantListCreateView,
    MatchListCreateView,
    MatchResultSubmitView,
    MatchApprovalView,
    MatchDisputeCreateView,
    MatchDisputeListView,
    MatchDisputeResolveView,
    GenerateKnockoutMatchesView,
    StandingListView,
    MyCompetitionsView,
    MyJoinedCompetitionsView,
    ChallengeListCreateView,
    ChallengeAcceptView,
    ChallengeCancelView,
    ChallengeResultSubmitView,
    WorldChatView,
    MatchMessageListCreateView,
    CompetitionMessageListCreateView,
    ParticipantApprovalView,
    HostAddParticipantView,
    ParticipantRemoveView,
)

urlpatterns = [
    path("", CompetitionListCreateView.as_view(), name="competition-list-create"),
    path("mine/", MyCompetitionsView.as_view(), name="my-competitions"),
    path("joined/", MyJoinedCompetitionsView.as_view(), name="my-joined-competitions"),

    path("world-chat/", WorldChatView.as_view(), name="world-chat"),

    path("challenges/", ChallengeListCreateView.as_view(), name="challenge-list-create"),
    path("challenges/<int:pk>/accept/", ChallengeAcceptView.as_view(), name="challenge-accept"),
    path("challenges/<int:pk>/cancel/", ChallengeCancelView.as_view(), name="challenge-cancel"),
    path("challenges/<int:pk>/submit-result/", ChallengeResultSubmitView.as_view(), name="challenge-submit-result"),

    path("matches/<int:pk>/submit-result/", MatchResultSubmitView.as_view(), name="submit-match-result"),
    path("matches/<int:pk>/approve/", MatchApprovalView.as_view(), name="approve-match-result"),
    path("matches/<int:pk>/messages/", MatchMessageListCreateView.as_view(), name="match-messages"),
    path("matches/<int:pk>/dispute/", MatchDisputeCreateView.as_view(), name="create-match-dispute"),

    path("disputes/<int:pk>/resolve/", MatchDisputeResolveView.as_view(), name="resolve-dispute"),

    path("<int:competition_id>/messages/", CompetitionMessageListCreateView.as_view(), name="competition-messages"),
    path("<int:competition_id>/participants/", CompetitionParticipantListCreateView.as_view(), name="competition-participants"),
    path("<int:competition_id>/matches/", MatchListCreateView.as_view(), name="competition-matches"),
    path("<int:competition_id>/generate-matches/", GenerateKnockoutMatchesView.as_view(), name="generate-matches"),
    path("<int:competition_id>/disputes/", MatchDisputeListView.as_view(), name="competition-disputes"),
    path("<int:competition_id>/standings/", StandingListView.as_view(), name="competition-standings"),

    path("<int:competition_id>/host-add-player/", HostAddParticipantView.as_view(), name="host-add-player"),
    path("participants/<int:pk>/approve/", ParticipantApprovalView.as_view(), name="participant-approval"),
    path("participants/<int:pk>/remove/", ParticipantRemoveView.as_view(), name="remove-participant"),

    # keep last
    path("<int:pk>/", CompetitionDetailView.as_view(), name="competition-detail"),
]