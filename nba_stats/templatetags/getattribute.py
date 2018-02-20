import re
import logging
from django import template
from django.conf import settings
log = logging.getLogger('fantasy')
numeric_test = re.compile("^\d+$")
register = template.Library()


def getattribute(value, arg):
    log.debug(("OCTOPUS", value, arg))
    """Gets an attribute of an object dynamically from a string name"""
    if hasattr(value, str(arg)):
        return getattr(value, arg)
    elif isinstance(value, dict) and arg in value:
        return value[arg]
    elif numeric_test.match(str(arg)) and len(value) > int(arg):
        return value[int(arg)]
    else:
        return settings.TEMPLATE_STRING_IF_INVALID


register.filter('getattribute', getattribute)
