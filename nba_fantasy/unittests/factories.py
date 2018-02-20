import pytz
import django
django.setup()
import factory
from datetime import datetime, timedelta, date
from factory import fuzzy
from django.contrib.auth.models import User
from nba_fantasy.models import (FantasyLeague, TransactionSettings, ScheduleSettings,
                                DraftSettings, ScoringSettings, FantasyTeam)
from nba_fantasy.constants import (DAILY_ALL_GAME, DAILY_INDIV_GAME, WEEKLY, HEAD_TO_HEAD,
                                   ROTISSERIE, CATEGORY, POINTS, SNAKE, SALARY_CAP)
from nba_fantasy.unittests.factory_utils import create_random_scoring_fields


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
    username = fuzzy.FuzzyText(length=150)
    first_name = fuzzy.FuzzyText(length=30)
    last_name = fuzzy.FuzzyText(length=30)
    # Using example.com because it's just easier for now
    email = fuzzy.FuzzyText(length=50, suffix="@example.com")
    date_joined = fuzzy.FuzzyDateTime(start_dt=datetime.now(tz=pytz.UTC) - timedelta(days=1000))


class FantasyLeagueFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = FantasyLeague

    name = fuzzy.FuzzyText(length=100)
    num_teams = fuzzy.FuzzyInteger(low=4, high=30)
    private_flag = fuzzy.FuzzyChoice([True, False])
    season_start_date = fuzzy.FuzzyDate(start_date=date.today() - timedelta(days=100))
    commissioner = factory.SubFactory(UserFactory)


class TransactionSettingsFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TransactionSettings
    league = factory.SubFactory(FantasyLeagueFactory)
    lineup_changes = fuzzy.FuzzyChoice([DAILY_ALL_GAME, DAILY_INDIV_GAME, WEEKLY])
    use_waivers_flag = fuzzy.FuzzyChoice([True, False])
    waiver_period = fuzzy.FuzzyInteger(low=0, high=5)
    season_acquisition_limit = fuzzy.FuzzyInteger(low=0, high=50)
    trade_limit = fuzzy.FuzzyInteger(low=0, high=25)
    trade_deadline = fuzzy.FuzzyDate(start_date=date.today(),
                                     end_date=date.today() + timedelta(days=100))
    # TODO: implement
    trade_review_period = None
    veto_votes_reqd = fuzzy.FuzzyInteger(low=0, high=6)
    keepers_flag = fuzzy.FuzzyChoice([True, False])
    max_keepers = fuzzy.FuzzyInteger(low=0, high=5)


class ScheduleSettingsFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ScheduleSettings

    league = factory.SubFactory(FantasyLeagueFactory)
    schedule_type = fuzzy.FuzzyChoice([HEAD_TO_HEAD, ROTISSERIE])
    start_week = fuzzy.FuzzyInteger(low=0, high=9)
    weeks_per_matchup = fuzzy.FuzzyInteger(low=0, high=4)
    reg_season_matchups = fuzzy.FuzzyInteger(low=0, high=19)
    num_playoff_teams = fuzzy.FuzzyInteger(low=0, high=10)


class DraftSettingsFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = DraftSettings

    league = factory.SubFactory(FantasyLeagueFactory)
    draft_type = fuzzy.FuzzyChoice([SNAKE, SALARY_CAP])
    draft_date = fuzzy.FuzzyDate(start_date=date.today(),
                                 end_date=date.today() + timedelta(days=100))
    salary_cap = fuzzy.FuzzyInteger(low=0, high=1000)
    seconds_per_pick = fuzzy.FuzzyInteger(low=0, high=300)


class ScoringSettingsFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ScoringSettings

    league = factory.SubFactory(FantasyLeagueFactory)
    scoring_type = fuzzy.FuzzyChoice([CATEGORY, POINTS])
    scoring_fields_vals = fuzzy.FuzzyAttribute(fuzzer=create_random_scoring_fields)


class FantasyTeamFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = FantasyTeam

    league = factory.SubFactory(FantasyLeagueFactory)
    owner = factory.SubFactory(UserFactory)
    # players = None
    city = fuzzy.FuzzyText(length=100)
    name = fuzzy.FuzzyText(length=100)
    abbreviation = fuzzy.FuzzyText(length=5)
    # Leaving off games/wins/losses/ties/win_pct for now