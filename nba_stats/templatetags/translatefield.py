import logging
from django import template
log = logging.getLogger('stats')

register = template.Library()


def translatefield(field, translation="upper"):
    name = field.split("__")[-1].replace("_pct", "%").replace("_", " ")
    if translation.lower() == "upper":
        return name.upper()
    elif translation.lower() == "title":
        new_name = " ".join(part[0].upper() + part[1:] for part in name.split())
        return new_name


register.filter('translatefield', translatefield)
