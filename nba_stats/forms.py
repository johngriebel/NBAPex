from django import forms
from datetime import date
from nba_stats.utils import make_season_str

PLAYER_SPLIT_TYPE_CHOICES = [("Traditional", "Traditional"),
                             ("Advanced", "Advanced"),
                             ("Misc", "Misc"),
                             ("Shooting", "Shooting"),
                             ("Usage", "Usage"),
                             ("Scoring", "Scoring")]
SEASON_CHOICES = [(str(year), make_season_str(year)) for year in range(1996, date.today().year)]


class GameUpdateForm(forms.Form):
    begin_date = forms.DateField()
    end_date = forms.DateField()


class SplitSearchForm(forms.Form):
    season_id = forms.ChoiceField(SEASON_CHOICES, required=False)
    season_type = forms.CharField(max_length=50, required=False, initial="Regular Season")
    split_type = forms.ChoiceField(PLAYER_SPLIT_TYPE_CHOICES, required=False)
    per_mode = forms.CharField(max_length=50, required=False, initial="PerGame")
    order_by = forms.CharField(max_length=50, required=False)


class UserQueryForm(forms.Form):
    pass
