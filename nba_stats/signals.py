import logging
from django.db import IntegrityError
from django.db.models.signals import m2m_changed
from nba_stats.models import Lineup
from nba_stats.utils import make_unique_filter_dict
log = logging.getLogger('stats')


def lineup_players_changed(sender, **kwargs):
    instance = kwargs.get('instance')
    if isinstance(instance, Lineup):
        if kwargs.get('action') == 'pre_remove':
            filter_dict = make_unique_filter_dict(instance.__class__, instance=instance)
            cur_pids = list(instance.players.all().values_list('id', flat=True).distinct())
            new_pids = list(kwargs.get('pk_set', set()))
            # TODO: Deal with cur_pids & new_pids having players in common
            all_pids = cur_pids + new_pids
            cur_lineups = instance.__class__.filter_on_players(all_pids, filter_dict)
            if cur_lineups.exists():
                raise IntegrityError("This lineup already exists!")


m2m_changed.connect(lineup_players_changed)
