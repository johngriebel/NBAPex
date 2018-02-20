import logging
from django import template
from django.conf import settings

log = logging.getLogger('stats')

register = template.Library()


def getrelatedset(obj, args):
    related_field, qry = args.split(",")
    qry_str, *vals = qry.split("=")
    filter_dict = {qry_str: eval(vals[0])}
    log.debug(("filter dict", filter_dict))
    related_field += "_set"

    if hasattr(obj, str(related_field)):
        relation = getattr(obj, related_field)
        return relation.filter(**filter_dict)
    else:
        return settings.TEMPLATE_STRING_IF_INVALID


register.filter('getrelatedset', getrelatedset)
