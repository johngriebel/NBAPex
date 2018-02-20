from datetime import date
from django.db import models
from nba_stats.utils import determine_season_for_date


class ActivePlayersManager(models.Manager):
    def get_queryset(self):
        current_season = determine_season_for_date(date.today())
        return super(ActivePlayersManager, self).get_queryset().filter(to_year=current_season)