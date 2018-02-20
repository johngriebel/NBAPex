import logging
from uuid import uuid4
from datetime import date, datetime, timedelta
from nba_stats.models import Player
from nba_fantasy.models import (FantasyTeam, FantasyTeamTransaction,
                                FantasyTeamRosterEntry)

log = logging.getLogger('stats')


def create_trade_proposal(trade_map):
    teams_incoming = {}
    teams_outgoing = {}

    for id_combo in trade_map:
        team_id, player_id = [int(part) for part in id_combo.split("_")]
        cur_team = FantasyTeam.objects.get(id=team_id)
        player = Player.objects.get(id=player_id)
        opposing_team = FantasyTeam.objects.get(id=trade_map[id_combo])

        if opposing_team in teams_incoming:
            teams_incoming[opposing_team].append(player)
        else:
            teams_incoming[opposing_team] = [player]

        if cur_team in teams_outgoing:
            teams_outgoing[cur_team].append(player)
        else:
            teams_outgoing[cur_team] = [player]

    if teams_incoming.keys() != teams_outgoing.keys():
        log.debug(("Keys", len(teams_incoming.keys()), len(teams_outgoing.keys())))
        raise Exception("Bork")

    prop_date = datetime.now()
    # Temp default
    exp_date = prop_date + timedelta(days=2)
    trade_identifier = uuid4()

    for team in teams_incoming:
        trans = FantasyTeamTransaction(team=team, transaction_type="TD",
                                       proposal_time=prop_date, expiry_time=exp_date,
                                       trade_identifier=trade_identifier)
        trans.save()
        trans.incoming_players = teams_incoming[team]
        trans.outgoing_players = teams_outgoing[team]
        trans.save()


def handle_accepted_trade(all_related_trades):
    today = date.today()
    for trade in all_related_trades:
        close_roster_entries = FantasyTeamRosterEntry.objects.filter(
            player__in=trade.outgoing_players.all(),
            team=trade.team,
            end_date=None)
        for ros in close_roster_entries:
            ros.end_date = today
            ros.save()
        for player in trade.incoming_players.all():
            new_roster_entry = FantasyTeamRosterEntry(league=trade.team.league,
                                                      team=trade.team,
                                                      player=player,
                                                      acquired_via="TD",
                                                      acquisition_date=today,
                                                      end_date=None)
            new_roster_entry.save()

        trade.transaction_date = today
        trade.accepted_flag = True
        trade.save()


def add_free_agent_to_team(league, fantasy_team, player):
    today = date.today()
    log.debug(("league", league.id, "team", fantasy_team.id, "player", player.id))

    roster_settings = RosterSettings.objects.get(league=league)
    cur_roster_size = FantasyTeamRosterEntry.objects.filter(team=fantasy_team,
                                                            end_date=None).count()
    if cur_roster_size >= roster_settings.total:
        data = {'added': False}
    else:
        existing_rec = FantasyTeamRosterEntry.objects.get(league=league,
                                                          player=player,
                                                          end_date=None)
        existing_rec.end_date = today
        existing_rec.save()
        new_rec = FantasyTeamRosterEntry(league=league,
                                         team=fantasy_team,
                                         player=player,
                                         acquisition_date=today,
                                         end_date=None,
                                         acquired_via="FA")
        new_rec.save()
        transaction = FantasyTeamTransaction(team=fantasy_team,
                                             transaction_type="FA",
                                             transaction_date=today)
        transaction.save()
        transaction.incoming_players = [player]
        transaction.save()
        log.debug("created new record")
        data = {'added': True}
    return data
