import simplejson
from collections import defaultdict
from decimal import Decimal
from datetime import date
from django.db import models
from django.db.models import Q
from django.contrib.auth.models import User
from django.contrib.postgres.fields import JSONField
from django.urls import reverse
from nba_stats import models as stats_models
from nba_stats.models import Player, PlayerGameLog, PlayerTraditionalBoxScore
from nba_fantasy.constants import (LINEUP_POSITIONS, LINEUP_CHANGE_CHOICES, DAILY_INDIV_GAME,
                                   SCHEDULE_TYPE_CHOICES, HEAD_TO_HEAD, SCORING_TYPE_CHOICES,
                                   POINTS, DRAFT_TYPE_CHOICES, SNAKE)


class FantasyLeague(models.Model):
    name = models.CharField(max_length=100)
    num_teams = models.IntegerField()
    private_flag = models.BooleanField(default=False)
    # TODO: Make the default be a callable that determines the current
    # season's start date
    season_start_date = models.DateField(null=True)
    # Only null because I forgot to have this initially
    commissioner = models.ForeignKey(User, null=True)
    # Begin settings fields

    # Transactions
    lineup_changes = models.CharField(max_length=3, choices=LINEUP_CHANGE_CHOICES,
                                      default=DAILY_INDIV_GAME)
    use_waivers_flag = models.BooleanField(default=False)
    waiver_period = models.IntegerField(default=0)
    season_acquisition_limit = models.IntegerField(default=0)
    trade_limit = models.IntegerField(default=0)
    trade_deadline = models.DateField(null=True)
    trade_review_period = models.DurationField(null=True)
    veto_votes_reqd = models.IntegerField(default=0)
    keepers_flag = models.BooleanField(default=False)
    max_keepers = models.IntegerField(default=0)

    # Schedule
    schedule_type = models.CharField(max_length=4, choices=SCHEDULE_TYPE_CHOICES,
                                     default=HEAD_TO_HEAD)
    start_week = models.IntegerField(default=0)
    weeks_per_matchup = models.IntegerField(default=1)
    reg_season_matchups = models.IntegerField(default=19)
    num_playoff_teams = models.IntegerField(default=4)

    # Draft
    draft_type = models.CharField(max_length=2, choices=DRAFT_TYPE_CHOICES, default=SNAKE)
    draft_date = models.DateTimeField(null=True)
    salary_cap = models.IntegerField(default=0)
    seconds_per_pick = models.IntegerField(default=0)

    # Scoring
    # TODO: Add a hybrid that uses weights to help score categories
    scoring_type = models.CharField(max_length=3, choices=SCORING_TYPE_CHOICES, default=POINTS)
    # This is basically a dict that maps an integer key (later used for ordering)
    # To a tuple of the form: (model__field, value)
    # e.g {0: ('traditional__pts', 1)}
    scoring_fields_vals = JSONField(null=True)

    # Roster
    point_guard = models.IntegerField(default=0)
    shooting_guard = models.IntegerField(default=0)
    small_forward = models.IntegerField(default=0)
    power_forward = models.IntegerField(default=0)
    center = models.IntegerField(default=0)
    guard = models.IntegerField(default=0)
    forward = models.IntegerField(default=0)
    wing = models.IntegerField(default=0)
    big = models.IntegerField(default=0)
    util = models.IntegerField(default=0)
    inj = models.IntegerField(default=0)
    bench = models.IntegerField(default=0)
    total = models.IntegerField(default=0)

    def __str__(self):
        pub_priv = "Private" if self.private_flag else "Public"
        return self.name + ": " + pub_priv

    def get_model_fields_map(self, suffix="BoxScore"):
        split_fields_dict = defaultdict(list)

        for fld in self.scoring_fields_vals:
            split_type, field = fld.split("__")
            if split_type in ["PlayerHustleStats", "PlayerTracking", "PlayerFourFactors"]:
                suffix = "BoxScore"
            full_model_name = split_type + suffix
            split_fields_dict[full_model_name].append(field)
        return split_fields_dict

    def save(self, *args, **kwargs):
        ros_vals = [self.point_guard, self.shooting_guard, self.small_forward,
                    self.power_forward, self.center, self.guard, self.forward,
                    self.wing, self.big, self.util, self.inj, self.bench, self.inj]
        self.total = sum(map(int, ros_vals))

        if self.id is None:
            super(FantasyLeague, self).save(*args, **kwargs)
            today = date.today()
            player_universe = Player.active_players.all()
            ros_entries = []
            for player in player_universe:
                unowned_roster_entry = FantasyTeamRosterEntry(league=self,
                                                              team=None,
                                                              player=player,
                                                              acquired_via="UO",
                                                              acquisition_date=today)
                ros_entries.append(unowned_roster_entry)
            FantasyTeamRosterEntry.objects.bulk_create(ros_entries)
        else:
            super(FantasyLeague, self).save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("nba_fantasy:fantasy-league-detail", kwargs={'pk': self.pk})

    class Meta:
        db_table = 'fantasy_league'
        unique_together = ('name', 'commissioner')


class FantasyTeam(models.Model):
    league = models.ForeignKey(FantasyLeague)
    owner = models.ForeignKey(User)
    players = models.ManyToManyField(Player, through="FantasyTeamRosterEntry")
    city = models.CharField(max_length=100)
    name = models.CharField(max_length=100)
    abbreviation = models.CharField(max_length=5)
    games = models.IntegerField(default=0)
    wins = models.IntegerField(default=0)
    losses = models.IntegerField(default=0)
    ties = models.IntegerField(default=0)
    win_pct = models.DecimalField(max_digits=5, decimal_places=3)

    def __str__(self):
        s = "{lg}: {city} {name} ({own})".format(lg=str(self.league),
                                                 city=self.city,
                                                 name=self.name,
                                                 own=self.owner.username)
        return s

    class Meta:
        db_table = 'fantasy_team'
        unique_together = (('league', 'owner'),
                           ('league', 'city', 'name'))


UNOWNED = "UO"
DRAFT = "DR"
TRADE = "TD"
FREE_AGENCY = "FA"
TRANSACTION_TYPES = ((DRAFT, "Drafted"),
                     (TRADE, "Trade"),
                     (FREE_AGENCY, "Free Agency/Waivers"),
                     (UNOWNED, "Is a Free agent"))


class FantasyTeamRosterEntry(models.Model):
    league = models.ForeignKey(FantasyLeague)
    team = models.ForeignKey(FantasyTeam, null=True)
    player = models.ForeignKey(Player)
    acquired_via = models.CharField(max_length=2, choices=TRANSACTION_TYPES)
    acquisition_date = models.DateField(null=True)
    end_date = models.DateField(null=True)

    def __str__(self):
        s = ("Roster Entry: {lg}/{tm}: {plr} "
             "acq. via {acq} on {dt}").format(lg=str(self.league),
                                              tm=str(self.team),
                                              plr=self.player.display_first_last,
                                              acq=self.acquired_via,
                                              dt=str(self.acquisition_date))
        return s

    class Meta:
        db_table = 'fantasy_team_roster_entry'


# This very closely mirrors FTeamRosterEntry, & creates approx, double 'necessary' records,
# But I think it's the most straightforward solution in terms of design
class FantasyTeamTransaction(models.Model):
    team = models.ForeignKey(FantasyTeam, related_name="team")
    outgoing_players = models.ManyToManyField(Player, related_name='outgoing_players')
    incoming_players = models.ManyToManyField(Player, related_name='incoming_players')
    transaction_date = models.DateField(null=True)
    transaction_type = models.CharField(max_length=2, choices=TRANSACTION_TYPES)
    # Next four are for trades only
    proposal_time = models.DateTimeField(null=True)
    expiry_time = models.DateTimeField(null=True)
    accepted_flag = models.BooleanField(default=False)
    trade_identifier = models.UUIDField(null=True)

    class Meta:
        db_table = 'fantasy_team_transaction'


class FantasyMatchup(models.Model):
    league = models.ForeignKey(FantasyLeague, null=True)
    home_team = models.ForeignKey(FantasyTeam, related_name="home_team")
    away_team = models.ForeignKey(FantasyTeam, related_name="away_team", null=True)
    begin_date = models.DateField()
    end_date = models.DateField()
    home_scoring_values = JSONField(null=True)
    away_scoring_values = JSONField(null=True)
    week_num = models.IntegerField(default=0)
    scoring_completed_flag = models.BooleanField(default=False)

    def get_all_lineup_entries(self):
        entries = FantasyLineupEntry.objects.filter(Q(team=self.home_team) | Q(team=self.away_team),
                                                    lineup_date__gte=self.begin_date,
                                                    lineup_date__lte=self.end_date)
        return entries

    def score_matchup(self):
        if not self.scoring_completed_flag:
            all_entries = self.get_all_lineup_entries()
            need_scoring = all_entries.filter(scoring_completed_flag=False)
            for entry in need_scoring:
                entry.score_entry()
            # Is this reload needed?
            all_entries = self.get_all_lineup_entries()

            home_entries = all_entries.filter(team=self.home_team)
            home_json = defaultdict(Decimal)

            away_entries = all_entries.filter(team=self.away_team)
            away_json = defaultdict(Decimal)

            home_wins = 0
            away_wins = 0
            ties = 0

            for key in self.league.scoringsettings.scoring_fields_vals.keys():
                for home_ent in home_entries:
                    home_score = simplejson.loads(home_ent.score, use_decimal=True)
                    home_json[key] += home_score[key][1]
                    home_json['total'] += home_score[key][1]

                for away_ent in away_entries:
                    away_score = simplejson.loads(away_ent.score, use_decimal=True)
                    away_json[key] += away_score[key][1]
                    away_json['total'] += away_score[key][1]

                if home_json[key] > away_json[key]:
                    home_wins += 1
                elif away_json[key] > home_json[key]:
                    away_wins += 1
                else:
                    ties += 1

            if self.league.scoringsettings.scoring_type == POINTS:
                home_wins = 0
                away_wins = 0
                ties = 0
                if home_json['total'] > away_json['total']:
                    home_wins = 1
                elif away_json['total'] > home_json['total']:
                    away_wins = 1
                else:
                    ties = 0

            home_json.update({'wins': home_wins,
                              'losses': away_wins,
                              'ties': ties})
            away_json.update({'wins': away_wins,
                              'losses': home_wins,
                              'ties': ties})

            self.home_scoring_values = simplejson.dumps(home_json)
            self.away_scoring_values = simplejson.dumps(away_json)

            if date.today() > self.end_date:
                self.home_team.wins += home_json['wins']
                self.home_team.losses += home_json['losses']
                self.home_team.ties += home_json['ties']
                self.home_team.games += (home_json['wins'] + home_json['losses'] +
                                         home_json['ties'])
                self.home_team.win_pct = (Decimal(self.home_team.wins + 0.5 * self.home_team.ties) /
                                          Decimal(self.home_team.games))
                self.home_team.save()

                self.away_team.wins += away_json['wins']
                self.away_team.losses += away_json['losses']
                self.away_team.ties += away_json['ties']
                self.away_team.games += (away_json['wins'] + away_json['losses'] + away_json['ties'])
                self.away_team.win_pct = (Decimal(self.away_team.wins + 0.5 * self.away_team.ties) /
                                          Decimal(self.away_team.games))
                self.away_team.save()

                self.scoring_completed_flag = True

            self.save()

    def __str__(self):
        s = (self.away_team.city + " " + self.away_team.name + " @ " +
             self.home_team.city + " " + self.home_team.name + "Begin: " +
             str(self.begin_date) + " End: " + str(self.end_date))
        return s

    class Meta:
        db_table = "fantasy_matchup"


class FantasyLineupEntry(models.Model):
    team = models.ForeignKey(FantasyTeam)
    player = models.ForeignKey(Player)
    position = models.CharField(max_length=25, choices=LINEUP_POSITIONS)
    lineup_date = models.DateField()
    score = JSONField(null=True)
    scoring_completed_flag = models.BooleanField(default=False)

    def score_entry(self):
        if not self.scoring_completed_flag:
            # TODO: Add a flag or datetime field or something to prevent needlessly doing these
            # TODO: Calculations every time the method is called
            score_dict = defaultdict(Decimal)
            # game_log = PlayerGameLog.objects.filter(player=self.player,
            #                                         game_date=self.lineup_date)
            # if game_log.exists():
            pbs = PlayerTraditionalBoxScore.objects.filter(player=self.player,
                                                           game__game_date_est=
                                                           self.lineup_date).first()
            scoring_settings = self.team.league.scoringsettings
            model_fields_map = scoring_settings.get_model_fields_map(suffix="BoxScore")
            total_score = 0
            for model_name in model_fields_map:
                model = getattr(stats_models, model_name)
                fields = model_fields_map[model_name]
                if pbs is not None:
                    values = model.objects.filter(player=self.player,
                                                  game=pbs.game).values(*fields).first()
                else:
                    values = None
                for fld in fields:
                    coefficients = scoring_settings.scoring_fields_vals
                    key = model_name.replace("BoxScore", "") + "__" + fld
                    if values is not None:
                        score = values[fld] * Decimal(repr(coefficients[key]))
                        score_dict[key] = (values[fld], score)
                    else:
                        score_dict[key] = (0, 0)
                        score = 0
                    total_score += score
            score_dict['total'] = total_score
            self.score = simplejson.dumps(score_dict)
            if date.today() > self.lineup_date:
                self.scoring_completed_flag = True
            # Not too sure how I feel about calling self.save()
            self.save()

    class Meta:
        db_table = 'fantasy_lineup_entry'

