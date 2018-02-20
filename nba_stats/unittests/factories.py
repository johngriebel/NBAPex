import django
django.setup()
import factory
from datetime import date, timedelta
from factory import fuzzy
from factory.django import  DjangoModelFactory
from nba_stats.models import (Player, Team, Game, LineScore)
from nba_stats.unittests.factory_utils import (FuzzyEntityIdentifier,
                                               generate_time_left_in_period_stamp,
                                               FuzzyDuration, FuzzyNullable)
from nba_stats.utils import determine_season_for_date


class TeamFactory(DjangoModelFactory):
    class Meta:
        model = Team
    team_id = FuzzyEntityIdentifier(model=Team, field='team_id')
    city = fuzzy.FuzzyText(length=50)
    name = fuzzy.FuzzyText(length=50)
    abbreviation = fuzzy.FuzzyText(length=5)
    conference = fuzzy.FuzzyText(length=4)
    division = fuzzy.FuzzyText(length=25)
    code = fuzzy.FuzzyText(length=25)
    arena = fuzzy.FuzzyText(length=100)
    arena_capacity = fuzzy.FuzzyInteger(low=1)
    owner = fuzzy.FuzzyText(length=200)
    general_manager = fuzzy.FuzzyText(length=200)
    d_league_affiliation = fuzzy.FuzzyText(length=150)
    bbref_abbreviation = fuzzy.FuzzyText(length=5)


class PlayerFactory(DjangoModelFactory):
    class Meta:
        model = Player
    player_id = FuzzyEntityIdentifier(model=Player, field='player_id')
    first_name = fuzzy.FuzzyText(length=100)
    last_name = fuzzy.FuzzyText(length=100)
    display_first_last = factory.LazyAttribute(lambda x: x.first_name + " " + x.last_name)
    display_last_comma_first = factory.LazyAttribute(lambda x: x.last_name + ", " + x.first_name)
    display_fi_last = factory.LazyAttribute(lambda x: x.first_name[0] + " " + x.last_name)
    birthdate = fuzzy.FuzzyDate(start_date=date(1920, 1, 1))
    height = fuzzy.FuzzyInteger(low=60, high=100)
    weight = fuzzy.FuzzyInteger(low=50, high=400)
    season_exp = fuzzy.FuzzyInteger(low=0, high=20)
    jersey = fuzzy.FuzzyChoice([str(x) for x in range(100)])
    position = fuzzy.FuzzyChoice(['', 'Center', 'Center-Forward', 'Forward', 'Forward-Center',
                                  'Forward-Guard', 'Guard', 'Guard-Forward', None])
    rosterstatus = fuzzy.FuzzyChoice(['Active', 'Inactive', None])
    team = factory.SubFactory(Team)
    playercode = fuzzy.FuzzyText(length=35)
    from_year = fuzzy.FuzzyInteger(low=1995, high=2017)
    to_year = fuzzy.FuzzyInteger(low=1995, high=2017)


class GameFactory(DjangoModelFactory):
    class Meta:
        model = Game
    game_id = FuzzyEntityIdentifier(model=Game, field='game_id')
    game_date_est = fuzzy.FuzzyDate(start_date=date.today() - timedelta(days=1000))
    game_sequence = factory.Sequence(lambda n: n)
    game_status_id = fuzzy.FuzzyInteger(low=0, high=4)
    game_status_text = fuzzy.FuzzyText(length=50)
    gamecode = fuzzy.FuzzyText(length=100)
    home_team = factory.SubFactory(TeamFactory)
    visitor_team = factory.SubFactory(TeamFactory)
    season = factory.LazyAttribute(lambda obj: determine_season_for_date(obj.game_date_est))
    live_period = fuzzy.FuzzyInteger(low=0, high=10)
    live_pc_time = factory.LazyFunction(generate_time_left_in_period_stamp)
    natl_tv_broadcaster_abbreviation = fuzzy.FuzzyText(length=6)
    live_period_time_bcast = factory.LazyAttribute(lambda obj:
                                                   obj.natl_tv_broadcaster_abbreviation + " - " +
                                                   obj.live_px_time)
    attendance = fuzzy.FuzzyInteger(low=0, high=25000)
    game_time = FuzzyDuration(min_seconds=7200, max_seconds=14400)


# Note: For all factories related to a game and a team (and/or a player)
# You must (currently) define the team/player. It's not easy to ensure
# uniqueness for those things in here, AFAIK
class LineScoreFactory(DjangoModelFactory):
    class Meta:
        model = LineScore

    game = factory.SubFactory(GameFactory)
    game_date_est = factory.LazyAttribute(lambda obj: obj.game.game_date_est)
    game_sequence = factory.LazyAttribute(lambda obj: obj.game.game_sequence)
    team = None
    pts_qtr1 = fuzzy.FuzzyInteger(low=0, high=50)
    pts_qtr2 = fuzzy.FuzzyInteger(low=0, high=50)
    pts_qtr3 = fuzzy.FuzzyInteger(low=0, high=50)
    pts_qtr4 = fuzzy.FuzzyInteger(low=0, high=50)
    pts_ot1 = FuzzyNullable(non_null_type=fuzzy.FuzzyInteger, prob_null=0.8, low=0, high=50)
    pts_ot2 = FuzzyNullable(non_null_type=fuzzy.FuzzyInteger, prob_null=0.8, low=0, high=50)
    pts_ot3 = FuzzyNullable(non_null_type=fuzzy.FuzzyInteger, prob_null=0.8, low=0, high=50)
    pts_ot4 = FuzzyNullable(non_null_type=fuzzy.FuzzyInteger, prob_null=0.8, low=0, high=50)
    pts_ot5 = FuzzyNullable(non_null_type=fuzzy.FuzzyInteger, prob_null=0.8, low=0, high=50)
    pts_ot6 = FuzzyNullable(non_null_type=fuzzy.FuzzyInteger, prob_null=0.8, low=0, high=50)
    pts_ot7 = FuzzyNullable(non_null_type=fuzzy.FuzzyInteger, prob_null=0.8, low=0, high=50)
    pts_ot8 = FuzzyNullable(non_null_type=fuzzy.FuzzyInteger, prob_null=0.8, low=0, high=50)
    pts_ot9 = FuzzyNullable(non_null_type=fuzzy.FuzzyInteger, prob_null=0.8, low=0, high=50)
    pts_ot10 = FuzzyNullable(non_null_type=fuzzy.FuzzyInteger, prob_null=0.8, low=0, high=50)
    pts = fuzzy.FuzzyInteger(low=0, high=50)
