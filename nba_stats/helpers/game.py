import logging
from nba_stats.models import (PlayerTraditionalBoxScore, PlayerAdvancedBoxScore, PlayerMiscBoxScore,
                              PlayerScoringBoxScore, PlayerUsageBoxScore, PlayerTrackingBoxScore,
                              PlayerFourFactorsBoxScore, PlayerHustleStatsBoxScore,
                              TeamTraditionalBoxScore, TeamAdvancedBoxScore, TeamMiscBoxScore,
                              TeamScoringBoxScore, TeamUsageBoxScore, TeamTrackingBoxScore,
                              TeamFourFactorsBoxScore, TeamHustleStatsBoxScore, Player, Team,
                              Game, GameOfficialXref, GameOtherStats, PlayByPlayEvent,
                              LineScore, Official)
from nba_stats.utils import (get_json_response, convert_min_sec_to_float,
                             convert_dict_keys_to_lowercase, make_season_str,
                             convert_datetime_string_to_date_instance,
                             convert_colon_tstamp_to_duration)
from nba_stats.constants import (NBA_BASE_URL, TRADITIONAL_BOX_URL, ADVANCED_BOX_URL,
                                 MISC_BOX_URL, SCORING_BOX_URL, USAGE_BOX_URL, PLAYER_TRACK_BOX_URL,
                                 FOUR_FACTORS_BOX_URL, HUSTLE_STATS_BOX_URL, PBP_URL, SUMMARY_URL)
log = logging.getLogger('stats')


def create_correct_type_of_player_box_score(p_box_data, box_type):
    if box_type == 'Traditional':
        return PlayerTraditionalBoxScore(**p_box_data)
    elif box_type == 'Advanced':
        return PlayerAdvancedBoxScore(**p_box_data)
    elif box_type == 'Misc':
        return PlayerMiscBoxScore(**p_box_data)
    elif box_type == 'Scoring':
        return PlayerScoringBoxScore(**p_box_data)
    elif box_type == 'Usage':
        return PlayerUsageBoxScore(**p_box_data)
    elif box_type == 'Tracking':
        return PlayerTrackingBoxScore(**p_box_data)
    elif box_type == 'FourFactors':
        return PlayerFourFactorsBoxScore(**p_box_data)
    elif box_type == 'Hustle':
        return PlayerHustleStatsBoxScore(**p_box_data)


def create_correct_type_of_team_box_score(t_box_data, box_type):
    if box_type == 'Traditional':
        return TeamTraditionalBoxScore(**t_box_data)
    elif box_type == 'Advanced':
        return TeamAdvancedBoxScore(**t_box_data)
    elif box_type == 'Misc':
        return TeamMiscBoxScore(**t_box_data)
    elif box_type == 'Scoring':
        return TeamScoringBoxScore(**t_box_data)
    elif box_type == 'Usage':
        return TeamUsageBoxScore(**t_box_data)
    elif box_type == 'Tracking':
        return TeamTrackingBoxScore(**t_box_data)
    elif box_type == 'FourFactors':
        return TeamFourFactorsBoxScore(**t_box_data)
    elif box_type == 'Hustle':
        return TeamHustleStatsBoxScore(**t_box_data)


def create_box_scores_for_game(game, url_suffix, season_type="Regular+Season",
                               box_type="Traditional"):

    player_box_scores = []
    team_box_scores = []

    url = (NBA_BASE_URL + url_suffix).format(game_id=game.game_id,
                                             season=make_season_str(game.season),
                                             season_type=season_type)
    data = get_json_response(url)
    if box_type == "Hustle":
        hustle_status = data['resultSets'][0]['rowSet'][0][1]
        if not hustle_status:
            player_stats = None
        else:
            player_stats = data['resultSets'][1]
    else:
        player_stats = data['resultSets'][0]

    if player_stats:
        player_headers = player_stats['headers']

        if box_type == "Hustle":
            team_stats = data['resultSets'][2]
        else:
            team_stats = data['resultSets'][1]

        team_headers = team_stats['headers']

        for p in player_stats['rowSet']:
            temp_dict = dict(zip(player_headers, p))

            temp_dict['GAME'] = game
            temp_dict['TEAM'] = Team.objects.filter(team_id=temp_dict['TEAM_ID']).first()

            player = Player.objects.filter(player_id=temp_dict['PLAYER_ID']).first()
            if not player:
                # TODO: Properly handle the situation where the given player doesn't exist yet
                log.debug("Player id and name about to look up: %s %s" % (temp_dict['PLAYER_ID'],
                                                                          temp_dict['PLAYER_NAME']))
                # Laziest possible player creation...
                # should probably write a script that goes through the db and
                # attempts to fill in missing player data

                player = Player(display_first_last=temp_dict['PLAYER_NAME'],
                                player_id=temp_dict['PLAYER_ID'],
                                team=temp_dict['TEAM'])
                player.save()
            temp_dict['PLAYER'] = player

            if box_type == "Tracking":
                converted_dict = convert_tracking_dict_to_nbapex_fields(temp_dict,
                                                                        player_flg=True)
            else:
                converted_dict = temp_dict
            p_box_data = convert_dict_keys_to_lowercase(converted_dict)

            if box_type == 'Hustle':
                p_box_data['minutes'] = convert_min_sec_to_float(p_box_data['minutes'])
            else:
                p_box_data['min'] = convert_min_sec_to_float(p_box_data['min'])

            pbox = create_correct_type_of_player_box_score(p_box_data, box_type)
            player_box_scores.append(pbox)

        for t in team_stats['rowSet']:
            temp_dict = dict(zip(team_headers, t))
            temp_dict['GAME'] = game
            temp_dict['TEAM'] = Team.objects.filter(team_id=temp_dict['TEAM_ID']).first()

            if box_type == 'Tracking':
                converted_dict = convert_tracking_dict_to_nbapex_fields(temp_dict,
                                                                        player_flg=False)
            else:
                converted_dict = temp_dict
            t_box_data = convert_dict_keys_to_lowercase(converted_dict)

            if box_type == "Hustle":
                t_box_data['minutes'] = convert_min_sec_to_float(t_box_data['minutes'])
            else:
                t_box_data['min'] = convert_min_sec_to_float(t_box_data['min'])

            tbox = create_correct_type_of_team_box_score(t_box_data, box_type)
            team_box_scores.append(tbox)
    else:
        log.debug("Box scores of type {bt} not available for game {gm}".format(bt=box_type,
                                                                               gm=game.game_id))

    ret_dict = {'players': player_box_scores, 'teams': team_box_scores}
    return ret_dict


def handle_bulk_create_box_scores(games):
    # Box scores are accessed: ['<type>']['<player>/<team>']
    # Type can be: 'traditional', 'advanced', 'misc', 'scoring', 'usage'
    #              'tracking', 'four', 'hustle'

    plr_trad = []
    team_trad = []
    plr_adv = []
    team_adv = []
    plr_misc = []
    team_misc = []
    plr_scoring = []
    team_scoring = []
    plr_usg = []
    team_usg = []
    plr_tracking = []
    team_tracking = []
    plr_four_factors = []
    team_four_factors = []
    plr_hustle = []
    team_hustle = []

    for box_scores_dict in games:
        plr_trad += box_scores_dict['traditional']['players']
        team_trad += box_scores_dict['traditional']['teams']
        plr_adv += box_scores_dict['advanced']['players']
        team_adv += box_scores_dict['advanced']['teams']
        plr_misc += box_scores_dict['misc']['players']
        team_misc += box_scores_dict['misc']['teams']
        plr_scoring += box_scores_dict['scoring']['players']
        team_scoring += box_scores_dict['scoring']['teams']
        plr_usg += box_scores_dict['usage']['players']
        team_usg += box_scores_dict['usage']['teams']
        plr_tracking += box_scores_dict['tracking']['players']
        team_tracking += box_scores_dict['tracking']['teams']
        plr_four_factors += box_scores_dict['four']['players']
        team_four_factors += box_scores_dict['four']['teams']
        plr_hustle += box_scores_dict['hustle']['players']
        team_hustle += box_scores_dict['hustle']['teams']

    log.debug("Creating Traditional Box Scores")
    PlayerTraditionalBoxScore.objects.bulk_create(plr_trad)
    TeamTraditionalBoxScore.objects.bulk_create(team_trad)
    log.debug("Creating Advanced Box Scores")
    PlayerAdvancedBoxScore.objects.bulk_create(plr_adv)
    TeamAdvancedBoxScore.objects.bulk_create(team_adv)
    log.debug("Creating Misc Box Scores")
    PlayerMiscBoxScore.objects.bulk_create(plr_misc)
    TeamMiscBoxScore.objects.bulk_create(team_misc)
    log.debug("Creating Scoring Box Scores")
    PlayerScoringBoxScore.objects.bulk_create(plr_scoring)
    TeamScoringBoxScore.objects.bulk_create(team_scoring)
    log.debug("Creating Usage Box Scores")
    PlayerUsageBoxScore.objects.bulk_create(plr_usg)
    TeamUsageBoxScore.objects.bulk_create(team_usg)
    log.debug("Creating Tracking Box Scores")
    PlayerTrackingBoxScore.objects.bulk_create(plr_tracking)
    TeamTrackingBoxScore.objects.bulk_create(team_tracking)
    log.debug("Creating Four Factors Box Scores")
    PlayerFourFactorsBoxScore.objects.bulk_create(plr_four_factors)
    TeamFourFactorsBoxScore.objects.bulk_create(team_four_factors)
    log.debug("Creating Hustle Box Scores")
    PlayerHustleStatsBoxScore.objects.bulk_create(plr_hustle)
    TeamHustleStatsBoxScore.objects.bulk_create(team_hustle)


def convert_tracking_dict_to_nbapex_fields(data_dict, player_flg=True):
    # Using all caps dict key for the sake of consistency;
    # we'll just run this converted dict through the lowercaser anyhow
    converted_dict = {}
    copy_fields = ['GAME', 'TEAM_ID', 'TEAM_ABBREVIATION', 'TEAM_CITY',
                   'MIN', 'DFGM', 'DFGA', 'DFG_PCT']
    if player_flg:
        copy_fields += ['PLAYER_ID', 'PLAYER_NAME', 'START_POSITION', 'COMMENT']
        converted_dict['SPEED'] = data_dict['SPD']
    for k in copy_fields:
        converted_dict[k] = data_dict[k]

    converted_dict['DISTANCE'] = data_dict['DIST']
    converted_dict['OREB_CHANCES'] = data_dict['ORBC']
    converted_dict['DREB_CHANCES'] = data_dict['DRBC']
    converted_dict['REB_CHANCES'] = data_dict['RBC']
    converted_dict['TOUCHES'] = data_dict['TCHS']
    converted_dict['SECONDARY_AST'] = data_dict['SAST']
    converted_dict['FT_AST'] = data_dict['FTAST']
    converted_dict['PASSES'] = data_dict['PASS']
    converted_dict['CONTESTED_FGM'] = data_dict['CFGM']
    converted_dict['CONTESTED_FGA'] = data_dict['CFGA']
    converted_dict['CONTESTED_FGPCT'] = data_dict['CFG_PCT']
    converted_dict['UNCONTESTED_FGM'] = data_dict['UFGM']
    converted_dict['UNCONTESTED_FGA'] = data_dict['UFGA']
    converted_dict['UNCONTESTED_FGPCT'] = data_dict['UFG_PCT']

    return converted_dict


def create_all_box_scores_for_game(game):
    log.debug("Begin creating box scores for game " + str(game.game_id))
    # for season_type in ['PreSeason', 'Regular+Season', 'Playoffs']:
    # It seems that it doesn't matter what season_type gets passed,
    # it will pick up the data regardless

    season_type = "Regular+Season"
    trad_box_scores = create_box_scores_for_game(game, TRADITIONAL_BOX_URL,
                                                 season_type, "Traditional")
    adv_box_scores = create_box_scores_for_game(game, ADVANCED_BOX_URL, season_type, "Advanced")
    misc_box_scores = create_box_scores_for_game(game, MISC_BOX_URL, season_type, "Misc")
    scoring_box_scores = create_box_scores_for_game(game, SCORING_BOX_URL, season_type, "Scoring")
    usg_box_scores = create_box_scores_for_game(game, USAGE_BOX_URL, season_type, "Usage")
    tracking_box_scores = create_box_scores_for_game(game, PLAYER_TRACK_BOX_URL,
                                                     season_type, "Tracking")
    four_factors_box_scores = create_box_scores_for_game(game, FOUR_FACTORS_BOX_URL,
                                                         season_type, "FourFactors")
    hustle_box_scores = create_box_scores_for_game(game, HUSTLE_STATS_BOX_URL,
                                                   season_type, "Hustle")

    ret_dict = {'traditional': trad_box_scores, 'advanced': adv_box_scores,
                'misc': misc_box_scores, 'scoring': scoring_box_scores,
                'usage': usg_box_scores, 'tracking': tracking_box_scores,
                'four': four_factors_box_scores, 'hustle': hustle_box_scores}
    return ret_dict


def create_play_by_play_for_game(game):
    log.debug("Creating Play By Play Events for Game " + str(game.game_id))
    pbp_events = []
    url = (NBA_BASE_URL + PBP_URL).format(game_id=game.game_id, season=make_season_str(game.season),
                                          season_type='foo')
    json_data = get_json_response(url)
    pbp_data = json_data['resultSets'][0]
    headers = pbp_data['headers']
    for pbp_event in pbp_data['rowSet']:
        temp_dict = dict(zip(headers, pbp_event))
        temp_dict['GAME'] = game
        # TODO: Write a method that will look for a player and if it doesn't find, creates it.
        # TODO: The method should then return the player object

        if temp_dict['PLAYER1_NAME']:
            player1 = Player.objects.filter(player_id=temp_dict['PLAYER1_ID']).first()
            if not player1:
                player1 = Player(player_id=temp_dict['PLAYER1_ID'], display_first_last=temp_dict['PLAYER1_NAME'])
                player1.save()
            temp_dict['PLAYER1'] = player1
        if temp_dict['PLAYER1_TEAM_ID']:
            temp_dict['PLAYER1_TEAM'] = Team.objects.filter(team_id=temp_dict['PLAYER1_TEAM_ID']).first()

        if temp_dict['PLAYER2_NAME']:
            player2 = Player.objects.filter(player_id=temp_dict['PLAYER2_ID']).first()
            if not player2:
                player2 = Player(player_id=temp_dict['PLAYER2_ID'], display_first_last=temp_dict['PLAYER2_NAME'])
                player2.save()
            temp_dict['PLAYER2'] = player2
        if temp_dict['PLAYER2_TEAM_ID']:
            temp_dict['PLAYER2_TEAM'] = Team.objects.filter(team_id=temp_dict['PLAYER2_TEAM_ID']).first()

        if temp_dict['PLAYER3_NAME']:
            player3 = Player.objects.filter(player_id=temp_dict['PLAYER3_ID']).first()
            if not player3:
                player3 = Player(player_id=temp_dict['PLAYER3_ID'], display_first_last=temp_dict['PLAYER1_NAME'])
                player3.save()
            temp_dict['PLAYER3'] = player3
        if temp_dict['PLAYER3_TEAM_ID']:
            temp_dict['PLAYER3_TEAM'] = Team.objects.filter(team_id=temp_dict['PLAYER3_TEAM_ID']).first()

        if temp_dict['SCOREMARGIN'] == 'TIE':
            temp_dict['SCOREMARGIN'] = 0

        pbp_create_data = convert_dict_keys_to_lowercase(temp_dict)
        pbp_obj = PlayByPlayEvent(**pbp_create_data)
        pbp_events.append(pbp_obj)
    return pbp_events


def create_line_scores_for_game(game, line_score_data):
    line_scores = []
    headers = line_score_data['headers']
    details = line_score_data['rowSet']

    for line_score in details:
        line_score[0] = convert_datetime_string_to_date_instance(line_score[0])
        temp_dict = dict(zip(headers, line_score))
        temp_dict['TEAM'] = Team.objects.get(team_id=temp_dict['TEAM_ID'])
        temp_dict['GAME'] = game
        ls_data = convert_dict_keys_to_lowercase(temp_dict)
        ls = LineScore(**ls_data)
        line_scores.append(ls)

    return line_scores


def create_other_stats_for_game(game, other_stats_data):
    log.debug("Creating OtherStats for game {g}".format(g=game.game_id))
    other_stats = []
    headers = other_stats_data['headers']
    rows = other_stats_data['rowSet']

    for row in rows:
        temp_dict = dict(zip(headers, row))
        temp_dict['GAME'] = game
        temp_dict['TEAM'] = (game.home_team if temp_dict['TEAM_ID'] == game.home_team.team_id
                                            else game.visitor_team)
        temp_dict['PTS_SECOND_CHANCE'] = temp_dict['PTS_2ND_CHANCE']
        ostats_data = convert_dict_keys_to_lowercase(temp_dict)
        ostats = GameOtherStats(**ostats_data)
        other_stats.append(ostats)

    return other_stats


def create_game_official_xrefs(game, officials_data):
    log.debug("Creating OfficialXrefs for game {g}".format(g=game.game_id))
    xrefs = []
    headers = officials_data['headers']
    rows = officials_data['rowSet']

    for row in rows:
        temp_dict = dict(zip(headers, row))
        ofc_data = convert_dict_keys_to_lowercase(temp_dict)
        official, created = Official.objects.get_or_create(official_id=ofc_data['official_id'],
                                                           defaults=ofc_data)
        if created:
            log.debug("Created a new official: {ofc}".format(ofc=str(official)))

        xref = GameOfficialXref(game=game, official=official)
        xrefs.append(xref)

    return xrefs


def create_games(game_info):
    headers = game_info['resultSets'][0]['headers']
    list_game_info = game_info['resultSets'][0]['rowSet']
    games = []
    line_scores = []
    all_box_scores = []
    pbp_events = []
    other_stats = []
    official_xrefs = []
    for info in list_game_info:
        info[0] = convert_datetime_string_to_date_instance(info[0])
        temp_dict = dict(zip(headers, info))
        existing_game = Game.objects.filter(game_id=temp_dict['GAME_ID'])

        if existing_game.exists():
            log.debug("Game {game} already exists!".format(game=existing_game.first()))
            log.debug("Avoided creating a new one. Moving on...")

        else:
            temp_dict['HOME_TEAM'] = Team.objects.get(team_id=temp_dict['HOME_TEAM_ID'])
            temp_dict['VISITOR_TEAM'] = Team.objects.get(team_id=temp_dict['VISITOR_TEAM_ID'])

            url = (NBA_BASE_URL + SUMMARY_URL).format(game_id=temp_dict['GAME_ID'])
            ancillary_game_data = get_json_response(url)
            ancillary_game_data = ancillary_game_data['resultSets']

            # TODO: I'm sure we are going to get index OOB Exception here at some point.
            other_stats_data = ancillary_game_data[1]
            officials_data = ancillary_game_data[2]
            game_info_data = dict(zip(ancillary_game_data[4]['headers'],
                                      ancillary_game_data[4]['rowSet'][0]))
            line_score_data = ancillary_game_data[5]

            temp_dict['ATTENDANCE'] = game_info_data['ATTENDANCE']
            temp_dict['GAME_TIME'] = convert_colon_tstamp_to_duration(game_info_data['GAME_TIME'])
            game_data = convert_dict_keys_to_lowercase(temp_dict, isgame=True)
            game = Game(**game_data)
            # Have to save the game now so that other object that reference can point to its id.
            # I'd like to find a way around this, but for now I don't know of one.
            game.save()
            games.append(game)
            line_scores += create_line_scores_for_game(game, line_score_data)
            # This is a dict of dicts containing a dictionary for each type of box score.
            # Each of those 5 dicts contains team and player box scores.
            all_box_scores_dict = create_all_box_scores_for_game(game)
            all_box_scores.append(all_box_scores_dict)
            pbp_events += create_play_by_play_for_game(game)
            other_stats += create_other_stats_for_game(game, other_stats_data)
            official_xrefs += create_game_official_xrefs(game, officials_data)

    ret_dict = {'games': games, 'line_scores': line_scores,
                'box_scores': all_box_scores, 'pbp_events': pbp_events,
                'other_stats': other_stats, 'official_xrefs': official_xrefs}
    return ret_dict


def instantiate_correct_boxscore_type(data, btype):
    from nba_stats import models as nba_stats_models
    if "player" in data:
        entity = "Player"
    else:
        entity = "Team"

    if btype == "Hustle":
        btype += "Stats"
    class_name = entity + btype + "BoxScore"
    class_name = class_name.replace(" ", "")
    model = getattr(nba_stats_models, class_name)
    final_data = {field.name: data[field.name] for field in
                  model._meta.get_fields() if (field.name != 'id' and field.name in data)}
    bscore = model(**final_data)
    return bscore


def get_display_data_for_line_score(line_score):
    vals = []
    for q in range(1, 5):
        vals.append(getattr(line_score, "pts_qtr" + str(q)))
    for ot in range(1, 11):
        ot_pts = getattr(line_score, "pts_ot" + str(ot), None)
        if ot_pts is not None:
            log.debug(("ot pts not null", line_score.game.gamecode, ot_pts))
            vals.append(ot_pts)
    return vals
