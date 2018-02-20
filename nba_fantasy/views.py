import json
import logging
from datetime import date, datetime

from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.shortcuts import render, redirect
from nba_fantasy.helpers.matchup import TeamMatchupEntries
from nba_fantasy.helpers.team import create_lineup_entry_rows
from nba_fantasy.forms import (FantasyLeagueForm, FantasyTeamForm, LoginForm)
from nba_fantasy.helpers.transaction import (create_trade_proposal, handle_accepted_trade,
                                             add_free_agent_to_team)
from nba_fantasy.models import (FantasyLeague, FantasyTeam, FantasyTeamRosterEntry,
                                FantasyTeamTransaction, FantasyMatchup, FantasyLineupEntry)
from nba_stats.models import Player
from nba_stats.helpers.split import SPLIT_FIELD_ORDERING

log = logging.getLogger('fantasy')


def login(request):
    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            user_data = form.cleaned_data
            user = authenticate(username=user_data['username'],
                                password=user_data['password'])
            if user is not None:
                request.session['user_id'] = user.id
            else:
                # TODO: Handle this properly
                request.session['user_id'] = -1

            return redirect("nba_fantasy:index")
    else:
        form = LoginForm()

    context = {'form': form}
    return render(request, "nba_fantasy/login.html", context)


def create_league(request):
    if request.method == "POST":
        form = FantasyLeagueForm(request.POST)
        if form.is_valid():
            league = form.save()
            return redirect("nba_fantasy:roster-settings", league_id=league.id)
    else:
        form = FantasyLeagueForm()

    context = {'form': form}
    return render(request, "nba_fantasy/create_league.html", context)


def league_homepage(request, league_id):
    league = FantasyLeague.objects.get(id=league_id)
    team = FantasyTeam.objects.filter(league=league,
                                      owner_id=request.session['user_id']).first()
    context = {'league': league, 'team_id': team.id or 0}
    log.debug(("session user", request.session['user_id']))
    return render(request, "nba_fantasy/league_homepage.html", context)


def create_team(request, league_id):
    league = FantasyLeague.objects.get(id=league_id)
    if request.method == "POST":
        form = FantasyTeamForm(request.POST)
        if form.is_valid():
            owner = User.objects.get(id=request.session['user_id'])
            team = form.save(commit=False)
            team.owner = owner
            team.league = league
            team.win_pct = 0
            team.save()
            return redirect("nba_fantasy:league-homepage", league_id=league.id)
    else:
        form = FantasyTeamForm()

    context = {'league': league, 'form': form, 'action': 'create'}
    return render(request, "nba_fantasy/create_team.html", context)


def edit_team(request, league_id, team_id):
    league = FantasyLeague.objects.get(id=league_id)
    fantasy_team = FantasyTeam.objects.get(id=team_id)

    if request.method == "POST":
        form = FantasyTeamForm(request.POST, instance=fantasy_team)
        if form.is_valid():
            team = form.save(commit=False)
            team.league = league
            team.save()
            return redirect("nba_fantasy:league-homepage", league_id=league.id)
    else:
        form = FantasyTeamForm(instance=fantasy_team)

    context = {'league': league, 'form': form, 'action': 'edit',
               'team': fantasy_team}
    return render(request, "nba_fantasy/edit_team.html", context)


def view_team(request, team_id, year=None, month=None, day=None):
    log.debug(("FOX", int(team_id)))
    log.debug(("ELEPHANT", int(team_id) == 0))
    if int(team_id) == 0:
        log.debug("IN HERE")
        return redirect("nba_fantasy:create-team", league_id=request.session['league_id'])

    team = FantasyTeam.objects.get(id=team_id)
    score_settings = team.league.scoringsettings
    score_fields = sorted([f for f in score_settings.scoring_fields_vals],
                          key=SPLIT_FIELD_ORDERING.index)
    pending_trades = FantasyTeamTransaction.objects.filter(team=team,
                                                           expiry_time__gt=datetime.now(),
                                                           accepted_flag=False)

    if year is None and month is None and day is None:
        lup_date = date.today()
    else:
        lup_date = date(year=int(year),
                        month=int(month),
                        day=int(day))

    default_date_str = lup_date.strftime("%m/%d/%Y")
    lineup_entries = create_lineup_entry_rows(team,
                                              scoring_settings=score_settings,
                                              lineup_date=lup_date)
    context = {'team': team, 'league': team.league, 'pending_trades': pending_trades,
               'lineup_entries': lineup_entries, 'default_date_str': default_date_str,
               'score_fields': score_fields}
    return render(request, "nba_fantasy/view_team.html", context)


def draft(request, league_id):
    league = FantasyLeague.objects.get(id=league_id)
    user = User.objects.get(id=request.session['user_id'])
    ros_entries = FantasyTeamRosterEntry.objects.filter(league=league,
                                                        team=None,
                                                        end_date=None,
                                                        acquired_via="UO").values_list('player_id',
                                                                                       flat=True)
    available_players = Player.objects.filter(id__in=ros_entries)
    # Temp

    team = FantasyTeam.objects.get(league=league,
                                   owner=user)
    context = {'league': league, 'available_players': available_players, 'team': team}
    return render(request, "nba_fantasy/draft.html", context)


def free_agents(request, league_id):
    league = FantasyLeague.objects.get(id=league_id)
    user = User.objects.get(id=request.session['user_id'])
    team = FantasyTeam.objects.get(league=league,
                                   owner=user)
    ros_entries = FantasyTeamRosterEntry.objects.filter(league=league,
                                                        team=None,
                                                        end_date=None).values_list('player_id',
                                                                                   flat=True)
    fa_players = Player.objects.filter(id__in=ros_entries)
    context = {'league': league, 'fa_players': fa_players, 'team': team}
    return render(request, "nba_fantasy/free_agents.html", context)


def trade(request, league_id):
    league = FantasyLeague.objects.get(id=league_id)
    user = User.objects.get(id=request.session['user_id'])
    team = FantasyTeam.objects.get(league=league,
                                   owner=user)
    other_teams = FantasyTeam.objects.filter(league=league).exclude(owner=user)
    context = {'league': league, 'user': user,
               'team': team, 'other_teams': other_teams}
    return render(request, 'nba_fantasy/trade.html', context)


def accept_trade(request, transaction_id):
    myteam_trade = FantasyTeamTransaction.objects.get(id=transaction_id)
    all_related_trades = FantasyTeamTransaction.objects.filter(trade_identifier=
                                                               myteam_trade.trade_identifier)
    handle_accepted_trade(all_related_trades)
    context = {}
    return render(request, 'nba_fantasy/accept_trade.html', context)


def schedule(request, league_id):
    league = FantasyLeague.objects.get(id=league_id)
    team = FantasyTeam.objects.get(league=league,
                                   owner_id=request.session['user_id'])
    cur_week = (date.today() - league.season_start_date).days // 7
    # Temp for testing
    cur_week = 15
    context = {'league': league, 'team': team, 'cur_week': cur_week}
    weeks = range(league.start_week, (league.reg_season_matchups *
                                           league.weeks_per_matchup))
    context['weeks'] = []

    matchups = FantasyMatchup.objects.filter(home_team__league=league)
    for week in weeks:
        context['weeks'].append(matchups.filter(week_num=week))
    context['matchups'] = matchups

    return render(request, 'nba_fantasy/schedule.html', context)


def matchup(request, matchup_id):
    mup = FantasyMatchup.objects.get(id=matchup_id)
    mup.score_matchup()
    league = mup.home_team.league
    log.debug(("NARWHAL", SPLIT_FIELD_ORDERING))
    scoring_fields = sorted(league.scoringsettings.scoring_fields_vals.keys(),
                            key=SPLIT_FIELD_ORDERING.index)
    scoring_fields.append("total")
    display_fields = [s.split("__")[-1].upper().replace("_", " ") for s in scoring_fields]
    my_team = FantasyTeam.objects.get(league=league,
                                      owner=request.session['user_id'])

    home_entries = TeamMatchupEntries(matchup=mup,
                                      team=mup.home_team)
    home_rows = home_entries.create_rows()
    log.debug(("HOME ROWS", [(h.player_name, h.score_fields) for h in home_rows]))

    away_entries = TeamMatchupEntries(matchup=mup,
                                      team=mup.away_team)
    away_rows = away_entries.create_rows()
    log.debug(("AWAY ROWS", [(h.player_name, h.score_fields) for h in away_rows]))

    context = {'league': league, 'team': my_team, 'matchup': mup,
               'home_rows': home_rows, 'away_rows': away_rows,
               'scoring_fields': scoring_fields, 'display_fields': display_fields}
    return render(request, 'nba_fantasy/matchup.html', context)


def standings(request, league_id):
    league = FantasyLeague.objects.get(id=league_id)
    team = FantasyTeam.objects.get(owner__id=request.session['user_id'],
                                   league=league)
    standings_teams = FantasyTeam.objects.filter(league=league).order_by('-win_pct')

    context = {'league': league, 'team': team, 'team_standings': standings_teams}
    return render(request, 'nba_fantasy/standings.html', context)


# Begin AJAX calls.
def add_free_agent(request):
    league_id = request.GET.get("league_id", None)
    pid = request.GET.get("player_id", None)
    team_id = request.GET.get("fantasy_team_id", None)
    league = FantasyLeague.objects.get(id=league_id)
    fantasy_team = FantasyTeam.objects.get(id=team_id)
    player = Player.objects.get(id=pid)
    data = add_free_agent_to_team(league, fantasy_team, player)
    return JsonResponse(data)


def propose_trade(request):
    # We have league_id and a dict mapping
    # cur_team.id/player.id -> team(that the player would be sent to).id
    trade_map = json.loads(request.GET.get("players_being_traded", None))
    create_trade_proposal(trade_map)
    data = {'proposed': True}
    return JsonResponse(data)

