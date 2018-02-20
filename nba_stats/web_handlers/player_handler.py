import logging
from urllib.request import urlretrieve
from bs4 import BeautifulSoup, Comment
from django.db.models import Q
from datetime import date
from nba_py.player import PlayerSummary
from nba_py.shotchart import ShotChart
from nba_stats.models import (Team, Transaction, Player, Game, PlayerShotChartDetail)
from nba_stats.helpers.player import sanitize_player_data
from nba_stats.utils import (get_beautiful_soup, make_unique_filter_dict,
                             auto_strip_and_convert_fields,
                             make_season_str, determine_season_for_date,
                             dictify, convert_dict_keys_to_lowercase)
from nba_stats.web_handlers.base_handler import BaseHandler
from nba_stats.constants import (NBA_BASE_URL, BBREF_BASE_URL, MONTHS)

log = logging.getLogger('stats')


class PlayerHandler(BaseHandler):
    def __init__(self, player, database="default"):
        super().__init__(base_url=NBA_BASE_URL)
        self.database = database
        if isinstance(player, Player):
            self.player_instance = player
            self.player_nba_id = player.player_id
        elif isinstance(player, int):
            self.player_instance = Player.objects.using(self.database).filter(player_id=player).first()
            self.player_nba_id = player
        else:
            raise ValueError("player argument bust either be a Player instance, or an id."
                             " You passed a {x}".format(x=type(player)))

    def get_player_image(self, filepath):
        url = "http://stats.nba.com/media/players/230x185/{pid}.png".format(pid=
                                                                            self.player_instance.player_id)
        urlretrieve(url, filepath + str(self.player_instance.player_id) + ".png")

    def fetch_raw_data(self):
        log.debug(("Before summary request", self.player_nba_id))
        plr_sum = PlayerSummary(player_id=self.player_nba_id)
        log.debug("After summary request")
        headers = plr_sum.json['resultSets'][0]['headers']
        values = plr_sum.json['resultSets'][0]['rowSet'][0]
        data_dict = dict(zip(headers, values))
        data_dict = sanitize_player_data(data_dict)
        try:
            data_dict['TEAM'] = Team.objects.get(team_id=data_dict['TEAM_ID'])
        except Exception as e:
            log.debug(("DINGO", data_dict))
            raise e
        final_data = auto_strip_and_convert_fields(Player, data=data_dict,
                                                   uppercase=True, make_instance=False)
        self.raw_data = final_data

    def create_update_player(self):
        # NOTE: If creating a player, he is not saved, so that bulk_create can be used
        if self.player_instance is None:
            action = "Created "
            log.debug("No player exists, so creating a new one.")
            self.player_instance = Player(**self.raw_data)
        else:
            action = "Updated "
            log.debug("Updating existing player.")
            for fld in self.raw_data:
                setattr(self.player_instance, fld, self.raw_data[fld])
            self.player_instance.save(using=self.database)

        log.debug((action, self.player_instance.display_first_last))
        return self.player_instance


class PlayerTransactionHandler(BaseHandler):
    def __init__(self, player):
        super().__init__(base_url=BBREF_BASE_URL)
        self.player = player
        suffix = "players/{l}/{idstr}.html".format(l=self.player.bbref_id_str[0],
                                                   idstr=self.player.bbref_id_str)
        self.full_url = self.base_url + suffix
        self.raw_data = None

    def _to_team(self, tag):
        return tag.has_attr('data-attr-to')

    def _from_team(self, tag):
        return tag.has_attr('data-attr-from')

    def fetch_raw_data(self):
        soup = get_beautiful_soup(self.full_url)
        transaction_div = soup.find(attrs={'id': 'all_transactions'})
        comment = transaction_div.find_all(string=lambda text: isinstance(text, Comment))[0]
        new_html = comment.strip()
        self.raw_data = BeautifulSoup(new_html, 'lxml')

    def transactions(self):
        log.debug(("Beginning fetching transactions for ", self.player.display_first_last))
        transactions = []
        raw_transactions = self.raw_data.find_all(attrs={'class': "transaction"})
        for rawt in raw_transactions:
            to_team = None
            from_team = None
            date_str, description = rawt.text.split(":")
            date_parts = date_str.replace(",", "").split()
            month = MONTHS[date_parts[0].lower()]
            trans_date = date(year=int(date_parts[2]), month=month, day=int(date_parts[1]))
            descr_parts = description.strip().split()
            if "trade" in description.lower():
                transaction_type = "Traded"
            elif "announce" in description.lower():
                transaction_type = "Retired"
            elif ("assigned" in description.lower() or
                          "recalled" in description.lower()):
                # This is just D-League Shuffling. Move on.
                continue
            else:
                transaction_type = descr_parts[0]
            try:
                to_team_tag = rawt.find(self._to_team)
                if to_team_tag:
                    # TODO: Update teams to account for these abbreviations.
                    # Not sure how much perf will be gained though
                    to_team_abb = to_team_tag.attrs.get('data-attr-to')
                    if to_team_abb in ["NOH", "NOK"]:
                        to_team_abb = "NOP"
                    elif to_team_abb == "NJN":
                        to_team_abb = "BKN"
                    elif to_team_abb == "VAN":
                        to_team_abb = "MEM"
                    elif to_team_abb == "WSB":
                        to_team_abb = "WAS"
                    elif to_team_abb == "SEA":
                        to_team_abb = "OKC"

                    to_team = Team.objects.get(Q(bbref_abbreviation=to_team_abb) |
                                               Q(abbreviation=to_team_abb))
                from_team_tag = rawt.find(self._from_team)
                if from_team_tag:
                    from_team_abb = from_team_tag.attrs.get('data-attr-from')
                    if from_team_abb in ["NOH", "NOK"]:
                        from_team_abb = "NOP"
                    elif from_team_abb == "NJN":
                        from_team_abb = "BKN"
                    elif from_team_abb == "VAN":
                        from_team_abb = "VAN"
                    elif from_team_abb == "WSB":
                        from_team_abb = "WAS"
                    elif from_team_abb == "SEA":
                        from_team_abb = "OKC"

                    from_team = Team.objects.get(Q(bbref_abbreviation=from_team_abb) |
                                                 Q(abbreviation=from_team_abb))
            except Exception as e:
                # Most likely just came across a player being assigned to the D-League
                log.debug(("player", self.player.display_first_last,
                           description))
                log.exception(e)
                raise e
            data = {'player': self.player, 'from_team': from_team, 'to_team':to_team,
                    'transaction_date': trans_date, 'transaction_type': transaction_type,
                    'description': description.strip()}
            filter_dict = make_unique_filter_dict(Transaction, data)
            try:
                transaction, created = Transaction.objects.get_or_create(**filter_dict,
                                                                         defaults=data)
            except Exception as e:
                log.debug(("FILTER DICT", filter_dict))
                log.exception(e)
                raise e
            transactions.append(transaction)
        log.debug(("completed fetching transactions for ", self.player.display_first_last))

        return transactions


class PlayerShotChartHandler(BaseHandler):
    def __init__(self):
        super().__init__(base_url=NBA_BASE_URL)
        self.player = None

    def fetch_raw_data(self, player, season=None):
        self.player = player
        if season is None:
            season = make_season_str(determine_season_for_date(date.today()))
        log.debug("Pre network call")
        shot_chart = ShotChart(player_id=player.player_id,
                               season=str(season))
        log.debug("post network call")
        scdtl_dicts = dictify(shot_chart.json['resultSets'][0])
        self.raw_data = scdtl_dicts

    def shotcharts(self, game_ids=None):
        shotchart_details = []
        team = None
        game = None
        for detail in self.raw_data:
            if game_ids is not None and detail['GAME_ID'] not in game_ids:
                continue

            detail['PLAYER'] = self.player

            if team is None or detail['TEAM_ID'] != team.team_id:
                log.debug(detail['TEAM_ID'])
                team = Team.objects.get(team_id=detail['TEAM_ID'])
                log.debug(team)
            detail['TEAM'] = team

            if game is None or detail['GAME_ID'] != getattr(game, 'game_id', None):

                try:
                    game = Game.objects.get(game_id=detail['GAME_ID'])

                except Exception as e:
                    log.debug(("DATA", detail))
                    log.exception(e)
                    raise e

                detail['GAME'] = game

            converted_dict = convert_dict_keys_to_lowercase(detail)
            filter_dict = make_unique_filter_dict(PlayerShotChartDetail, converted_dict)
            shotchart_dtl, created = PlayerShotChartDetail.objects.get_or_create(**filter_dict,
                                                                                 defaults=converted_dict)
            if created:
                log.debug(("Created a new shot chart detail: ", filter_dict))
            shotchart_details.append(shotchart_dtl)

        return shotchart_details
