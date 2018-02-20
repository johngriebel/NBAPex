import logging
from nba_stats.models import (Team, Player, Game, PlayerShotChartDetail, PlayerSeason)
from nba_stats.utils import (convert_datetime_string_to_date_instance,
                             convert_height_to_int, convert_dict_keys_to_lowercase,
                             make_season_int, get_json_response, make_season_str,
                             make_unique_filter_dict)
from nba_stats.constants import (NBA_BASE_URL, PLAYER_INFO_URL, SHOTCHART_PARAMS,
                                 PLAYER_CAREER_STATS_ENDPOINT, PLAYER_CAREER_STATS_PARAMS,
                                 IGNORE_SEASON_TYPES)
log = logging.getLogger('stats')


# This should just be an instance method
def get_player_age(player, year):
    # Not correct. Doesn't account for when in the year a player's birthday is
    # TODO: Fix this
    return year - player.birthdate.year


def get_player_info_from_web(player_id):
    url = (NBA_BASE_URL + PLAYER_INFO_URL).format(player_id=str(player_id),
                                                  season_type="Regular+Season")
    log.debug("Player URL: " + url)
    data = get_json_response(url)
    # This goofy thing returns a list containing the relevant player information
    headers = data['resultSets'][0]['headers']
    info = data['resultSets'][0]['rowSet'][0]
    data_dict = dict(zip(headers, info))
    return data_dict


def sanitize_player_data(data_dict):
    # debug("data_dict: " + str(data_dict))
    log.debug("Player id = %s" % data_dict['PERSON_ID'])
    log.debug("Player name: %s" % data_dict['DISPLAY_FIRST_LAST'])
    data_dict['BIRTHDATE'] = convert_datetime_string_to_date_instance(data_dict['BIRTHDATE'])
    data_dict['HEIGHT'] = convert_height_to_int(data_dict['HEIGHT'])
    data_dict['PLAYER_ID'] = data_dict['PERSON_ID']
    if not data_dict['SCHOOL']:
        data_dict['SCHOOL'] = "N/A"
    # weight
    if not(data_dict['WEIGHT'] == '' or data_dict['WEIGHT'] == ' '):
        data_dict['WEIGHT'] = int(data_dict['WEIGHT'])
    else:
        data_dict['WEIGHT'] = 0
    # from_year
    if data_dict['FROM_YEAR'] == '' or data_dict['FROM_YEAR'] == ' ':
        data_dict['FROM_YEAR'] = 0
    # to_year
    if data_dict['TO_YEAR'] == '' or data_dict['TO_YEAR'] == ' ':
        data_dict['TO_YEAR'] = 0
    if data_dict.get("DLEAGUE_FLAG", "N").lower() == "n":
        data_dict['DLEAGUE_FLAG'] = False
    else:
        data_dict['DLEAGUE_FLAG'] = True
    return data_dict


# season_id should only be
# set if adv_flag=True, otherwise it does nothing...
def standardize_player_data(data, player=None, adv_flag=False, season_type='regular',
                            season_str="2014-15"):
    seasons_list = []
    hdrs = data['headers']
    if data['rowSet']:
        for s in data['rowSet']:
            d = dict(zip(hdrs, s))
            # log.debug(d)
            # Not sure how or why this happens, but just return the empty list and move on.s
            if d.get('PLAYER_NAME', "") is None:
                return seasons_list
            team_id = d.get('Team_ID', None)
            if team_id is None:
                team_id = d.get("TEAM_ID", None)
            team = Team.objects.get(team_id=team_id)
            if "Career" in data['name']:
                d['SEASON_ID'] = 0
                d['TEAM_ABBREVIATION'] = team.team_abbreviation
                d['CAREER_FLAG'] = True
            else:
                d['CAREER_FLAG'] = False
                # Dunno why this has to be like this...
                if d.get('SEASON_ID', None):
                    d['SEASON_ID'] = make_season_int(d['SEASON_ID'])
                else:
                    # Temporary Hack
                    d['SEASON_ID'] = make_season_int(season_str)
            if "Regular" in data['name']:
                d['SEASON_TYPE'] = "regular"
            elif "Post" in data['name']:
                d['SEASON_TYPE'] = "post"
            elif "AllStar" in data['name']:
                d['SEASON_TYPE'] = "all_star"
            d['PLAYER'] = Player.objects.get(player_id=d['PLAYER_ID'])
            if team:
                d['TEAM'] = team
            # Another temporary hack <--- Wtf was I doing here?
            # d['SEASON_TYPE'] = 'regular'
            lowercased = convert_dict_keys_to_lowercase(d)
            seasons_list.append(lowercased)
    # We now have a list of dicts that each specify a season
    return seasons_list


def create_player_from_web(player_id):
    data_dict = sanitize_player_data(get_player_info_from_web(player_id=player_id))
    # Some historical players last played for a now defunct franchise.
    team, team_created = Team.objects.get_or_create(team_id=data_dict['TEAM_ID'],
                                                    defaults={'team_id': data_dict['TEAM_ID'],
                                                              'team_name': data_dict['TEAM_NAME'],
                                                              'team_abbreviation': data_dict['TEAM_ABBREVIATION'],
                                                              'team_code': data_dict['TEAM_CODE'],
                                                              'team_city': data_dict['TEAM_CITY']})
    if team_created:
        log.debug("Created team: %s" % team)
    data_dict['TEAM'] = team
    data_dict = convert_dict_keys_to_lowercase(data_dict)
    log.debug("Attempting to create player with data_dict: \n" + str(data_dict))
    player = Player(**data_dict)
    return player


def get_player_shotchart(player, season, season_type="Regular Season"):
    params = SHOTCHART_PARAMS
    params['PlayerID'] = player.player_id
    params['Season'] = season
    params['SeasonType'] = season_type
    url = NBA_BASE_URL + 'shotchartdetail'
    # log.debug("URL: " + url)
    # log.debug("Params: \n" + str(params))
    json_data = get_json_response(url, params=params)
    # log.debug("JSON Data: \n" + str(json_data))
    relevant_data = json_data['resultSets'][0]
    return relevant_data


def create_player_shotchart_details_from_json(player, raw_json):
    headers = raw_json['headers']
    shotchart_details = []
    team = None
    game = None
    for row in raw_json['rowSet']:
        data_dict = dict(zip(headers, row))
        data_dict['PLAYER'] = player
        if team is None or data_dict['TEAM_ID'] != team.team_id:
            team = Team.objects.get(team_id=data_dict['TEAM_ID'])
            data_dict['TEAM'] = team
        if game is None or data_dict['GAME_ID'] != game.game_id:
            game = Game.objects.get(game_id=data_dict['GAME_ID'])
            data_dict['GAME'] = game
        converted_dict = convert_dict_keys_to_lowercase(data_dict, isgame=True)
        shotchart_dtl = PlayerShotChartDetail(**converted_dict)
        shotchart_details.append(shotchart_dtl)

    return shotchart_details


def create_all_shotchart_details_player(player):
    player_scdtls = []
    # I *think* it should be + 1
    for year in range(2001, player.to_year + 1):
        team = None
        for season_type in ["Regular Season", "Playoffs"]:
            season_str = make_season_str(year)
            log.debug("Season: " + season_str)
            raw_json = get_player_shotchart(player, season_str,
                                            season_type=season_type)
            # log.debug("Raw JSON: \n" + str(raw_json))
            player_scdtls += create_player_shotchart_details_from_json(player, raw_json)
    return player_scdtls


# Will eventually handle PerGame/Totals/Advanced
# Also have to add Shooting, as it seems to be a special case for whatever reason
def create_update_all_seasons_for_player(player, year=None):
    player_seasons = []
    url = NBA_BASE_URL + PLAYER_CAREER_STATS_ENDPOINT
    parms = PLAYER_CAREER_STATS_PARAMS
    parms['PlayerID'] = player.player_id
    # Removing Per36 & PerGame cut down the requests by 2/3
    per_mode = "Totals"
    parms['PerMode'] = per_mode
    json_data = get_json_response(url, params=parms)
    result_sets = json_data['resultSets']
    for rset in result_sets:
        season_type = rset['name']
        if not any(ignore in season_type for ignore in IGNORE_SEASON_TYPES):
            headers = rset['headers']
            rows = rset['rowSet']
            team = None
            for row in rows:
                data = dict(zip(headers, row))
                # log.debug("Data: " + str(data))
                dteam_key = "TEAM_ID" if "TEAM_ID" in data else "Team_ID"
                if team is None or data[dteam_key] != team.team_id:
                    try:
                        team = Team.objects.get(team_id=data[dteam_key])
                    except Exception as e:
                        log.debug(("ELEPHANT", data))
                        raise e
                conv_data = convert_dict_keys_to_lowercase(data, override_list=['LEAGUE_ID'])

                conv_data['season_id'] = make_season_int(conv_data.get('season_id', 0))
                # year=None -> update/create all seasons. Always update career.
                if year is not None and conv_data['season_id'] not in [0, year]:
                    continue

                conv_data['season_type'] = season_type
                conv_data['player'] = player

                conv_data['team'] = team
                conv_data['per_mode'] = per_mode
                # log.debug("Converted Data: " + str(conv_data))
                filters = make_unique_filter_dict(PlayerSeason, conv_data)
                season, created = PlayerSeason.objects.update_or_create(**filters,
                                                                        defaults=conv_data)
                if created:
                    log.debug(("Created a new season: ", filters))
                    player_seasons.append(season)

    return player_seasons


# THis is mostly correct, but not entirely. Mo Williams is an example of where it goes
# Wrong. IDK what to do really.
def map_players_to_bbref_str():
    players = Player.objects.all().order_by('last_name', 'first_name', 'birthdate')
    bbref_id_map = {}
    for player in players:
        log.debug((player.first_name, player.last_name))
        if player.first_name and player.last_name:
            str_found = False
            count = 1
            while not str_found:
                id_str = "{sur}{giv}{cnt}".format(sur=player.last_name[:5].lower(),
                                                  giv=player.first_name[:2].lower(),
                                                  cnt=str(count).rjust(2, '0')).replace(".", "")
                if bbref_id_map.get(id_str, None):
                    count += 1
                else:
                    bbref_id_map[id_str] = player
                    str_found = True
    for bbref_id_str, player in bbref_id_map.items():
        log.debug("%s %s" % (player, bbref_id_str))
        player.bbref_id_str = bbref_id_str
        player.save()


def get_player_seasons_context(player, fields):
    player_seasons = PlayerSeason.objects.filter(player=player)

    regular_seasons_per_game = player_seasons.filter(season_type=
                                                     "SeasonTotalsRegularSeason",
                                                     per_mode="PerGame").values_list(*fields).order_by('season_id')
    most_recent_season = player_seasons.filter(season_type="SeasonTotalsRegularSeason",
                                               per_mode="PerGame").order_by('-season_id').last()
    regular_seasons_totals = player_seasons.filter(season_type=
                                                   "SeasonTotalsRegularSeason",
                                                   per_mode="Totals").values_list(*fields).order_by(
        'season_id')
    regular_seasons_per_36 = player_seasons.filter(season_type=
                                                   "SeasonTotalsRegularSeason",
                                                   per_mode="Per36").values_list(*fields).order_by(
        'season_id')
    career_regular_pg = player_seasons.filter(season_type=
                                              "CareerTotalsRegularSeason",
                                              per_mode="PerGame").values_list(*fields).first()
    career_regular_totals = player_seasons.filter(season_type=
                                                  "CareerTotalsRegularSeason",
                                                  per_mode="Totals").values_list(*fields).first()
    career_regular_per_36 = player_seasons.filter(season_type=
                                                  "CareerTotalsRegularSeason",
                                                  per_mode="Per36").values_list(*fields).first()

    playoff_seasons = player_seasons.filter(season_type="SeasonTotalsPostSeason").values_list(
        *fields)
    playoff_per_game = playoff_seasons.filter(per_mode="PerGame").order_by('season_id')
    playoff_totals = playoff_seasons.filter(per_mode="Totals").order_by('season_id')
    playoff_per_36 = playoff_seasons.filter(per_mode="Per36").order_by('season_id')
    career_playoff = player_seasons.filter(season_type="CareerTotalsPostSeason").values_list(
        *fields)
    career_playoff_pg = career_playoff.filter(per_mode="PerGame").first()
    career_playoff_totals = career_playoff.filter(per_mode="Totals").first()
    career_playoff_per_36 = career_playoff.filter(per_mode="Per36").first()

    # Sort of silly to have PerGame/Totals/Per36 for all star but meh
    all_star_seasons = player_seasons.filter(season_type='SeasonTotalsAllStarSeason').values_list(
        *fields)
    all_star_pg = all_star_seasons.filter(per_mode="PerGame").order_by('season_id')
    all_star_totals = all_star_seasons.filter(per_mode="Totals").order_by('season_id')
    all_star_per_36 = all_star_seasons.filter(per_mode="Per36").order_by('season_id')

    career_all_star = player_seasons.filter(season_type="CareerTotalsAllStarSeason").values_list(
        *fields)
    career_all_star_pg = career_all_star.filter(per_mode="PerGame").first()
    career_all_star_totals = career_all_star.filter(per_mode="Totals").first()
    career_all_star_per_36 = career_all_star.filter(per_mode="Per36").first()

    context_seasons = {'regular_season_per_game': regular_seasons_per_game,
                       'regular_season_totals': regular_seasons_totals,
                       'regular_season_per_36': regular_seasons_per_36,
                       'career_regular_pg': career_regular_pg,
                       'career_regular_totals': career_regular_totals,
                       'career_regular_per_36': career_regular_per_36,
                       'playoff_per_game': playoff_per_game,
                       'playoff_totals': playoff_totals,
                       'playoff_per_36': playoff_per_36,
                       'career_playoff_pg': career_playoff_pg,
                       'career_playoff_totals': career_playoff_totals,
                       'career_playoff_per_36': career_playoff_per_36,
                       'all_star_pg': all_star_pg,
                       'all_star_totals': all_star_totals,
                       'all_star_per_36': all_star_per_36,
                       'career_all_star_pg': career_all_star_pg,
                       'career_all_star_totals': career_all_star_totals,
                       'career_all_star_per_36': career_all_star_per_36,
                       'cur_season': most_recent_season}
    return context_seasons


def get_player_context(player, fields):
    context = {'player': player}
    context.update(get_player_seasons_context(player, fields))

    return context
