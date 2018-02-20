import logging
import csv
import json
from collections import OrderedDict
from datetime import date
from uuid import uuid4
from django.core import serializers
from django.shortcuts import render
from django.http import HttpResponseRedirect, HttpResponse
from dicttoxml import dicttoxml
from nba_stats.models import (Player, PlayerTraditionalSplit,
                              PlayerAdvancedSplit, PlayerMiscSplit,
                              PlayerShootingSplit, PlayerUsageSplit,
                              PlayerScoringSplit, TeamTraditionalSplit,
                              TeamAdvancedSplit, TeamMiscSplit,
                              TeamShootingSplit, TeamScoringSplit,
                              Game, LineScore, PlayerSeason, Transaction,
                              Team, TeamSeason)
from nba_stats.utils import (convert_datetime_string_to_date_instance,
                             determine_season_for_date, make_season_str,
                             get_default_display_fields, get_field_literals,
                             get_user_exposed_models, get_user_exposed_model_fields)
from nba_stats.forms import GameUpdateForm, SplitSearchForm
from nba_stats.helpers.team import get_currently_active_teams, get_team_context
from nba_stats.helpers.game import get_display_data_for_line_score
from nba_stats.helpers.player import get_player_context

SPLIT_TYPE_MAP = {"PlayerTraditional": PlayerTraditionalSplit,
                  "PlayerAdvanced": PlayerAdvancedSplit,
                  "PlayerMisc": PlayerMiscSplit,
                  "PlayerShooting": PlayerShootingSplit,
                  "PlayerUsage": PlayerUsageSplit,
                  "PlayerScoring": PlayerScoringSplit,
                  "TeamTraditional": TeamTraditionalSplit,
                  "TeamAdvanced": TeamAdvancedSplit,
                  "TeamMisc": TeamMiscSplit,
                  "TeamShooting": TeamShootingSplit,
                  "TeamScoring": TeamScoringSplit}

log = logging.getLogger('stats')

DEFAULT_SPLIT_SEARCH = {'season_id': date.today().year,
                        'season_type': 'Regular Season',
                        'split_type': "Traditional",
                        'per_mode': "PerGame",
                        'group_set': "Overall"}


def index(request):
    context = {}
    return render(request, 'nba_stats/index.html', context)


def players(request):
    if request.GET:
        form = SplitSearchForm(request.GET)
        if form.is_valid():
            search = form.cleaned_data
            search['group_set'] = "Overall"
        else:
            log.debug("BORK")
            search = {}
    else:
        search = DEFAULT_SPLIT_SEARCH

        form = SplitSearchForm()

    model = SPLIT_TYPE_MAP["Player" + search['split_type']]
    log.debug(("ARAMDILLO", model))
    # TODO: Make all these field selections dynamically selectable for the user as well.
    fields = get_default_display_fields(model, exclude=["plus_minus", "dd2", "td3"])
    header_labels = ["Player"] + get_field_literals(fields)
    all_fields = ['player__display_first_last'] + fields
    order_by = search.get('order_by') or "-" + all_fields[-1]

    log.debug(("BADGER", search))

    raw_seasons = model.objects.filter(season_id=int(search['season_id']),
                                       season_type=search['season_type'],
                                       per_mode=search['per_mode'],
                                       group_set=search['group_set'])
    log.debug(("CHEETAH", raw_seasons.count()))
    id_list = raw_seasons.values_list('player__id', flat=True).order_by(order_by)
    seasons = raw_seasons.values_list(*all_fields).order_by(order_by)

    context = {'header_labels': header_labels, 'seasons': seasons,
               'form': form, 'id_list': id_list}
    return render(request, 'nba_stats/players.html', context)


def player(request, id):
    plr = Player.objects.get(id=id)
    last_transaction = Transaction.objects.filter(player=plr).order_by('-transaction_date').first()
    # TODO: This is a scenario where REST API may be helpful
    serialized = json.loads(serializers.serialize('json', [plr]))[0]
    player_json = serialized['fields']
    player_json['id'] = plr.id
    player_json = json.dumps(player_json)
    display_field_info = get_user_exposed_model_fields(PlayerSeason,
                                                       translation_style="upper",
                                                       exclude=["season_type", "team", "per_mode",
                                                                "player", "player_name",
                                                                "league_id"])
    season_headers = [info['display_value'] for info in display_field_info]
    fields = [info['field_name'] for info in display_field_info]
    context = get_player_context(plr, fields)
    context['headers'] = season_headers
    context['player_json'] = player_json
    context['last_transaction'] = last_transaction
    return render(request, "nba_stats/player.html", context)


def teams(request):
    if request.GET:
        form = SplitSearchForm(request.GET)
        if form.is_valid():
            search = form.cleaned_data
            search['group_set'] = "Overall"
        else:
            log.debug("BORK")
            search = {}
    else:
        search = DEFAULT_SPLIT_SEARCH

        form = SplitSearchForm()

    model = SPLIT_TYPE_MAP["Team" + search['split_type']]
    # TODO: Make all these field selections dynamically selectable for the user as well.
    fields = get_default_display_fields(model, exclude=["plus_minus", "dd2", "td3"])
    header_labels = ["Team"] + get_field_literals(fields)
    all_fields = ['team__abbreviation'] + fields
    order_by = search.get('order_by') or "-" + all_fields[-1]

    raw_seasons = model.objects.filter(season_id=int(search['season_id']),
                                       season_type=search['season_type'],
                                       per_mode=search['per_mode'],
                                       group_set=search['group_set'])
    id_list = raw_seasons.values_list('team__id', flat=True).order_by(order_by)
    seasons = raw_seasons.values_list(*all_fields).order_by(order_by)
    context = {'header_labels': header_labels,
               'seasons': seasons, 'form': form,
               'id_list': id_list}
    return render(request, 'nba_stats/teams.html', context)


def team(request, id):
    requested_team = Team.objects.get(id=id)
    serialized = json.loads(serializers.serialize('json', [requested_team]))[0]
    team_json = serialized['fields']
    team_json['id'] = requested_team.id
    team_json['from_year'] = 1996
    team_json['to_year'] = 2016
    team_json = json.dumps(team_json)
    display_field_info = get_user_exposed_model_fields(TeamSeason,
                                                       translation_style="upper",
                                                       exclude=["season_type", "team", "per_mode",
                                                                "league_id", "team_abbreviation",
                                                                "team_city", "team_name",
                                                                "conf_count", "div_count"])
    season_headers = [info['display_value'] for info in display_field_info]
    fields = [info['field_name'] for info in display_field_info]
    log.debug(("FIELDS", fields))
    context = {'team': requested_team,
               'headers': season_headers,
               'team_json': team_json}

    context.update(get_team_context(requested_team, fields))
    return render(request, 'nba_stats/team.html', context)


def games(request, year=None, month=None, day=None):
    if any([year, month, day]) and not all([year, month, day]):
        log.debug("I'm not sure how the hell we got here, but things are all borked up.")
        log.debug(("year, month, day ", year, month, day))
        raise Exception("Bork")
    elif not any([year, month, day]):
        the_date = date.today()
    else:
        the_date = date(year=int(year), month=int(month), day=int(day))

    todays_games = Game.objects.filter(game_date_est=the_date)
    line_scores = LineScore.objects.filter(game__in=todays_games)
    ls_dict = {ls.team.id: get_display_data_for_line_score(ls) for ls in line_scores}
    context = {'games': todays_games, 'line_scores': ls_dict}
    return render(request, 'nba_stats/games.html', context)


def admin_portal(request):
    if request.method == "POST":
        form = GameUpdateForm(request.POST)
        if form.is_valid():
            log.debug(request.POST)
            begin_date_str = request.POST['begin_date']
            end_date_str = request.POST['end_date']
            begin_date = convert_datetime_string_to_date_instance(begin_date_str)
            end_date = convert_datetime_string_to_date_instance(end_date_str)
            log.debug(("Dates", begin_date, end_date))
            return HttpResponseRedirect("")
    else:
        form = GameUpdateForm()

    context = {'form': form}
    return render(request, "nba_stats/admin_portal.html", context)


def shot_chart(request):
    active_players = Player.active_players.all()
    cur_year = determine_season_for_date(date.today())
    seasons = {}
    for year in range(2001, cur_year + 1):
        seasons[year] = make_season_str(year)
    context = {'players': active_players, 'seasons': seasons}
    return render(request, "nba_stats/shot_chart.html", context)


def roster_history(request):
    active_teams = get_currently_active_teams()
    context = {'teams': active_teams}
    return render(request, "nba_stats/roster_history.html", context)


def user_query(request):
    exposed_models = [model.__name__ for model in get_user_exposed_models()]
    context = {'models': exposed_models}
    return render(request, 'nba_stats/user_query.html', context)


def download_user_query_results(request, fmt):
    log.debug("In download user query results call")
    request_data = json.loads(request.session.get('user_query_data'),
                              object_pairs_hook=OrderedDict)
    log.debug(request_data)
    response = HttpResponse(content_type='text/' + fmt)

    if fmt == "csv":
        writer = csv.writer(response)
        for row in request_data:
            log.debug(row.values())
            writer.writerow([str(x) for x in row.values()])
    elif fmt == "json":
        response.write(request_data)
    elif fmt == "xml":
        xml = dicttoxml(request_data)
        response.write(xml)

    filename = "nba-stats-qry-download" + str(uuid4()) + "." + fmt
    response['Content-Disposition'] = 'attachment; filename="{fn}"'.format(fn=filename)

    return response
