import logging

from datetime import date, timedelta
from requests import get
from django.apps import apps
from django.db.models.fields import IntegerField, FloatField, CharField, DecimalField
from bs4 import BeautifulSoup
from nba_stats import models as nba_stats_models
from nba_stats.constants import *
__author__ = 'John Griebel'

log = logging.getLogger('stats')


def extract_values(attrib):
    values = []
    for a in attrib:
        values.append(a.get_text())
    return values


# For right now I'm just going to append the two url halves. Will soon switch to something
# More modular.
def get_json_response(url, params={}):
    # Note: I've seen examples online that use a 'referrer' element in the headers.
    # So far I've had success without that. Not too sure what's going on there.
    response = get(url, params=params, headers=HEADERS)
    json_response = response.json()
    return json_response


def get_beautiful_soup(url):
    response = get(url)
    html = response.text
    soup = BeautifulSoup(html, 'html5lib')
    return soup


def is_player_row(tag):
    return tag.name == "tr" and (tag.attrs.get('class') not in [["over_header"],
                                                                ["thead"],
                                                                ["over_header", "thead"]])


def get_data_from_table_cell(row, stat):
    # HACK
    val = row.find('td', {'data-stat': stat}).get_text()
    if val =='':
        val = 0
    return val


def convert_height_to_int(height_string):
    if len(height_string) > 0:
        vals = height_string.split('-')
        return 12 * int(vals[0]) + int(vals[1])
    return 0


def convert_datetime_string_to_date_instance(date_string):
    # Chomps off the end of the string which is universally 'T00:00:00'
    if date_string:
        vals = date_string[:10].split('-')
        return date(int(vals[0]), int(vals[1]), int(vals[2]))


def convert_date_string_to_instace(date_string):
    """Mar 25, 2016 -> date(year=2016, month=3, day=25)"""
    date_parts = date_string.replace(",", "").split()
    month = MONTHS[date_parts[0].lower()]
    date_instance = date(year=int(date_parts[2]), month=month, day=int(date_parts[1]))
    return date_instance


def make_season_int(season):
    if type(season) == str:
        return int(season.split("-")[0])
    else:
        return season


def make_season_str(year):
    # for some reason year is getting passed as a str???
    # Don't know why, but for now just make it work
    year = int(year)
    if year == 1999:
        return "1999-00"
    suf = int(str(year)[2:])
    suf += 1
    if 2000 <= year <= 2008:
        return "%s-%s" % (str(year), str(suf).rjust(2, '0'))
    return "%s-%s" % (str(year), str(suf))


def determine_season_for_date(the_date):
    year = the_date.year - 1 if the_date.month < 7 else the_date.year
    return year


def dictify(result_set, include_name=False):
    dicts_list = []
    for row in result_set['rowSet']:
        detail_dict = dict(zip(result_set['headers'], row))
        if include_name:
            detail_dict['name'] = result_set['name']
        dicts_list.append(detail_dict)

    return dicts_list


def get_model(prefix="", middle="", suffix=""):
    if not any([prefix, middle, suffix]):
        raise Exception("What are you doing? You have to pass at least one non-empty argument.")

    class_name = prefix + middle + suffix
    model = getattr(nba_stats_models, class_name.replace(" ", ""))
    return model


def convert_colon_tstamp_to_duration(tstamp):
    duration = None
    if tstamp and type(tstamp) is str:
        hours, minutes = tstamp.split(":")
        duration = timedelta(hours=int(hours), minutes=int(minutes))

    return duration


def convert_dict_keys_to_lowercase(data, isgame=False, override_list=[], aux_list=[]):
    ret_dict = {}
    keys_to_ignore = ["GROUP_SET", "GROUP_VALUE", "CFID", "CFPARAMS", "TEAM_ID", "PLAYER_ID", "AGE",
                      "HOME_TEAM_ID", "VISITOR_TEAM_ID", "TO", "PLAYER1_ID", "PLAYER2_ID",
                      "PLAYER3_ID", "PLAYER1_TEAM_ID", "PLAYER2_TEAM_ID", "PLAYER3_TEAM_ID",
                      "DLEAGE_FLAG", "GAMES_PLAYED_FLAG", 'W', 'L', "SEASON_YEAR", "PCT",
                      "PERSON_ID", "DREB_PCT1", "Team_ID", "PLAYER_NAME", "LEAGUE_ID",
                      "PTS_2ND_CHANCE"] + aux_list
    if not isgame:
        keys_to_ignore.append("GAME_ID")

    for k, v in data.items():
        if ("RANK" not in k and k not in keys_to_ignore) or k in override_list:
            ret_dict[k.lower()] = v
        elif k == 'AGE':
            ret_dict['player_age'] = v
        elif k == 'TO':
            ret_dict['tov'] = v
        elif k == 'PERSON_ID':
            ret_dict['player_id'] = v
        elif k == 'PCT':
            ret_dict['w_pct'] = v
    return ret_dict


def convert_min_sec_to_float(min_sec):
    if not min_sec:
        return 0
    if isinstance(min_sec, int):
        return min_sec
    minutes, seconds = min_sec.split(":")
    return int(minutes) + (int(seconds)/60)


def auto_strip_and_convert_fields(model, data, uppercase=False, make_instance=True):
    # I'm sure there is a more elegant way to do this
    if uppercase:
        final_data = {field.name: data[field.name.upper()] for field in
                      model._meta.get_fields()
                      if (field.name != 'id' and field.name.upper() in data)}
    else:
        final_data = {field.name: data[field.name] for field in
                      model._meta.get_fields() if (field.name != 'id' and field.name in data)}
    if make_instance:
        model_obj = model(**final_data)
        return model_obj
    else:
        return final_data


def replace_special_chars(mod_str):
    special_chars = ["\n", "\t", "\r"]
    for char in special_chars:
        mod_str = mod_str.replace(char, "")

    return mod_str


def convert_salary_to_int(salary):
    raw_str = salary.replace("$", "").replace(",", "")
    return int(raw_str)


def get_default_display_fields(model, exclude=list):
    default_exclude = ["season_id"]
    fields = [f.name for f in model._meta.get_fields() if (type(f) in [IntegerField, FloatField, DecimalField]
                                                           and f.name
                                                           not in default_exclude + exclude)]
    return fields


def get_field_literals(fields):
    literals = []
    for field in fields:
        if field not in literals:
            literals.append(field.replace("_pct", "%").replace("_", " ").upper())
    return literals


def get_user_exposed_models():
    exposed_models = [model for model in apps.get_app_config('nba_stats').get_models()
                      if model.user_exposed]
    return exposed_models


def get_user_exposed_model_fields(model, translation_style="title", exclude=[]):
    # Very similar to get_default_display_fields. Consider merging?
    all_fields = model._meta.get_fields()
    fields = []
    ignore = ["create_ts", "create_user", "mod_ts", "mod_user"] + exclude
    for field in all_fields:
        field_type = field.__class__.__name__
        if (field_type not in ["ManyToOneRel", "AutoField", "ManyToManyRel"]
            and field.name not in ignore):
            field_info = {'model_name': model.__name__,
                          'field_name': field.name,
                          'field_type': field_type.replace("Field", ""),
                          'display_value': translate_field(field.name,
                                                           translation=translation_style)}
            fields.append(field_info)

    return fields


def translate_field(field, translation="upper"):
    name = field.replace("_pct", "%").replace("_", " ").replace("id", "").replace("abbreviation",
                                                                                  "")
    name = name.replace("player", "")
    if translation.lower() == "upper":
        return name.upper()
    elif translation.lower() == "title":
        new_name = " ".join(part[0].upper() + part[1:] for part in name.split())
        return new_name


def make_unique_filter_dict(model, data=None, instance=None):
    if (data is None and instance is None) or (data is not None and instance is not None):
        raise ValueError("You must pass exactly one of data or instance")

    if hasattr(model, "unique_together"):
        # In the case of Lineup and its children, we've had to use a hack
        # To get around the uniqueness constraint, and just made unique_together
        # a class attribute
        unique_fields = model.unique_together
    else:
        unique_fields = model._meta.unique_together[0]

    if data:
        filter_dict = {fld: data[fld] for fld in unique_fields}
    else:
        filter_dict = {fld: getattr(instance, fld) for fld in unique_fields}

    if "season_type" in filter_dict:
        new_season_type = filter_dict['season_type']
        for junk_str in [" ", "Career", "Totals", "Season"]:
            new_season_type = new_season_type.replace(junk_str, "")

        filter_dict['season_type'] = new_season_type
    return filter_dict

