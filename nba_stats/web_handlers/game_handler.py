import logging
from datetime import date
from nba_stats.web_handlers.base_handler import BaseHandler
from nba_stats.models import *
from nba_stats.constants import NBA_BASE_URL
from nba_stats.helpers.game import (convert_tracking_dict_to_nbapex_fields,
                                    instantiate_correct_boxscore_type)
from nba_stats.utils import (get_json_response,
                             convert_datetime_string_to_date_instance as convert_date,
                             convert_dict_keys_to_lowercase,
                             convert_min_sec_to_float)
log = logging.getLogger('stats')


class GameHandler(BaseHandler):

    def __init__(self):
        super().__init__(NBA_BASE_URL, Game)
        self.endpoint = "scoreboardV2"
        self.full_url = self.base_url + self.endpoint
        self.params = {'DayOffset': 0,
                       'LeagueID': "00",
                       'GameDate': None}
        self.date = None

    def _fetch_raw_data(self, scoreboard_date):
        date_parm = scoreboard_date.strftime("%m/%d/%Y")
        self.params['GameDate'] = date_parm
        self.date = scoreboard_date
        self.raw_data = get_json_response(self.full_url, self.params)

    def game_headers(self, scoreboard_date=date.today(), season=None):
        self._fetch_raw_data(scoreboard_date)
        gh_dict = self.raw_data['resultSets'][0]
        columns = gh_dict['headers']
        rows = gh_dict['rowSet']
        uppercase_dicts = [dict(zip(columns, row)) for row in rows]
        season_type = season.determine_season_type_for_date(scoreboard_date)
        for data in uppercase_dicts:
            data['HOME_TEAM'] = Team.objects.get(team_id=data['HOME_TEAM_ID'])
            data['VISITOR_TEAM'] = Team.objects.get(team_id=data['VISITOR_TEAM_ID'])
            data['GAME_DATE_EST'] = convert_date(data['GAME_DATE_EST'])
            data['SEASON'] = season
            data['SEASON_TYPE'] = season_type

        converted_dicts = [convert_dict_keys_to_lowercase(data, isgame=True)
                           for data in uppercase_dicts]
        return converted_dicts

    def create_games(self, scoreboard_date=date.today(), season=None):
        log.debug("Creating Games for {d}".format(d=scoreboard_date))
        data_dicts = self.game_headers(scoreboard_date=scoreboard_date, season=season)
        self.obj_list = [Game(**data) for data in data_dicts]
        return self.obj_list


class GameSummaryHandler(BaseHandler):

    def __init__(self, game):
        super().__init__(NBA_BASE_URL)
        self.game = game
        self.endpoint = "boxscoresummaryv2"
        self.full_url = self.base_url + self.endpoint
        self.params = {'GameID': self.game.game_id}

    def fetch_raw_data(self):
        self.raw_data = get_json_response(self.full_url, params=self.params)

    def other_stats(self):
        ostats = self._get_data(1)
        ostats_list = []
        for ostat in ostats:
            ostat['GAME'] = self.game
            ostat['TEAM'] = (self.game.home_team if ostat['TEAM_ID'] == self.game.home_team.team_id
                              else self.game.visitor_team)
            ostat['PTS_SECOND_CHANCE'] = ostat['PTS_2ND_CHANCE']
            ostat = convert_dict_keys_to_lowercase(ostat)
            ostat_obj = GameOtherStats(**ostat)
            ostats_list.append(ostat_obj)
        return ostats_list

    def official_xrefs(self):
        xrefs = [convert_dict_keys_to_lowercase(data) for data in self._get_data(2)]
        oxrefs = []
        for xref in xrefs:
            official, created = Official.objects.get_or_create(official_id=xref['official_id'],
                                                               defaults=xref)
            if created:
                log.debug("Created a new official: {ofc}".format(ofc=str(official)))

            oxref = GameOfficialXref(game=self.game, official=official)
            oxrefs.append(oxref)
        return oxrefs

    def game_info(self):
        other_info = self._get_data(4)[0]
        return convert_dict_keys_to_lowercase(other_info)

    def line_scores(self):
        lscores = self._get_data(5)
        lscores_list = []
        for lscore in lscores:
            lscore['GAME_DATE_EST'] = convert_date(lscore['GAME_DATE_EST'])
            lscore['TEAM'] = Team.objects.get(team_id=lscore['TEAM_ID'])
            lscore['GAME'] = self.game
            lscore = convert_dict_keys_to_lowercase(lscore)
            lscores_list.append(LineScore(**lscore))

        return lscores_list


class BoxScoreHandler(BaseHandler):

    def __init__(self, game):
        super().__init__(NBA_BASE_URL)
        self.game = game
        self.box_types = ["traditional", "advanced", "misc", "scoring", "usage",
                          "playertrack", "fourfactors", "hustlestats"]
        self.endpoint = "boxscore{btype}v2"
        self.params = {'GameID': self.game.game_id,
                       'StartPeriod': 1,
                       'EndPeriod': 1,
                       'StartRange': 0,
                       'EndRange': 0,
                       'RangeType': 0}
        # For BoxScores, raw_data is a list of dicts
        self.raw_data = {}

    def fetch_raw_data(self):
        for btype in self.box_types[:-1]:
            full_url = self.base_url + self.endpoint.format(btype=btype)
            rawdata = get_json_response(full_url, params=self.params)
            self.raw_data[btype] = rawdata
        full_url = self.base_url + "hustlestatsboxscore"
        rawdata = get_json_response(full_url, params=self.params)
        self.raw_data['hustle'] = rawdata

    def _determine_matchup_and_winners(self, box_scores):
        home_line_score = self.game.linescore_set.get(team=self.game.home_team)
        away_line_score = self.game.linescore_set.get(team=self.game.visitor_team)

        home_win = home_line_score.pts > away_line_score.pts

        for bscore in box_scores:
            if bscore.team == self.game.home_team:
                bscore.matchup = "vs. " + self.game.visitor_team.abbreviation
                bscore.win_flag = home_win
            else:
                bscore.matchup = "@ " + self.game.home_team.abbreviation
                bscore.win_flag = not home_win

    def boxscore(self, box_type="Traditional"):
        player_box_scores = []
        team_box_scores = []
        bkey = "playertrack" if box_type == "Tracking" else box_type.lower()
        log.debug(("bkey, btype", bkey, box_type))
        data = self.raw_data.get(bkey.replace(" ", ""))

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

                temp_dict['GAME'] = self.game
                temp_dict['TEAM'] = Team.objects.filter(team_id=temp_dict['TEAM_ID']).first()

                player = Player.objects.filter(player_id=temp_dict['PLAYER_ID']).first()
                if not player:
                    # TODO: Properly handle the situation where the given player doesn't exist yet
                    log.debug(
                        "Player id and name about to look up: %s %s" % (temp_dict['PLAYER_ID'],
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

                pbox = instantiate_correct_boxscore_type(p_box_data, box_type)
                player_box_scores.append(pbox)

            for t in team_stats['rowSet']:
                temp_dict = dict(zip(team_headers, t))
                temp_dict['GAME'] = self.game
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

                tbox = instantiate_correct_boxscore_type(t_box_data, box_type)
                team_box_scores.append(tbox)
        else:
            log.debug("Box scores of type {bt} not available for game {gm}".format(bt=box_type,
                                                                                   gm=self.game.game_id))

        ret_dict = {'players': player_box_scores, 'teams': team_box_scores}
        return ret_dict


class PlayByPlayHandler(BaseHandler):

    def __init__(self, game):
        super().__init__(NBA_BASE_URL)
        self.game = game
        self.endpoint = "playbyplayv2"
        self.full_url = self.base_url + self.endpoint
        self.params = {'GameID': self.game.game_id,
                       'StartPeriod': 1,
                       'EndPeriod': 1,
                       'StartRange': 0,
                       'EndRange': 0,
                       'RangeType': 0}

    def fetch_raw_data(self):
        self.raw_data = get_json_response(self.full_url, params=self.params)

    def play_by_play(self):
        pbp_list = []
        pbp_events = self._get_data(0)
        for event in pbp_events:
            event['GAME'] = self.game

            if event['PLAYER1_NAME']:
                player1 = Player.objects.filter(player_id=event['PLAYER1_ID']).first()
                if not player1:
                    player1 = Player(player_id=event['PLAYER1_ID'],
                                     display_first_last=event['PLAYER1_NAME'])
                    player1.save()
                event['PLAYER1'] = player1
            if event['PLAYER1_TEAM_ID']:
                event['PLAYER1_TEAM'] = Team.objects.filter(team_id=
                                                            event['PLAYER1_TEAM_ID']).first()

            if event['PLAYER2_NAME']:
                player2 = Player.objects.filter(player_id=event['PLAYER2_ID']).first()
                if not player2:
                    player2 = Player(player_id=event['PLAYER2_ID'],
                                     display_first_last=event['PLAYER2_NAME'])
                    player2.save()
                event['PLAYER2'] = player2
            if event['PLAYER2_TEAM_ID']:
                event['PLAYER2_TEAM'] = Team.objects.filter(
                    team_id=event['PLAYER2_TEAM_ID']).first()

            if event['PLAYER3_NAME']:
                player3 = Player.objects.filter(player_id=event['PLAYER3_ID']).first()
                if not player3:
                    player3 = Player(player_id=event['PLAYER3_ID'],
                                     display_first_last=event['PLAYER1_NAME'])
                    player3.save()
                event['PLAYER3'] = player3
            if event['PLAYER3_TEAM_ID']:
                event['PLAYER3_TEAM'] = Team.objects.filter(
                    team_id=event['PLAYER3_TEAM_ID']).first()

            if event['SCOREMARGIN'] == 'TIE':
                event['SCOREMARGIN'] = 0

            event = convert_dict_keys_to_lowercase(event)
            pbp = PlayByPlayEvent(**event)
            pbp_list.append(pbp)

        return pbp_list
