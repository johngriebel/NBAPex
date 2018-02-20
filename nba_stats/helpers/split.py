import logging
from datetime import date
from nba_stats.models import (Player, Team, TraditionalSplit, AdvancedSplit, MiscSplit,
                              UsageSplit, ScoringSplit, ShootingSplit, TrackingBoxScore,
                              FourFactorsBoxScore, HustleStatsBoxScore)
from nba_stats.utils import (dictify, convert_dict_keys_to_lowercase, make_season_int,
                             get_json_response, make_season_str, make_unique_filter_dict)
from nba_stats.constants import (NBA_BASE_URL, GENERAL_SPLITS_PARMS, PLAYER_GENERAL_SPLITS_ENDPOINT,
                                 PLAYER_SHOOTING_SPLITS_ENDPOINT, TEAM_GEN_SPLITS_ENDPOINT,
                                 TEAM_SHOOTING_SPLITS_ENDPOINT)
log = logging.getLogger('stats')


# This is a beaut, if I do say so myself
def instantiate_correct_split_type(data):
    from nba_stats import models as nba_stats_models
    if "player" in data:
        entity_type = "Player"
    elif "team" in data:
        entity_type = "Team"
    else:
        raise Exception("Neither team nor player found in data")

    split_type = "Traditional" if data['measure_type'] == "Base" else data['measure_type']

    class_name = entity_type + split_type + "Split"
    model = getattr(nba_stats_models, class_name)
    # This removes all fields in the data dict that aren't actually in the model.
    # This is to account for differences in naming, cruft, etc. This may unintentionally cover up
    # Some mistakes.
    final_data = {field.name: data[field.name] for field in
                  model._meta.get_fields() if (field.name != 'id' and field.name in data)}

    try:
        find_args = make_unique_filter_dict(model, final_data)
    except Exception as e:
        log.debug(("INITIAL DATA", data))
        log.debug(("FINAL DATA ", final_data))
        log.debug(("CLASS NAME", class_name, "MODEL", model))
        log.exception(e)
        raise e
    try:
        split, created = model.objects.update_or_create(**find_args, defaults=final_data)
        if created:
            log.debug("Created a nwew split with the following params:")
            log.debug(find_args)
    except Exception as e:
        log.debug(("INITIAL DATA", data))
        log.debug(("FIND ARGS", find_args))
        log.debug(("MODEL", model))
        log.debug(("FINAL DATA", final_data))
        log.exception(e)
        raise e

    return split


def create_update_split_from_raw_json(entity, raw_json):
    splits = []
    if "Message" in raw_json.keys():
        # For whatever reason, certain combinations of measure/permode/year aren't available
        return []
    parms = raw_json['parameters']
    if "shooting" in raw_json['resource']:
        measure_type = "Shooting"
    else:
        measure_type = parms['MeasureType']
    result_sets = raw_json['resultSets']
    aux_ignore = ['OPP_PTS_2ND_CHANCE', 'PCT_PTS_2PT_MR']
    override = ['GROUP_SET', 'GROUP_VALUE', 'W', 'L']
    for rset in result_sets:
        rows = dictify(rset)
        for row in rows:
            if measure_type == "Misc":
                row['PTS_SECOND_CHANCE'] = row['PTS_2ND_CHANCE']
                row['OPP_PTS_SECOND_CHANCE'] = row['OPP_PTS_2ND_CHANCE']
            elif measure_type == "Scoring":
                row['PCT_PTS_2PT_MIDRANGE'] = row['PCT_PTS_2PT_MR']
            elif measure_type == "Shooting":
                if row['GROUP_SET'] == "Assisted By":
                    row['GROUP_VALUE'] = row['PLAYER_NAME']

            conv_data = convert_dict_keys_to_lowercase(row, override_list=override,
                                                       aux_list=aux_ignore)
            if isinstance(entity, Player):
                conv_data['player'] = entity
            elif isinstance(entity, Team):
                conv_data['team'] = entity
            conv_data['season_id'] = make_season_int(parms['Season'])
            conv_data['season_type'] = parms['SeasonType']
            conv_data['per_mode'] = parms['PerMode']
            conv_data['measure_type'] = measure_type
            # This if is the result of an impossible to reproduce scenario where we received
            # A phantom base split for Harrison barnes that said he played two games at starting
            # position 'None' in 2016-17. If you can figure it out, tell me.
            if conv_data['group_value'] is None:
                continue
            try:
                split = instantiate_correct_split_type(conv_data)
            except Exception as e:
                log.debug(("RAW PARMS", raw_json['parameters']))
                log.debug(("RAW RESOURCE ", raw_json['resource']))
                log.debug(("ROW", row))
                log.debug(("CONV DATA", conv_data))
                log.exception(e)
                raise e
            splits.append(split)

    return splits


def create_update_all_splits_for_entity(entity, year=None, season_type="Regular Season"):
    splits = {'Base': [], 'Advanced': [], 'Misc': [],
              'Scoring': [], 'Usage': [], 'Shooting': []}

    parms = GENERAL_SPLITS_PARMS
    if isinstance(entity, Player):
        parms['PlayerID'] = ent_nba_id = entity.player_id
        endpoint = PLAYER_GENERAL_SPLITS_ENDPOINT
        shooting_endpoint = PLAYER_SHOOTING_SPLITS_ENDPOINT
    elif isinstance(entity, Team):
        parms['TeamID'] = ent_nba_id = entity.team_id
        endpoint = TEAM_GEN_SPLITS_ENDPOINT
        shooting_endpoint = TEAM_SHOOTING_SPLITS_ENDPOINT
    else:
        raise Exception("What are you doing. This function requires a Player or Team.")

    # teams default to 1996-2015-16 season
    first_year = getattr(entity, 'from_year', None) or 1996
    first_year = 1996 if first_year < 1996 else first_year
    final_year = getattr(entity, 'to_year', None) or date.today().year

    if year is not None:
        if year < first_year or year > final_year:
            raise ValueError("You passed an invalid year: {yr}. "
                             "Year must be between {first} and {last} "
                             "for {ent}.".format(yr=year, first=first_year,
                                                 last=final_year, ent=str(entity)))
        else:
            first_year = year
            final_year = year + 1

    # Need to loop over every measure_type, per_mode, season, season_type
    # Could cut this down to Totals & Per100, then calculate everything else.
    # That cuts the requests in half. Could also jut get box scores, but I think that would
    # Make it tough (impossible) to get/do per possession data.
    for per_mode in ['Totals', 'Per100Possessions']:
        parms['PerMode'] = per_mode
        parms['SeasonType'] = season_type
        for cur_year in range(first_year, final_year):
            parms['Season'] = make_season_str(cur_year)
            # This is probably the most effective place to make a cut,
            # But I'm not sure if it can be done.
            for measure_type in ['Base', 'Advanced', 'Misc', 'Scoring', 'Usage']:
                parms['MeasureType'] = measure_type
                log.debug((ent_nba_id, cur_year, season_type, per_mode, measure_type))
                url = NBA_BASE_URL + endpoint
                # Temp. for Hornets
                try:
                    # This is where like 90% of the time is being spent
                    data = get_json_response(url, parms)
                except Exception as e:
                    log.exception(e)
                    continue
                entity_splits = create_update_split_from_raw_json(entity, data)
                splits[measure_type] += entity_splits
            url = NBA_BASE_URL + shooting_endpoint
            # I don't think this actually matters
            parms['MeasureType'] = "Base"
            data = get_json_response(url, parms)
            log.debug((ent_nba_id, cur_year, season_type, per_mode, "Shooting"))
            shooting_splits = create_update_split_from_raw_json(entity, data)
            splits['Shooting'] += shooting_splits

    return splits

# Normally I'd like this to be in utils, but it creates a circular import
split_models = [TraditionalSplit, AdvancedSplit, MiscSplit, UsageSplit, ScoringSplit, ShootingSplit,
                TrackingBoxScore, FourFactorsBoxScore, HustleStatsBoxScore]
# TODO: Is list.index() faster or slower than dict.get() ?
SPLIT_FIELD_ORDERING = []
for model in split_models:
    model_fields = [fld.name for fld in model._meta.get_fields()]
    SPLIT_FIELD_ORDERING += ["Player" + model.__name__.replace("Split", "").replace("BoxScore", "")
                             + "__" + field for field in model_fields]
