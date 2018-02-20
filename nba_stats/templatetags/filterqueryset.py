import logging
from django import template

log = logging.getLogger('stats')
register = template.Library()


def filterqueryset(qs, week):
    log.debug(("qs", qs))
    log.debug(("week", week))

    return qs.filter(week_num=week)


register.filter('filterqueryset', filterqueryset)
