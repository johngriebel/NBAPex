import logging
from datetime import date
from urllib.request import urlretrieve
from nba_py.team import (TeamPlayerOnOffDetail, TeamPlayerOnOffSummary,
                         TeamSummary, TeamDetails)
from nba_stats.models import Team, Player, Coach
from nba_stats.web_handlers.base_handler import BaseHandler
from nba_stats.constants import NBA_BASE_URL, REGULAR_SEASON, BASE, TOTALS
from nba_stats.utils import (make_season_int, auto_strip_and_convert_fields,
                             get_model, make_unique_filter_dict, make_season_str,
                             determine_season_for_date, dictify)

log = logging.getLogger('stats')


class TeamHandler(BaseHandler):
    def __init__(self, team_id):
        super().__init__(base_url=NBA_BASE_URL, model=Team)
        self.team_id = team_id
        self.team_instance = None
        self.raw_data = None
        self.summary = None
        self.details = None

    def _convert_dict_to_apex(self):
        self.raw_data['GENERAL_MANAGER'] = self.raw_data['GENERALMANAGER']
        coach_name = self.raw_data['HEADCOACH']
        coach, created = Coach.objects.get_or_create(display_first_last=coach_name,
                                                     defaults={'first_name': coach_name.split()[0],
                                                               'last_name': coach_name.split()[-1],
                                                               'display_first_last': coach_name})
        if created:
            log.debug(("Created a new coach: ", coach))
        self.raw_data['HEAD_COACH'] = coach
        self.raw_data['D_LEAGUE_AFFILIATION'] = self.raw_data['DLEAGUEAFFILIATION']
        for fld in ['TEAM_CITY', 'TEAM_NAME', 'TEAM_ABBREVIATION',
                    'TEAM_CONFERENCE', 'TEAM_DIVISION', 'TEAM_CODE']:
            new_key = fld.split("_")[-1]
            self.raw_data[new_key] = self.raw_data[fld]
        team_instance = auto_strip_and_convert_fields(Team, self.raw_data,
                                                      uppercase=True)
        return team_instance

    def fetch_raw_data(self, *args, **kwargs):
        data_dict = {}
        self.summary = TeamSummary(team_id=self.team_id)
        self.details = TeamDetails(team_id=self.team_id)
        # Change dictify. I hate this
        data_dict.update(dictify(self.summary.json['resultSets'][0])[0])
        dtl_dict = dictify(self.details.json['resultSets'][0])[0]
        data_dict.update({k: dtl_dict[k] for k in dtl_dict
                          if k in ['ARENA', 'ARENA_CAPACITY', 'OWNER',
                                   'GENERALMANAGER', 'HEADCOACH',
                                   'DLEAGUEAFFILIATION']})
        self.raw_data = data_dict
        self.team_instance = self._convert_dict_to_apex()

    def team(self):
        if self.team_instance is None:
            self.fetch_raw_data()
        return self.team_instance


class OnOffHandler(BaseHandler):

    def __init__(self, team):
        super().__init__(base_url=NBA_BASE_URL)
        self.team = team
        self.summary = None
        self.detail = None

    def fetch_raw_data(self, season=None, season_type=REGULAR_SEASON,
                       measure_type=BASE, per_mode=TOTALS):
        if season is None:
            season = make_season_str(determine_season_for_date(date.today()))
        log.debug(("Fetching raw data for: ", self.team, season, season_type,
                   measure_type, per_mode))
        self.raw_data = []
        if self.summary is None:
            log.debug("Don't have a summary yet. Fetching it.")
            summary = TeamPlayerOnOffSummary(team_id=self.team.team_id,
                                             measure_type=measure_type,
                                             per_mode=per_mode,
                                             season=str(season),
                                             season_type=season_type)
            self.summary = summary.json
        detail = TeamPlayerOnOffDetail(team_id=self.team.team_id,
                                       measure_type=measure_type,
                                       per_mode=per_mode,
                                       season=str(season),
                                       season_type=season_type)
        self.detail = detail.json

        self.raw_data = [self.summary, self.detail]

    def _get_objects(self, detail_flag=False):
        log.debug("in _get objects")
        log.debug(("len(self.raw_data): ", len(self.raw_data)))
        objects = []
        idx = 1 if detail_flag else 0
        rawdata = self.raw_data[idx]
        parms = rawdata['parameters']
        measure_type = parms['MeasureType']
        on = rawdata['resultSets'][1]
        off = rawdata['resultSets'][2]
        rows = on['rowSet'] + off['rowSet']
        headers = on['headers']

        prefix = "Player"
        middle = measure_type.replace(" ", "") if detail_flag else ""
        suffix = "OnOffDetail" if detail_flag else "OnOffSummary"
        model = get_model(prefix, middle, suffix)

        for row in rows:
            data = dict(zip(headers, row))
            data['SEASON_ID'] = make_season_int(parms['Season'])
            data['MEASURE_TYPE'] = parms['MeasureType']
            data['SEASON_TYPE'] = parms['SeasonType']
            data['PER_MODE'] = parms['PerMode']
            data['TEAM'] = Team.objects.get(team_id=data['TEAM_ID'])
            data['PLAYER'] = Player.objects.get(player_id=data['VS_PLAYER_ID'])

            if detail_flag:
                if measure_type == "Misc":
                    data['PTS_SECOND_CHANCE'] = data['PTS_2ND_CHANCE']
                    data['OPP_PTS_SECOND_CHANCE'] = data['OPP_PTS_2ND_CHANCE']

                elif measure_type == "Scoring":
                    data['PCT_PTS_2PT_MIDRANGE'] = data['PCT_PTS_2PT_MR']

            final_data = auto_strip_and_convert_fields(model, data,
                                                       uppercase=True,
                                                       make_instance=False)
            filter_dict = make_unique_filter_dict(model, final_data)
            obj, created = model.objects.update_or_create(**filter_dict,
                                                          defaults=final_data)
            if created:
                log.debug(("Created new OnOff ", filter_dict))

            objects.append(obj)

        return objects

    def summaries(self):
        summaries = self._get_objects(detail_flag=False)
        return summaries

    def details(self):
        details = self._get_objects(detail_flag=True)
        return details

    def all(self):
        self.summaries()
        self.details()
