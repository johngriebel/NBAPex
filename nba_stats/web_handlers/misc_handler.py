from bs4 import BeautifulSoup as bs
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.db.models import Q
from nba_stats.models import *
from nba_stats.utils import *
from nba_stats.web_handlers.base_handler import BaseHandler


# TODO: Remove all the * imports.
class InjuryHandler:

    def __init__(self, url=INJURIES_URL):
        self.url = url
        self.soup = None
        self.dict_list = []

    def fetch_raw_data(self):
        resp = get(self.url)
        html = resp.text
        self.soup = bs(html, 'html.parser')

    # TODO: Come up with a better name for this func.
    def parse(self):
        inj_div = self.soup.find(id='cp1_pnlInjuries')
        team_injuries = inj_div.find_all(attrs={'class': 'pb'})
        today = date.today()
        for tinj in team_injuries:
            rows = tinj.find_all('tr')
            player_rows = rows[1:]
            # IT's about to get reaaal ugly
            for prow in player_rows:
                cells = prow.find_all('td')
                display_name = cells[0].text
                log.debug("Parsing injury data for " + display_name)
                try:
                    player = Player.objects.get(display_first_last=display_name)
                except (ObjectDoesNotExist, MultipleObjectsReturned) as e:
                    log.exception(e)
                    log.debug("Just moving on for now. Either fix manually, "
                              "or decide on a strategy")
                    continue
                report = cells[1].find(attrs={'class': "report"}).text
                # cells[2] is just the player's position
                status = cells[3].text
                raw_date_parts = cells[4].text.split("\xa0")
                log.debug(raw_date_parts)
                month = MONTHS[raw_date_parts[0].lower()]
                day = int(raw_date_parts[1])
                # Could probably write a unit test for this
                if month > today.month or (month == today.month and day > today.day):
                    year = today.year - 1
                else:
                    year = today.year
                injury_date = date(year=year, month=month, day=day)
                descr = cells[5].text
                impact = cells[6].text
                inj_dict = {'player': player, 'report': report,
                            'status': status, 'injury_date': injury_date,
                            'current_impact': impact, 'description': descr}
                self.dict_list.append(inj_dict)

    def create(self):
        injuries = []
        for data in self.dict_list:
            injury = Injury(**data)
            injuries.append(injury)
        Injury.objects.bulk_create(injuries)


class BasketBallRef:

    def __init__(self):
        self.base_url = BBREF_BASE_URL
        self.player_id_strs = []

    def populate_list_of_player_ids(self, letter):
        list_url = self.base_url + "players/{l}/".format(l=letter)
        soup = get_beautiful_soup(list_url)
        player_table = soup.find(attrs={'id': 'players'})
        tbody = player_table.find('tbody')
        rows = tbody.find_all('tr')
        for row in rows:
            header = row.find('th')
            link = header.a.attrs['href']
            link = link.replace(".html", "")
            id = link.replace("/players/{l}/".format(l=letter), "")
            self.player_id_strs.append(id)

    def match_player_to_bbref_id(self, bbref_id):
        log.debug("Attempting to find matching player for bbref id %s" % bbref_id)
        url = self.base_url + "players/{l}/{id}.html".format(l=bbref_id[0],
                                                             id=bbref_id)
        print(url)
        soup = get_beautiful_soup(url)
        info_panel = soup.find(attrs={'itemtype': "http://schema.org/Person"})
        if info_panel is None:
            # This means that we got a 404 somehow, just move on for now.
            # Jeff Ayres/Pendergraph is an example of this -_-
            return

        names_to_try = []
        init_name = info_panel.find('h1').text
        player = Player.objects.filter(display_first_last=init_name)
        alt_name = ""
        if not player.exists():
            all_pgraphs = info_panel.find_all('p')
            if "Pronunciation" in all_pgraphs[0].text:
                pgraph = all_pgraphs[1]
                alt_name = pgraph.find('strong').find('strong').text
            else:
                alt_name = info_panel.find('p').find('strong').find('strong').text
            player = Player.objects.filter(display_first_last=alt_name)
            if not player.exists():
                log.debug("Could not find a player by either of the following names: {x}\n{y}."
                          "Giving up for now, fix manually.".format(x=init_name, y=alt_name))
                print("Could not find a player by either of the following names: {x}\n{y}."
                      "Giving up for now, fix manually.".format(x=init_name, y=alt_name))
                return
        if player.count() > 1:
            log.debug("More than one player found. Attempting to narrow down using birthdate.")
            birthdate_tag = info_panel.find(attrs={'id':'necro-birth'})
            bdate_str = birthdate_tag.attrs['data-birth']
            log.debug(("bdate str", bdate_str))
            bdate = convert_datetime_string_to_date_instance(bdate_str)
            player = player.filter(birthdate=bdate)
            if player.count() > 1:
                log.debug("Found more than one player with name {n} and"
                          "birthdate {d}".format(n=player.first().display_first_last,
                                                 d=bdate))
                raise Exception("Too Many Players found.")
        player = player.first()
        if player is None:
            log.debug("I don't know how this possibly could have happened, but a player"
                      "STILL hasn't been found. Moving on.")
            return
        player.bbref_id_str = bbref_id
        if player.display_first_last != init_name:
            player.alternate_name = init_name
        elif alt_name and player.display_first_last != alt_name:
            player.alternate_name = alt_name
        player.save()


class SalaryHandler(BaseHandler):

    def __init__(self):
        super().__init__(base_url=BBREF_BASE_URL, model=PlayerContractSeason)
        log.debug("Creating a salary Handler")
        self.soup = None
        self.contract_seasons = []
        self.player = None

    def fetch_raw_data(self):
        full_url = self.base_url + BBREF_CONTRACTS_ENDPOINT
        self.soup = get_beautiful_soup(full_url)

    def contracts(self):
        contract_table = self.soup.find(attrs={'id': 'player-contracts'})
        tbody = contract_table.find('tbody')
        prows = tbody.find_all(is_player_row)
        contract_years = []
        dne_count = 0
        for row in prows:
            cells = row.find_all('td')
            link = cells[0].a.attrs['href']
            idstr = link[11:].rstrip(".html")
            try:
                player = Player.objects.get(bbref_id_str=idstr)
            except Exception as e:
                dne_count += 1
                log.debug(idstr)
                log.exception(e)
                continue
            salary_cells = cells[2:8]
            salary_amounts = [convert_salary_to_int(cell.text) for cell in salary_cells if
                              cell.text]
            # player:salary-pl, team: salary-tm, eto: salary-et
            # Almost certain this is uniform, but won't be surprised when it breaks
            options = [cell.attrs.get('class')[1].split("-")[-1] for cell in salary_cells
                                                                     if cell.text]
            season_id = 2016
            for salary in salary_amounts:
                option = CONTRACT_OPTIONS.get(options[season_id - 2016])
                contract_season = PlayerContractSeason(player=player, season_id=season_id,
                                                       salary=salary, option=option)
                contract_years.append(contract_season)
                season_id += 1
        log.debug(("Total num players not found ", dne_count))
        return contract_years


class TransactionHandler(BaseHandler):
    # Note: Transactions are a highly irregular endpoint for nba.com
    # There are no parameters (that I can find), and the records only go back to july 2015.

    def __init__(self):
        super().__init__(NBA_TRANSACTION_ENDPOINT, Transaction)

    def _convert_to_apex_dict(self, nba_dict):
        apex_dict = {}
        pid = int(nba_dict['player_id'])
        log.debug("Looking up player_id " + str(pid))
        player = Player.objects.get(player_id=pid)
        apex_dict['player'] = player
        tid = int(nba_dict['team_id'])
        log.debug("Looking up team_id " + str(tid))
        team = Team.objects.get(team_id=tid)
        apex_dict['team'] = team
        apex_dict['transaction_date'] = convert_datetime_string_to_date_instance(nba_dict['transaction_date'])
        apex_dict['transaction_type'] = nba_dict['transaction_type']
        apex_dict['description'] = nba_dict['transaction_description']
        apex_dict['group_sort'] = nba_dict['groupsort']
        apex_dict['additional_sort'] = str(nba_dict['additional_sort'])
        return apex_dict

    def fetch_raw_data(self):
        log.debug("Fetching raw data for transactions.")
        self.raw_data = get_json_response(self.base_url)

    def parse(self):
        rows = self.raw_data['NBA_Player_Movement']['rows']
        rows = list(map(lambda x: {k.lower(): x[k] for k in x}, rows))
        data_dicts = []
        for row in rows:
            try:
                data = self._convert_to_apex_dict(row)
                data_dicts.append(data)
            except ObjectDoesNotExist as e:
                log.exception(e)
                log.debug("Data that caused exception:")
                log.debug(row)
                continue

        for data in data_dicts:
            self.obj_list.append(Transaction(**data))


class DraftHandler(BaseHandler):

    def __init__(self, year):
        super().__init__(base_url=BBREF_BASE_URL)
        log.debug("Creating a Draft Handler")
        self.soup = None
        self.year = year
        self.draft_picks = []

    def fetch_raw_data(self):
        full_url = BBREF_BASE_URL + BBREF_DRAFT_ENDPOINT.format(year=self.year)
        self.soup = get_beautiful_soup(full_url)

    def draftpicks(self):
        draft_picks = []
        table = self.soup.find(attrs={'id': 'stats'})
        prows = table.find_all(is_player_row)[1:]
        for row in prows:
            cells = row.find_all('td')
            link = cells[2].a.attrs['href']
            idstr = link[11:].rstrip(".html")

            player = Player.objects.filter(bbref_id_str=idstr).first()
            player_name = cells[2].text
            team_abb = cells[1].text

            try:
                team = Team.objects.get(Q(abbreviation=team_abb) | Q(bbref_abbreviation=team_abb))
            except Exception as e:
                log.exception(e)
                log.debug(("Bad/missing abbreviation", team_abb))
                continue

            pick = int(cells[0].text)
            draft_pick = DraftPick(player=player, team=team,
                                   year=self.year, pick=pick,
                                   player_name=player_name)
            draft_picks.append(draft_pick)

        return draft_picks
