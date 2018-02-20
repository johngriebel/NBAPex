from django import forms
from django.forms import ModelForm, Form
from nba_stats.models import (TraditionalSplit, AdvancedSplit, MiscSplit,
                              ScoringSplit, UsageSplit, TrackingBoxScore,
                              FourFactorsBoxScore, HustleStatsBoxScore)
from nba_fantasy.models import FantasyTeam
from nba_fantasy.constants import (LINEUP_CHANGE_CHOICES, SCHEDULE_TYPE_CHOICES,
                                   DRAFT_TYPE_CHOICES, SCORING_TYPE_CHOICES)


class FantasyLeagueForm(Form):
    name = forms.CharField(max_length=100)
    num_teams = forms.IntegerField()
    private_flag = forms.BooleanField()
    season_start_date = forms.DateField(required=False, widget=forms.SelectDateWidget(years=[2016, 2017]))


class TransactionSettingsForm(Form):
    lineup_changes = forms.ChoiceField(LINEUP_CHANGE_CHOICES)
    use_waivers_flag = forms.BooleanField()
    waiver_period = forms.IntegerField(initial=0)
    season_acquisition_limit = forms.IntegerField(initial=0)
    trade_limit = forms.IntegerField(initial=0)
    trade_deadline = forms.DateField(required=False, widget=forms.SelectDateWidget(years=[2016, 2017]))
    trade_review_period = forms.DurationField(required=False)
    veto_votes_reqd = forms.IntegerField(initial=0)
    keepers_flag = forms.BooleanField()
    max_keepers = forms.IntegerField(initial=0)


class ScheduleSettingsForm(Form):
    schedule_type = forms.ChoiceField(SCHEDULE_TYPE_CHOICES)
    start_week = forms.IntegerField(initial=0)
    weeks_per_matchup = forms.IntegerField(initial=1)
    reg_season_matchups = forms.IntegerField(initial=19)
    num_playoff_teams = forms.IntegerField(initial=4)


class DraftSettingsForm(Form):
    draft_type = forms.ChoiceField(DRAFT_TYPE_CHOICES)
    draft_date = forms.DateTimeField(required=False, widget=forms.SelectDateWidget(years=[2016, 2017]))
    salary_cap = forms.IntegerField(initial=0)
    seconds_per_pick = forms.IntegerField(initial=0)


class ScoringSettingsForm(Form):
    scoring_type = forms.ChoiceField(SCORING_TYPE_CHOICES)


class RosterSettingsForm(Form):
    point_guard = forms.IntegerField(initial=0)
    shooting_guard = forms.IntegerField(initial=0)
    small_forward = forms.IntegerField(initial=0)
    power_forward = forms.IntegerField(initial=0)
    center = forms.IntegerField(initial=0)
    guard = forms.IntegerField(initial=0)
    forward = forms.IntegerField(initial=0)
    wing = forms.IntegerField(initial=0)
    big = forms.IntegerField(initial=0)
    util = forms.IntegerField(initial=0)
    inj = forms.IntegerField(initial=0)
    bench = forms.IntegerField(initial=0)


class BaseScoringForm(Form):
    gp = forms.IntegerField(label="Games Played", required=False)
    w = forms.IntegerField(label="Wins", required=False)
    l = forms.IntegerField(label="Losses", required=False)
    w_pct = forms.FloatField(label="Win Pct", required=False)
    min = forms.FloatField(label="Minutes", required=False)


class TraditionalScoringForm(Form):
    def __init__(self, *args, **kwargs):
        super(TraditionalScoringForm, self).__init__(*args, **kwargs)
        for mfield in TraditionalSplit._meta.get_fields():
            self.fields["PlayerTraditional__" + mfield.name] = forms.FloatField(required=False)


class AdvancedScoringForm(Form):
    def __init__(self, *args, **kwargs):
        super(AdvancedScoringForm, self).__init__(*args, **kwargs)
        for mfield in AdvancedSplit._meta.get_fields():
            if mfield.name != "min":
                self.fields["PlayerAdvanced__" + mfield.name] = forms.FloatField(required=False)


class MiscScoringForm(Form):
    def __init__(self, *args, **kwargs):
        super(MiscScoringForm, self).__init__(*args, **kwargs)
        for mfield in MiscSplit._meta.get_fields():
            self.fields["PlayerMisc__" + mfield.name] = forms.FloatField(required=False)


class ScoringScoringForm(Form):
    def __init__(self, *args, **kwargs):
        super(ScoringScoringForm, self).__init__(*args, **kwargs)
        for mfield in ScoringSplit._meta.get_fields():
            self.fields["PlayerScoring__" + mfield.name] = forms.FloatField(required=False)


class UsageScoringForm(Form):
    def __init__(self, *args, **kwargs):
        super(UsageScoringForm, self).__init__(*args, **kwargs)
        for mfield in UsageSplit._meta.get_fields():
            self.fields["PlayerUsage__" + mfield.name] = forms.FloatField(required=False)


class TrackingScoringForm(Form):
    def __init__(self, *args, **kwargs):
        super(TrackingScoringForm, self).__init__(*args, **kwargs)
        for mfield in TrackingBoxScore._meta.get_fields():
            self.fields["PlayerTracking__" + mfield.name] = forms.FloatField(required=False)


class FourFactorsScoringForm(Form):
    def __init__(self, *args, **kwargs):
        super(FourFactorsScoringForm, self).__init__(*args, **kwargs)
        for mfield in FourFactorsBoxScore._meta.get_fields():
            self.fields["PlayerFourFactors__" + mfield.name] = forms.FloatField(required=False)


class HustleScoringForm(Form):
    def __init__(self, *args, **kwargs):
        super(HustleScoringForm, self).__init__(*args, **kwargs)
        for mfield in HustleStatsBoxScore._meta.get_fields():
            self.fields["PlayerHustleStats__" + mfield.name] = forms.FloatField(required=False)


class FantasyTeamForm(ModelForm):
    class Meta:
        model = FantasyTeam
        exclude = ['league', 'owner', 'games', 'wins', 'losses', 'ties', 'win_pct', 'players']


class LoginForm(forms.Form):
    username = forms.CharField(max_length=100)
    password = forms.CharField(widget=forms.PasswordInput())
