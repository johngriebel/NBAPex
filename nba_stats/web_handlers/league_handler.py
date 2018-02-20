import logging
from datetime import date
from nba_py.league import Lineups, PlayerStats, GameLog
from nba_stats import models
from nba_stats.models import Player, Team, Game, PlayerGameLog
# I can't find any docs that say this import is required, but the signal
# Doesn't seem to work without it
# I think I've fixed the setup so that this can be removed. Need to test it out
from nba_stats.signals import lineup_players_changed
from nba_stats.utils import (make_season_int,
                             auto_strip_and_convert_fields,
                             make_unique_filter_dict,
                             determine_season_for_date,
                             make_season_str,
                             dictify, get_model,
                             convert_dict_keys_to_lowercase,
                             get_json_response,
                             convert_datetime_string_to_date_instance)
from nba_stats.web_handlers.base_handler import BaseHandler
from nba_stats.helpers.tracking import (convert_shot_type_dict_to_apex,
                                        convert_touch_dict_to_apex)
from nba_stats.constants import (NBA_BASE_URL, BASE, REGULAR_SEASON,
                                 TOTALS, REVERSE_MONTH_MAP, GROUP_SETS, GROUP_VALUES,
                                 SPEED_DISTANCE, LEAGUE_PLAYER_TRACKING_ENDPOINT,
                                 LEAUGE_PT_PARMS, USAGE, DEFENSE, MISC)

log = logging.getLogger('stats')


class LineupHandler(BaseHandler):

    def __init__(self):
        super().__init__(base_url=NBA_BASE_URL)
        self.raw_data = None
        self.measure_type = None

    def fetch_raw_data(self, season=None, measure_type="Base", per_mode=TOTALS,
                       season_type=REGULAR_SEASON, group_quantity=5):
        self.measure_type = measure_type
        self.model = get_model(prefix=self.measure_type, suffix="Lineup")
        self.raw_data = []
        if measure_type in [USAGE, DEFENSE]:
            raise ValueError("Usage is not a valid measure type for lineups.")

        if season is None:
            season = make_season_str(determine_season_for_date(date.today()))

        log.debug(("Fetching data", season, season_type, measure_type,
                   per_mode, group_quantity))
        # Really hope this respects season type. I've seen scenarios where it doesn't
        lineup = Lineups(season=str(season),
                         season_type=season_type,
                         per_mode=per_mode,
                         group_quantity=group_quantity,
                         measure_type=measure_type)
        resp_json = lineup.json
        parms = resp_json['parameters']
        result_set = resp_json['resultSets'][0]
        lineup_rows = dictify(result_set)

        for row in lineup_rows:
            row['TEAM'] = Team.objects.get(team_id=int(row['TEAM_ID']))
            row['SEASON_ID'] = make_season_int(parms['Season'])
            row['MEASURE_TYPE'] = parms['MeasureType']
            row['SEASON_TYPE'] = parms['SeasonType']
            row['PER_MODE'] = parms['PerMode']
            row['GROUP_QUANTITY'] = parms['GroupQuantity']
            row['SEASON'] = season

            if measure_type == "Misc":
                row['PTS_SECOND_CHANCE'] = row['PTS_2ND_CHANCE']
                row['OPP_PTS_SECOND_CHANCE'] = row['OPP_PTS_2ND_CHANCE']

            elif measure_type == "Scoring":
                row['PCT_PTS_2PT_MIDRANGE'] = row['PCT_PTS_2PT_MR']
            proc_row = convert_dict_keys_to_lowercase(row)
            self.raw_data.append(proc_row)

    # Saving the models in this method goes against what the other handlers do,
    # but handling Many-To-Many fields is a bit difficult. Could not save them
    # and return a list of tuples (or dicts) matching players to lineups, but
    # that would be even more atypical.

    def lineups(self):
        lineups_list = []

        for row in self.raw_data:
            final_data = auto_strip_and_convert_fields(model=self.model,
                                                       data=row,
                                                       make_instance=False)
            player_ids = [int(pid.strip()) for pid in row['group_id'].split("-")]
            players = Player.objects.filter(player_id__in=player_ids).order_by('id')

            filter_dict = make_unique_filter_dict(self.model, final_data)
            filter_dict['group_quantity'] = final_data['group_quantity']
            lineup = self.model.filter_on_players(players, filter_dict).first()

            if lineup is None:
                lineup = self.model(**final_data)
                lineup.save()
                lineup.players = players
                lineup.save()
                log.debug(("Created new lineup: ", filter_dict, players))

            else:
                for fld in final_data:
                    setattr(lineup, fld, final_data[fld])
                lineup.save()

            lineups_list.append(lineup)

        return lineups_list


class LeagueStatsHandler(BaseHandler):
    def __init__(self):
        super().__init__(base_url=NBA_BASE_URL)
        self.measure_type = None
        self.player_or_team = None

    def fetch_raw_data(self, player_or_team=PlayerStats, season=None, season_type=REGULAR_SEASON,
                       measure_type=BASE, per_mode=TOTALS, group_set="Overall",
                       group_value=None):
        self.measure_type = measure_type
        self.player_or_team = player_or_team
        if season is None:
            season = make_season_str(determine_season_for_date(date.today()))
            if group_set == "Overall" and group_value is None:
                group_value = season

        entity = "Player" if self.player_or_team == PlayerStats else "Team"

        log.debug(("Fetching {entity} Stats: ".format(entity=entity), season,
                   season_type, measure_type, per_mode, group_set, group_value))
        if group_set != "Overall":
            if group_set != "Month":
                group_value = GROUP_VALUES[group_value]
            kwargs = {GROUP_SETS[group_set]: group_value}
        else:
            kwargs = {}

        stats = player_or_team(season=str(season),
                               season_type=season_type,
                               measure_type=measure_type,
                               per_mode=per_mode,
                               **kwargs)
        raw_json = stats.json
        rset = raw_json['resultSets'][0]
        stat_rows = dictify(result_set=rset)
        for row in stat_rows:
            if player_or_team == PlayerStats:
                row['PLAYER'] = Player.objects.get(player_id=row['PLAYER_ID'])
            else:
                row['TEAM'] = Team.objects.get(team_id=row['TEAM_ID'])
            row['GROUP_SET'] = group_set
            row['SEASON'] = season
            row['SEASON_TYPE'] = season_type
            row['MEASURE_TYPE'] = measure_type
            row['PER_MODE'] = per_mode
            if group_set == "Month":
                row['GROUP_VALUE'] = REVERSE_MONTH_MAP[group_value]
            else:
                row['GROUP_VALUE'] = group_value
            if measure_type == "Misc":
                row['PTS_SECOND_CHANCE'] = row['PTS_2ND_CHANCE']
                row['OPP_PTS_SECOND_CHANCE'] = row['OPP_PTS_2ND_CHANCE']
            elif measure_type == "Scoring":
                row['PCT_PTS_2PT_MIDRANGE'] = row['PCT_PTS_2PT_MR']
            elif measure_type == "Shooting":
                if row['GROUP_SET'] == "Assisted By":
                    row['GROUP_VALUE'] = row['PLAYER_NAME']
        stat_rows = [convert_dict_keys_to_lowercase(row, override_list=['GROUP_SET',
                                                                        'GROUP_VALUE'])
                       for row in stat_rows]
        self.raw_data = stat_rows

    def splits(self):
        prefix = "Player" if self.player_or_team == PlayerStats else "Team"
        model = get_model(prefix=prefix, middle=self.measure_type.replace("Base", "Traditional"),
                          suffix="Split")
        splits = []
        for row in self.raw_data:
            data = auto_strip_and_convert_fields(model=model, data=row, make_instance=False)
            filter_dict = make_unique_filter_dict(model, data=data)
            split, created = model.objects.update_or_create(**filter_dict, defaults=data)
            if created:
                log.debug("Created a new split with the following parms:")
                log.debug(filter_dict)
            splits.append(split)
        return splits


# TODO: Think about how to combine this with LeagueStatsHandler. They're essentially identical
class LeaguePlayerTrackingHandler(BaseHandler):
    def __init__(self):
        super().__init__(base_url=NBA_BASE_URL)
        self.endpoint = LEAGUE_PLAYER_TRACKING_ENDPOINT
        self.params = LEAUGE_PT_PARMS
        self.pt_measure_type = None

    def fetch_raw_data(self, season=None, season_type=REGULAR_SEASON,
                       pt_measure_type=SPEED_DISTANCE, per_mode=TOTALS, group_set="Overall",
                       group_value=None):
        self.raw_data = []
        self.pt_measure_type = pt_measure_type

        if self.pt_measure_type in ["CatchShoot", "PullUpShot"]:
            middle = "ShotType"
        elif "Touch" in self.pt_measure_type or "Drive" in self.pt_measure_type:
            middle = "Touch"
        else:
            middle = self.pt_measure_type
        self.model = get_model(prefix="Player", middle=middle, suffix="Tracking")

        # Silly way to do this, I know
        url = self.base_url + self.endpoint

        if season is None:
            season = make_season_str(determine_season_for_date(date.today()))
            if group_set == "Overall" and group_value is None:
                group_value = season

        self.params['Season'] = str(season)
        self.params['SeasonType'] = season_type
        self.params['PerMode'] = per_mode
        self.params['PtMeasureType'] = pt_measure_type

        if group_set != "Overall":
            self.params[group_set] = group_value
            if group_set != "Month":
                group_value = GROUP_VALUES[group_value]

        log.debug(("Fetching Player Stats: ", season, season_type, pt_measure_type,
                   per_mode, group_set, group_value))
        raw_json = get_json_response(url, self.params)
        rset = raw_json['resultSets'][0]
        player_rows = dictify(result_set=rset)
        processed_rows = []
        for row in player_rows:
            row['PLAYER'] = Player.objects.get(player_id=row['PLAYER_ID'])
            row['GROUP_SET'] = group_set
            row['SEASON'] = season
            row['SEASON_TYPE'] = season_type
            row['PT_MEASURE_TYPE'] = pt_measure_type
            row['PER_MODE'] = per_mode
            if group_set == "Month":
                row['GROUP_VALUE'] = REVERSE_MONTH_MAP[group_value]
            else:
                row['GROUP_VALUE'] = group_value

            if self.pt_measure_type in ["CatchShoot", "PullUpShot"]:
                row = convert_shot_type_dict_to_apex(row)
            elif "Touch" in self.pt_measure_type or "Drive" in self.pt_measure_type:
                row = convert_touch_dict_to_apex(row)

            proc_row = convert_dict_keys_to_lowercase(row, override_list=['GROUP_SET',
                                                                          'GROUP_VALUE'])
            processed_rows.append(proc_row)
        self.raw_data = processed_rows

    def tracking(self):
        tracks = []

        for row in self.raw_data:
            # Something weird is happening here, but only in specific cases
            # Which are yet to be determined
            data = auto_strip_and_convert_fields(model=self.model,
                                                 data=row,
                                                 make_instance=False)
            filter_dict = make_unique_filter_dict(self.model, data=data)
            track, created = self.model.objects.update_or_create(**filter_dict, defaults=data)

            if created:
                log.debug("Created a new tracking record with the following parms:")
                log.debug(filter_dict)

            tracks.append(track)

        return tracks


class GameLogHandler(BaseHandler):
    def __init__(self):
        super().__init__(base_url=NBA_BASE_URL)
        self.entity_type = None

    def fetch_raw_data(self, season=None, season_type=REGULAR_SEASON,
                       player_or_team="P"):
        if season is None:
            season = make_season_str(determine_season_for_date(date.today()))

        self.entity_type = Player if player_or_team == "P" else Team
        log.debug(("Fetching game logs for ", season, season_type,
                   self.entity_type.__name__))

        gl = GameLog(season=season,
                     season_type=season_type,
                     player_or_team=player_or_team)

        result_set = gl.json['resultSets'][0]
        self.raw_data = dictify(result_set)

    def game_logs(self, game_ids=None, team_ids=None, player_ids=None):
        log.debug("Creating GameLogs")
        glogs = []
        cur_team_id = None
        team = None
        cur_player_id = None
        player = None
        cur_game_id = None
        game = None

        for row in self.raw_data:
            # While the NBA does give a 'SEASON_ID' in its response,
            # It seems to be of the form '22016', or '22015', etc.
            # I don't know what's going on there, and I don't trust it.
            game_date = convert_datetime_string_to_date_instance(row['GAME_DATE'])
            row['GAME_DATE'] = game_date
            row['SEASON_ID'] = determine_season_for_date(game_date)
            row['WIN_FLAG'] = row['WL'] == "W"

            new_game_id = int(row['GAME_ID'])
            if new_game_id != cur_game_id:
                if game_ids is not None and new_game_id not in game_ids:
                    continue

                game = Game.objects.get(game_id=new_game_id)
                cur_game_id = new_game_id
            row['GAME'] = game

            new_team_id = row['TEAM_ID']
            if new_team_id != cur_team_id:
                if team_ids is not None and new_team_id not in team_ids:
                    continue

                team = Team.objects.get(team_id=new_team_id)
                cur_team_id = new_team_id
            row['TEAM'] = team

            if self.entity_type == Player:
                new_player_id = row['PLAYER_ID']
                if player_ids is not None and new_player_id not in player_ids:
                    continue

                if new_player_id != cur_player_id:
                    player = Player.objects.get(player_id=new_player_id)
                    cur_player_id = new_player_id
                row['PLAYER'] = player

            gm_log = auto_strip_and_convert_fields(model=PlayerGameLog,
                                                   data=row,
                                                   uppercase=True,
                                                   make_instance=True)
            glogs.append(gm_log)

        return glogs
