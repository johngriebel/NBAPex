import logging
from django import template
from nba_fantasy.models import FantasyTeam
log = logging.getLogger('stats')

register = template.Library()


def getotherteams(team):
    other_teams = FantasyTeam.objects.filter(league=team.league).exclude(id=team.id)
    return other_teams


register.filter('getotherteams', getotherteams)
