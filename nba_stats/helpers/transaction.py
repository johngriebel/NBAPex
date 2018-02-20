from nba_stats.models import Transaction


def get_transaction_for_roster_entry(entry):
    """Gets the Transaction that led to the given roster entry."""
    # Strictly speaking, the transaction_type filter shouldn't be necessary,
    # But it can't hurt
    tsact = Transaction.objects.get(player=entry.player,
                                    to_team=entry.team,
                                    transaction_date=entry.acquisition_date,
                                    transaction_type=entry.acquired_via)
    return tsact


def get_prior_transaction(transaction):
    prev_tsact = Transaction.objects.filter(player=transaction.player,
                                            transaction_date__lt=
                                            transaction.transaction_date).order_by('-transaction_date')
    if prev_tsact.exists():
        return prev_tsact.first()
    else:
        return None