import logging
from datetime import date
from nba_stats.models import (Team, TeamSeason, Player, TeamHof,
                              TeamHistory, TeamRetired, PlayerTeamRosterXref,
                              TeamAward, Coach)
from nba_stats.utils import (convert_dict_keys_to_lowercase, get_json_response,
                             dictify, make_season_int, make_unique_filter_dict)
from nba_stats.constants import (NBA_BASE_URL, TEAM_INFO_BASE_URL,
                                 TEAM_SEASONS_ENDPOINT, TEAM_SEASONS_PARMS, PER_MODES)
log = logging.getLogger('stats')


def intify_arena_capacity(capacity):
    capacity = capacity.replace(",", "")
    retval = int(capacity) if capacity else 0
    return retval


def standardize_team_data(data, season_type, year):
    seasons_list = []
    try:
        hdrs = data.get('headers', None) or data['resultSets'][0]['headers']
        rows = data.get('rowSet', None) or data['resultSets'][0]['rowSet']
        if rows:
            for s in rows:
                d = dict(zip(hdrs, s))
                d['SEASON_TYPE'] = season_type
                d['SEASON_ID'] = year
                d['TEAM'] = Team.objects.get(team_id=d['TEAM_ID'])
                seasons_list.append(convert_dict_keys_to_lowercase(d))
    except Exception as e:
        log.debug("Exception: " + str(e))
        log.debug("Data that resulted in exception:\n" + str(data))
        raise e
    return seasons_list


def get_team_info_from_web(team_id):
    # season should probably be passed or derived from current date
    url = NBA_BASE_URL + TEAM_INFO_BASE_URL.format(id=str(team_id), season="2016-17")
    log.debug("Team URL: " + url)
    data = get_json_response(url)
    headers = data['resultSets'][0]['headers']
    info = data['resultSets'][0]['rowSet'][0]
    data_dict = dict(zip(headers, info))
    return data_dict


def create_team_from_web(team_id):
    # TODO: Unnest this method call. Blech
    data_dict = convert_dict_keys_to_lowercase(get_team_info_from_web(team_id=team_id),
                                               override_list=['TEAM_ID'])
    log.info(data_dict)
    team = Team(**data_dict)
    log.debug("Team to create: %s %s %s" % (team.team_id, team.city, team.name))
    team.save()


def process_team_season_json(team, jdata, season):
    season_dicts = dictify(jdata['resultSets'][0])
    for sdict in season_dicts:
        sdict['SEASON_ID'] = make_season_int(sdict['YEAR'])
        if sdict['SEASON_ID'] == season.year:
            log.debug(sdict['YEAR'])
            sdict['SEASON'] = season
            sdict['W'] = sdict['WINS']
            sdict['L'] = sdict['LOSSES']
            sdict['W_PCT'] = sdict['WIN_PCT']
            sdict['PLAYOFF_WINS'] = sdict['PO_WINS']
            sdict['PLAYOFF_LOSSES'] = sdict['PO_LOSSES']
            sdict['NBA_FINALS_APPEARANCE'] = (sdict['NBA_FINALS_APPEARANCE'] != "N/A")
            sdict['TEAM'] = team
            sdict['SEASON_TYPE'] = jdata['parameters']['SeasonType']
            sdict['PER_MODE'] = jdata['parameters']['PerMode']
            sdict = convert_dict_keys_to_lowercase(sdict, override_list=["CONF_RANK", "DIV_RANK",
                                                                         "W", "L"],
                                                   aux_list=["YEAR", "WINS", "LOSSES", "WIN_PCT",
                                                             "PO_WINS", "PO_LOSSES"])

            filter_dict = make_unique_filter_dict(TeamSeason, sdict)
            season, created = TeamSeason.objects.update_or_create(**filter_dict, defaults=sdict)
            if created:
                log.debug(("Created team season ", filter_dict))


def create_update_team_seasons(team, season):
    log.debug("Seeding Team Seasons")
    # I am sure there are others we need to exclude
    url = NBA_BASE_URL + TEAM_SEASONS_ENDPOINT
    parms = TEAM_SEASONS_PARMS
    log.debug(team.city + " " + team.name)
    parms['TeamID'] = team.team_id
    # TODO: Something weird is going on with playoffs
    # We're getting the exact same stats as reg season, even though I checked the request &
    # It seems correct. When I look via browser, the stats seem to be correct.
    for season_type in ["Regular Season", "Playoffs"]:
        log.debug(season_type)
        parms['SeasonType'] = season_type
        for permode in ["PerGame", "Totals"]:
            log.debug(permode)
            parms['PerMode'] = permode
            try:
                json_data = get_json_response(url, params=parms)
            except Exception as e:
                log.debug(("PARMS ", parms))
                log.debug(("URL ", url))
                log.exception(e)
                raise e
            process_team_season_json(team, json_data, season)


def populate_new_team_data(team, raw_json):
    log.debug("Populating new team data")
    log.debug(raw_json)
    if len(raw_json[0]['rowSet']):
        team_background = dict(zip(raw_json[0]['headers'], raw_json[0]['rowSet'][0]))
        team.arena = team_background['ARENA']
        team.arena_capacity = intify_arena_capacity(team_background['ARENACAPACITY'])
        team.owner = team_background['OWNER']
        team.general_manager = team_background['GENERALMANAGER']
        coach = Coach.objects.filter(display_first_last=team_background['HEADCOACH']).first()
        team.head_coach = coach
        team.d_league_affiliation = team_background['DLEAGUEAFFILIATION']
        team.save()


def create_misc_team_history_info(team, result_sets):
    obj_dict = {'histories': [], 'awards': [], 'hofs': [], 'retired': []}
    team_histories = dictify(result_sets[1])
    log.debug(team_histories)
    team_awards = []
    for rs in result_sets[3:6]:
        team_awards += dictify(rs, include_name=True)
    team_hofs = dictify(result_sets[6])
    team_retired = dictify(result_sets[7])

    log.debug("Creating TeamHistory objects")
    for th in team_histories:
        tm_hist = TeamHistory(team=team, city=th['CITY'], name=th['NICKNAME'],
                              year_founded=th['YEARFOUNDED'], active_thru=th['YEARACTIVETILL'])
        obj_dict['histories'].append(tm_hist)

    log.debug("Creating TeamAward Objects")
    for ta in team_awards:
        tm_award = TeamAward(team=team, award_type=ta['name'],
                             year_awarded=ta['YEARAWARDED'], opposite_team=ta['OPPOSITETEAM'])
        obj_dict['awards'].append(tm_award)

    log.debug("Creating TeamHofs")
    for hof in team_hofs:
        # I am positive this will blow up at some point
        player = Player.objects.get(player_id=hof['PLAYERID'])
        tm_hof = TeamHof(team=team, position=hof['POSITION'], player=player,
                         seasons_with_team=hof['SEASONSWITHTEAM'], year_elected=hof['YEAR'])
        obj_dict['hofs'].append(tm_hof)

    log.debug("Creating TeamRetired")
    for ret in team_retired:
        if ret['PLAYERID'] is None:
            player = None
        else:
            player = Player.objects.get(player_id=ret['PLAYERID'])

        tm_ret = TeamRetired(player=player, player_name=ret['PLAYER'], position=ret['POSITION'],
                             seasons_with_team=ret['SEASONSWITHTEAM'], year_retired=ret['YEAR'],
                             jersey=ret['JERSEY'])
        obj_dict['retired'].append(tm_ret)

    return obj_dict


def create_team_roster_xrefs(team, result_sets):
    xrefs = []
    common_team_roster = dictify(result_sets[0])
    log.debug("num of players " + str(len(common_team_roster)))
    coaches = dictify(result_sets[1])

    for plr in common_team_roster:
        player = Player.objects.filter(player_id=plr['PLAYER_ID']).first()
        if player is None:
            log.debug("Missing player: {id}/{name}".format(id=plr['PLAYER_ID'],
                                                           name=plr['PLAYER']))
            continue
        plr_xref = PlayerTeamRosterXref(team=team, player=player,
                                        season_id=int(plr['SEASON']),
                                        number=plr['NUM'])
        xrefs.append(plr_xref)

    return xrefs


def get_currently_active_teams():
    from nba_stats.models import TeamHistory, Team
    this_year = date.today().year
    tids = TeamHistory.objects.filter(active_thru=this_year - 1).values_list('team_id',
                                                                             flat=True).distinct()
    abbrevs = ["TOT", "EST", "WST"]
    teams = Team.objects.filter(id__in=tids).exclude(abbreviation__in=abbrevs).order_by('id')
    return teams


def get_team_context(team, fields):
    team_seasons = TeamSeason.objects.filter(team=team)
    regular_season_pg = team_seasons.filter(season_type="Regular Season",
                                            per_mode="PerGame").order_by('-season_id')
    most_recent_season = regular_season_pg.first()
    regular_season_pg = regular_season_pg.values_list(*fields)
    regular_season_totals = team_seasons.filter(season_type="Regular Season",
                                                per_mode="Totals").order_by('-season_id').values_list(*fields)
    playoff_pg = team_seasons.filter(season_type="Playoffs",
                                     per_mode="PerGame").order_by('-season_id').values_list(*fields)
    playoff_totals = team_seasons.filter(season_type="Playoffs",
                                         per_mode="Totals").order_by('-season_id').values_list(*fields)

    context = {'cur_season': most_recent_season,
               'regular_season_pg': regular_season_pg,
               'regular_season_totals': regular_season_totals,
               'playoff_pg': playoff_pg,
               'playoff_totals': playoff_totals}
    return context
