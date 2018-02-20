from nba_stats.web_data_handler import SalaryGetter


class TestSalaryGetter:
    # TODO: Figure up setup and teardown functions...

    def test_parse_contract_info(self):
        sg = SalaryGetter()
        cinfo = ('2016-17:  $15,730,338  2017-18:  $16,910,113  2018-19:  $18,089,887  '
                 '2019-20:  $18,089,887  {Player  Option}  2020-21:  UFA')
        sg._parse_contract_info(cinfo)
        assert len(sg.contract_seasons) == 4, len(sg.contract_seasons)
        first_season = sg.contract_seasons[0]
        last_season = sg.contract_seasons[-1]
        assert first_season.season_id == 2016
        assert first_season.salary == 15730338
        assert first_season.option is None
        assert last_season.season_id == 2019
        assert last_season.salary == 18089887
        assert last_season.option == "Player"
