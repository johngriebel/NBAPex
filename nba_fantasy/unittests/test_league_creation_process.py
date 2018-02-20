import logging
import django
django.setup()
from datetime import date, timedelta
from nba_stats.models import Player
from nba_fantasy.models import FantasyTeamRosterEntry, FantasyMatchup
from nba_fantasy.helpers.league import (validate_transaction_settings,
                                        validate_schedule_settings,
                                        validate_draft_settings,
                                        create_schedule)
from nba_fantasy.constants import *
from nba_fantasy.unittests.factories import (FantasyLeagueFactory, UserFactory,
                                             TransactionSettingsFactory, ScheduleSettingsFactory,
                                             DraftSettingsFactory, FantasyTeamFactory)
log = logging.getLogger('unittests')


class TestLeagueCreation:
    def setup(self):
        log.debug("Setup instance method")
        self.user = UserFactory()
        self.league = FantasyLeagueFactory(commissioner=self.user)

    def teardown(self):
        log.debug("Teardown instance method")
        self.user.delete()
        self.league.delete()

    @classmethod
    def setup_class(cls):
        log.debug("Setup class method")

    def test_create_new_league_makes_player_universe(self):
        log.debug("test_create_new_league")
        active_player_count = Player.active_players.all().count()
        new_league_players = FantasyTeamRosterEntry.objects.filter(league=self.league,
                                                                   team=None,
                                                                   acquired_via="UO",
                                                                   acquisition_date=date.today())
        assert active_player_count == new_league_players.count()

    def test_transaction_settings_validation_waivers(self):
        log.debug("Test Transaction Settings Validation Waivers")
        transaction_settings = TransactionSettingsFactory(league=self.league,
                                                          use_waivers_flag=True,
                                                          waiver_period=0,
                                                          season_acquisition_limit=0,
                                                          trade_limit=0,
                                                          keepers_flag=False,
                                                          max_keepers=0)
        success, message = validate_transaction_settings(vars(transaction_settings))
        # TODO: Need to make sure it's failing for the correct reason. Implement a messages system?
        log.debug((success, message))
        assert not success, message

    def test_transaction_settings_validation_not_using_waivers(self):
        log.debug("Test Transaction Settings Validation Not Using Waivers")
        transaction_settings = TransactionSettingsFactory(league=self.league,
                                                          use_waivers_flag=False,
                                                          waiver_period=3,
                                                          season_acquisition_limit=0,
                                                          trade_limit=0,
                                                          keepers_flag=False,
                                                          max_keepers=0)
        success, message = validate_transaction_settings(vars(transaction_settings))
        log.debug((success, message))
        assert not success, message

    def test_transaction_settings_validation_acquisition_limit(self):
        log.debug("Season Acquisition Limit")
        transaction_settings = TransactionSettingsFactory(league=self.league,
                                                          use_waivers_flag=False,
                                                          waiver_period=0,
                                                          season_acquisition_limit=5,
                                                          trade_limit=10,
                                                          keepers_flag=False,
                                                          max_keepers=0)
        success, message = validate_transaction_settings(vars(transaction_settings))
        log.debug((success, message))
        assert not success, message

    def test_transaction_settings_validation_using_keepers(self):
        log.debug("Season Acquisition Limit")
        transaction_settings = TransactionSettingsFactory(league=self.league,
                                                          use_waivers_flag=False,
                                                          waiver_period=0,
                                                          season_acquisition_limit=0,
                                                          trade_limit=0,
                                                          keepers_flag=True,
                                                          max_keepers=0)
        success, message = validate_transaction_settings(vars(transaction_settings))
        log.debug((success, message))
        assert not success, message

    def test_transaction_settings_validation_not_using_keepers(self):
        log.debug("Season Acquisition Limit")
        transaction_settings = TransactionSettingsFactory(league=self.league,
                                                          use_waivers_flag=False,
                                                          waiver_period=0,
                                                          season_acquisition_limit=0,
                                                          trade_limit=0,
                                                          keepers_flag=False,
                                                          max_keepers=5)
        success, message = validate_transaction_settings(vars(transaction_settings))
        log.debug((success, message))
        assert not success, message

    def test_schedule_settings_validation_roto_weeks_matchup(self):
        log.debug("Test Schedule settings roto weeks per matchup")
        schedule_settings = ScheduleSettingsFactory(league=self.league,
                                                    schedule_type="ROTO",
                                                    weeks_per_matchup=1,
                                                    reg_season_matchups=0,
                                                    num_playoff_teams=0)
        success, message = validate_schedule_settings(vars(schedule_settings))
        assert not success, message

    def test_schedule_settings_validation_roto_num_matchups(self):
        log.debug("Test Schedule settings roto num matchups")
        schedule_settings = ScheduleSettingsFactory(league=self.league,
                                                    schedule_type="ROTO",
                                                    weeks_per_matchup=0,
                                                    reg_season_matchups=19,
                                                    num_playoff_teams=0)
        success, message = validate_schedule_settings(vars(schedule_settings))
        assert not success, message

    def test_schedule_settings_validation_roto_playoff_teams(self):
        log.debug("Test Schedule settings roto num playoff teams")
        schedule_settings = ScheduleSettingsFactory(league=self.league,
                                                    schedule_type="ROTO",
                                                    weeks_per_matchup=0,
                                                    reg_season_matchups=0,
                                                    num_playoff_teams=4)
        success, message = validate_schedule_settings(vars(schedule_settings))
        assert not success, message

    def test_draft_settings_validation_bad_date(self):
        log.debug("test draft settings bad date")
        past_date = date.today() - timedelta(days=3)
        draft_settings = DraftSettingsFactory(league=self.league,
                                              draft_type=SNAKE,
                                              draft_date=past_date,
                                              salary_cap=0,
                                              seconds_per_pick=90)
        success, message = validate_draft_settings(vars(draft_settings))
        assert not success, message

    def test_draft_settings_snake_seconds_per_pick(self):
        log.debug("test draft settings seconds per pick")
        future_date = date.today() + timedelta(days=3)
        draft_settings = DraftSettingsFactory(league=self.league,
                                              draft_type=SNAKE,
                                              draft_date=future_date,
                                              salary_cap=0,
                                              seconds_per_pick=0)
        success, message = validate_draft_settings(vars(draft_settings))
        assert not success, message

    def test_draft_settings_snake_salary_cap(self):
        log.debug("test draft settings salary cap")
        future_date = date.today() + timedelta(days=3)
        draft_settings = DraftSettingsFactory(league=self.league,
                                              draft_type=SNAKE,
                                              draft_date=future_date,
                                              salary_cap=100,
                                              seconds_per_pick=90)
        success, message = validate_draft_settings(vars(draft_settings))
        assert not success, message

    def test_draft_settings_salary_cap_no_cap(self):
        log.debug("test draft settings salary cap with no cap set")
        future_date = date.today() + timedelta(days=3)
        draft_settings = DraftSettingsFactory(league=self.league,
                                              draft_type=SALARY_CAP,
                                              draft_date=future_date,
                                              salary_cap=0,
                                              seconds_per_pick=0)
        success, message = validate_draft_settings(vars(draft_settings))
        assert not success, message

    def test_draft_settings_salary_cap_seconds_per_pick(self):
        log.debug("test draft settings salary cap with no cap set")
        future_date = date.today() + timedelta(days=3)
        draft_settings = DraftSettingsFactory(league=self.league,
                                              draft_type=SALARY_CAP,
                                              draft_date=future_date,
                                              salary_cap=1000,
                                              seconds_per_pick=90)
        success, message = validate_draft_settings(vars(draft_settings))
        assert not success, message

    def test_create_schedule_head_to_head_even_teams(self):
        log.debug("test_create_schedule_head_to_head_even_teams")

        all_team_ids = []

        for x in range(0, 10):
            new_team = FantasyTeamFactory(league=self.league)
            all_team_ids.append(new_team.id)

        schedule = ScheduleSettingsFactory(league=self.league,
                                           schedule_type="H2H",
                                           weeks_per_matchup=1,
                                           reg_season_matchups=19,
                                           num_playoff_teams=6)

        create_schedule(self.league)

        end_week = schedule.start_week + (schedule.weeks_per_matchup *
                                          schedule.reg_season_matchups)
        for week in range(schedule.start_week, end_week, schedule.weeks_per_matchup):
            home_teams = []
            away_teams = []
            matchups = FantasyMatchup.objects.filter(home_team__league=self.league,
                                                     away_team__league=self.league,
                                                     week_num=week)
            for mup in matchups:
                home_teams.append(mup.home_team.id)
                away_teams.append(mup.away_team.id)

            # All teams have exactly one matchup
            assert set(all_team_ids) == set(home_teams + away_teams)

    def test_create_schedule_head_to_head_odd_teams(self):
        log.debug("test_create_schedule_head_to_head_even_teams")

        all_team_ids = []

        for x in range(0, 11):
            new_team = FantasyTeamFactory(league=self.league)
            all_team_ids.append(new_team.id)

        schedule = ScheduleSettingsFactory(league=self.league,
                                           schedule_type="H2H",
                                           weeks_per_matchup=1,
                                           reg_season_matchups=19,
                                           num_playoff_teams=6)

        create_schedule(self.league)

        end_week = schedule.start_week + (schedule.weeks_per_matchup *
                                          schedule.reg_season_matchups)
        for week in range(schedule.start_week, end_week, schedule.weeks_per_matchup):
            home_teams = []
            away_teams = []
            matchups = FantasyMatchup.objects.filter(home_team__league=self.league,
                                                     away_team__league=self.league,
                                                     week_num=week)
            for mup in matchups:
                home_teams.append(mup.home_team.id)
                away_teams.append(mup.away_team.id)

            assert len(all_team_ids) == len(home_teams + away_teams) + 1
            # TODO: Figure out how to ensure that bye weeks are evenly distributed

