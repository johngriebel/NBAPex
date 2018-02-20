import logging
import simplejson
import math
from collections import OrderedDict
from datetime import date
from django.core import serializers
from django.db.models import Min, Max
from django.http import JsonResponse
from nba_stats.models import (PlayerShotChartDetail, Team, Player,
                              RosterEntry, TeamColorXref, UserExposedModel)
from nba_stats.helpers.roster import get_roster_on_date, get_prev_roster_entry
from nba_stats.helpers.transaction import get_transaction_for_roster_entry
from nba_stats.utils import (get_user_exposed_model_fields, get_model)
from nba_stats.constants import TRANSACTION_COLORS
log = logging.getLogger('stats')


def get_player_shot_chart_data(request):
    player_id = request.GET.get('player_id')
    season_id = request.GET.get('season_id')
    log.debug(("player id", player_id, "season", season_id))
    scdtls = PlayerShotChartDetail.objects.filter(player__id=player_id)
    raw_data = simplejson.loads(serializers.serialize('json', scdtls, fields=("loc_x", "loc_y",
                                                                        "shot_made_flag",
                                                                        "game_date")))
    data = [entry['fields'] for entry in raw_data]
    return JsonResponse(data, safe=False)


def get_team_roster_history(request):
    team_id = request.GET.get("team_id")
    raw_date = request.GET.get("date")
    date_parts = [int(part) for part in raw_date.split("/")]
    the_date = date(month=date_parts[0], day=date_parts[1], year=date_parts[2])
    team = Team.objects.get(id=team_id)

    roster_entries = get_roster_on_date(team, the_date)
    pids = roster_entries.values_list('player_id', flat=True).distinct('player_id')
    players = Player.objects.filter(id__in=pids)

    min_date = roster_entries.aggregate(Min('acquisition_date'))['acquisition_date__min']
    max_date = roster_entries.aggregate(Max('acquisition_date'))['acquisition_date__max']
    x_scale = (max_date - min_date).days
    log.debug(("X scale ", x_scale))

    all_entries = RosterEntry.objects.filter(player__in=players, acquisition_date__gte=min_date)

    nodes = []
    links = []
    player_y_pos_map = {}
    cur_y = 0

    for ros in all_entries:
        end_date = ros.end_date if ros.end_date else date.today()
        duration = (end_date - ros.acquisition_date).days or 1
        scaled_duration = math.log2(duration) * 1.5

        x_pos = ((ros.acquisition_date - min_date).days / x_scale) * 0.75
        log.debug(("X pos ", x_pos))

        if not (ros.player.id in player_y_pos_map):
            player_y_pos_map[ros.player.id] = cur_y
            cur_y += 1
        y_pos = player_y_pos_map[ros.player.id]
        log.debug(("Y pos", cur_y))
        team_string = "Free Agency"
        color = "#ff33cc"
        if ros.team:
            team_string = ros.team.city + " " + ros.team.name
            color = TeamColorXref.objects.get(team=ros.team, order=0).hex_str

        ros_date = {'id': ros.player.id,
                    'player': ros.player.display_first_last,
                    'team': team_string,
                    'acquired_via': ros.acquired_via,
                    'acquisition_date': ros.acquisition_date,
                    'end_date': ros.end_date if ros.end_date else "",
                    'duration': scaled_duration,
                    'x_pos': x_pos,
                    'y_pos': y_pos,
                    'color': color}

        nodes.append(ros_date)

        prev_roster_entry = get_prev_roster_entry(ros)
        if prev_roster_entry is not None:
            prev_x = ((prev_roster_entry.acquisition_date - min_date).days / x_scale) * 0.75
        else:
            prev_x = 0

        log.debug(("prev_x", prev_x))

        transaction = get_transaction_for_roster_entry(ros)
        tsact = {'player': transaction.player.display_first_last,
                 'date': transaction.transaction_date,
                 'from_team': getattr(transaction.from_team, "abbreviation", "Draft/FA"),
                 'to_team': getattr(transaction.to_team, "abbreviation", "Draft/FA"),
                 'description': transaction.description,
                 'x1': prev_x,
                 'y1': y_pos,
                 'x2': x_pos,
                 'y2': y_pos,
                 'color': TRANSACTION_COLORS[transaction.transaction_type]}

        links.append(tsact)

    data = {'nodes': nodes, 'links': links}
    return JsonResponse(data, safe=False)


def ajax_get_related_models(request):
    model_name = request.GET.get('model')
    svg_nodes = []
    svg_links = []
    # Temp for now:
    cur_group_count = 1
    model = get_model(middle=model_name)
    log.debug(("Getting related models for ", model))
    related_models = [rel for rel in model.get_related_models(app_names=["nba_stats"])]
    fields = {}
    groups_dict = {}
    for rel_model in related_models:
        # Note: This only grabs the first parent defined in models.py.
        # Because of this, I'm not sure it works in 100% of cases right now.
        # Additionally, it forces us to be careful with our model definitions
        parent_model = rel_model.__base__
        log.debug(("ZEBRA", rel_model, parent_model))
        fields[rel_model.__name__] = get_user_exposed_model_fields(rel_model)

        if parent_model not in groups_dict:
            log.debug((parent_model, " not in groups dict yet. adding it as group no. ",
                       cur_group_count))
            groups_dict[parent_model] = cur_group_count
            if parent_model != UserExposedModel:
                svg_nodes.append({'id': parent_model.__name__, 'group': cur_group_count})
                svg_links.append({'source': parent_model.__name__,
                                  'target': model_name, 'value': 3})
            cur_group_count += 1

        group = groups_dict[parent_model]

        svg_nodes.append({'id': rel_model.__name__, 'group': group})

        if parent_model != UserExposedModel:
            svg_links.append({'source': rel_model.__name__,
                              'target': parent_model.__name__, 'value': 2})

    related_models = [rel.__name__ for rel in related_models]
    data = {'related': related_models, 'fields': fields,
            'nodes': svg_nodes, 'links': svg_links}
    return JsonResponse(data)


# TODO: Optimize this for performance
def ajax_send_user_query(request):

    primary_model_name = request.GET.get('primary_model_name')
    model = get_model(middle=primary_model_name)

    filters = simplejson.loads(request.GET.get('filters_list'))
    filter_dict = {}

    for user_qry in filters:
        table_field = user_qry['table_field'].lower()
        log.debug(table_field)
        table, field = table_field.split("__")

        if table != model.__name__.lower():
            field = table_field

        operator = user_qry['operator']
        input_val = user_qry['input_val']

        final_field = field + "__" + operator
        filter_dict[final_field] = input_val

    raw_fields_str = request.GET.get('fields_wanted')
    fields_wanted = raw_fields_str.lstrip("[").rstrip("]").replace('"', "").split(",")

    serialize_fields = []
    for field in fields_wanted:
        log.debug(("field wanted ", field))
        table, sub_field = [x.lower() for x in field.split("__")]
        if table == model.__name__.lower():
            field_to_add = sub_field
        else:
            field_to_add = field.lower()
        log.debug(("field as it is being add ", field_to_add))
        serialize_fields.append(field_to_add.lower())

    qry_result = model.objects.filter(**filter_dict).values(*serialize_fields)
    results_list = []
    for result in qry_result:
        ordered_result_dict = OrderedDict()
        for field in serialize_fields:
            val = str(result[field]) if isinstance(result[field], date) else result[field]
            ordered_result_dict[field] = val
        results_list.append(ordered_result_dict)

    data = simplejson.dumps(results_list)
    request.session['user_query_data'] = data

    return JsonResponse(data, safe=False)


def ajax_get_player_splits(request):
    log.debug("In get plyer splits")
    split_type = request.GET.get('split_type')
    filter_dict = {k: request.GET.get(k) for k in request.GET if k not in['split_type',
                                                                          'entity_id']}
    filter_dict['player_id'] = request.GET.get('entity_id')
    log.debug(filter_dict)
    model = get_model(prefix="Player", middle=split_type, suffix="Split")
    splits = model.objects.filter(**filter_dict).order_by('season_id')
    model_fields_dict = get_user_exposed_model_fields(model, translation_style="upper",
                                                      exclude=[k for k in filter_dict] +
                                                              ['measure_type', 'player',
                                                               'season_id'])
    serialize_fields = [d['field_name'] for d in model_fields_dict]
    raw_data = simplejson.loads(serializers.serialize('json', splits, fields=serialize_fields))
    splits_json = [entry['fields'] for entry in raw_data]
    data = {'model_fields': model_fields_dict, 'splits': splits_json}
    return JsonResponse(data)


def ajax_get_team_splits(request):
    log.debug("In get team splits")
    split_type = request.GET.get('split_type')
    filter_dict = {k: request.GET.get(k) for k in request.GET if k not in ['split_type',
                                                                           'entity_id']}
    filter_dict['team_id'] = request.GET.get('entity_id')
    log.debug(filter_dict)
    model = get_model(prefix="Team", middle=split_type, suffix="Split")
    splits = model.objects.filter(**filter_dict).order_by('season_id')
    model_fields_dict = get_user_exposed_model_fields(model, translation_style="upper",
                                                      exclude=[k for k in filter_dict] +
                                                              ['measure_type', 'season_id',
                                                               'team'])
    serialize_fields = [d['field_name'] for d in model_fields_dict]
    raw_data = simplejson.loads(serializers.serialize('json', splits, fields=serialize_fields))
    splits_json = [entry['fields'] for entry in raw_data]
    data = {'model_fields': model_fields_dict, 'splits': splits_json}
    return JsonResponse(data)
