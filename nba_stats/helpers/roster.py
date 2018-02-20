import logging
from django.db.models import Q
from nba_stats.models import RosterEntry
log = logging.getLogger('stats')


def get_roster_on_date(team, the_date):
    roster = RosterEntry.objects.filter(Q(end_date__isnull=True) | Q(end_date__gt=the_date),
                                        team=team, acquisition_date__lt=the_date)
    return roster


def make_roster_xrefs(player):
    from nba_stats.models import Transaction, RosterEntry
    log.debug(("Creating roster xrefs for ", player.display_first_last))
    transactions = Transaction.objects.filter(player=player).order_by('transaction_date')
    cur_team = None
    cur_roster_entry = None
    for tsact in transactions:
        if tsact.transaction_type == "Suspended":
            # Idk why bbref considers suspensions a transaction. Should be under injuries IMO
            continue
        if tsact.to_team != cur_team:
            log.debug(("old team", cur_team, "new team", tsact.to_team))
            if cur_roster_entry is None:
                log.debug("cur roster entry is none")
                print(("Cur roster is None.", tsact.transaction_type))
                cur_roster_entry = RosterEntry(team=tsact.to_team, player=player,
                                               acquired_via=tsact.transaction_type,
                                               acquisition_date=tsact.transaction_date,
                                               end_date=None)
                cur_roster_entry.save()

            else:
                log.debug("roster entry exists. Updating it & making new one")
                cur_roster_entry.end_date = tsact.transaction_date
                cur_roster_entry.save()
                cur_roster_entry = RosterEntry(team=tsact.to_team, player=player,
                                               acquired_via=tsact.transaction_type,
                                               acquisition_date=tsact.transaction_date,
                                               end_date=None)
                cur_roster_entry.save()
            cur_team = tsact.to_team
    log.debug(("Finished creating roster entries for ", player.display_first_last))


def get_prev_roster_entry(entry):
    entry = RosterEntry.objects.filter(player=entry.player,
                                       end_date=entry.acquisition_date).first()
    return entry
