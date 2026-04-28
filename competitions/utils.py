from .models import Match


def advance_winner(match):
    """
    Move winner to next round match
    """

    if not match.next_match:
        return

    next_match = match.next_match

    # Decide slot (player1 or player2)
    if not next_match.player1:
        next_match.player1 = match.winner
    elif not next_match.player2:
        next_match.player2 = match.winner

    next_match.save()