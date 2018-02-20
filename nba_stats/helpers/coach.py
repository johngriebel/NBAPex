import logging
from nba_stats.models import Coach, CoachSeason
from nba_stats.utils import extract_values, get_data_from_table_cell, make_season_int
from nba_stats.constants import BBREF_COACH_SEASON_DATA_FIELDS
log = logging.getLogger('stats')


def create_coach_from_web(c_id, attr):
    vals = extract_values(attrib=attr)
    names = vals[1].split(' ')
    log.debug(vals)
    if vals[10] == '':
        log.debug("No playoff games")
        coach = Coach(coach_id=c_id, first_name=names[0], last_name=names[1], display_first_last=vals[1],
                      from_year=vals[2], to_year=vals[3], years=vals[4], reg_season_games=vals[5],
                      reg_season_wins=vals[6], reg_season_losses=vals[7], reg_season_w_pct=vals[8], above_500=vals[9])
    else:
        if vals[14] == '' or vals[15] == '':
            if vals[13] == '':
                coach = Coach(coach_id=c_id, first_name=names[0], last_name=names[1], display_first_last=vals[1],
                              from_year=vals[2], to_year=vals[3], years = vals[4], reg_season_games=vals[5],
                              reg_season_wins=vals[6], reg_season_losses=vals[7], reg_season_w_pct=vals[8],
                              above_500=vals[9])
            else:
                coach = Coach(coach_id=c_id, first_name=names[0], last_name=names[1], display_first_last=vals[1],
                              from_year=vals[2], to_year=vals[3], years=vals[4], reg_season_games=vals[5],
                              reg_season_wins=vals[6], reg_season_losses=vals[7], reg_season_w_pct=vals[8],
                              above_500=vals[9], post_season_games=vals[10], post_season_wins=vals[11],
                              post_season_losses=vals[12], post_season_w_pct=vals[13])
        else:
            if vals[13] == '':
                coach = Coach(coach_id=c_id, first_name=names[0], last_name=names[1], display_first_last=vals[1],
                              from_year=vals[2], to_year=vals[3], years=vals[4], reg_season_games=vals[5],
                              reg_season_wins=vals[6], reg_season_losses=vals[7], reg_season_w_pct=vals[8],
                              above_500=vals[9], post_season_games=vals[10], post_season_wins=vals[11],
                              post_season_losses=vals[12], conference_champs=vals[14], league_champs=vals[15])
            else:
                coach = Coach(coach_id=c_id, first_name=names[0], last_name=names[1], display_first_last=vals[1],
                              from_year=vals[2], to_year=vals[3], years=vals[4], reg_season_games=vals[5],
                              reg_season_wins=vals[6], reg_season_losses=vals[7], reg_season_w_pct=vals[8],
                              above_500=vals[9], post_season_games=vals[10], post_season_wins=vals[11],
                              post_season_losses=vals[12], post_season_w_pct=vals[13], conference_champs=vals[14],
                              league_champs=vals[15])
    coach.save()


def extract_coach_data_from_bbref(table_row):
    coach_basic_info = table_row.find('td', {'data-stat': "coach"})
    # bbref splits up there tables w/ blank rows and headers in the middle for readability.
    # In that case, coach_basic_info will be None, so skip it.
    if coach_basic_info is None:
        return None

    coach_id = coach_basic_info.a.get('href')[9:-5]
    names = coach_basic_info.get_text().split()
    fname = names[0]
    lname = " ".join(names[1:])
    year_min = get_data_from_table_cell(table_row, "year_min")
    year_max = get_data_from_table_cell(table_row, "year_max")
    years = get_data_from_table_cell(table_row, "years")

    coach_data = {'coach_id': coach_id, 'first_name': fname, 'last_name': lname,
                  'year_min': year_min, 'year_max': year_max, 'years': years}

    return coach_data


def extract_coach_stats_from_bbref(coach, table):
    log.debug("Creating CoachSeasons for " + coach.display_first_last)
    coach_seasons = []
    rows = table.find('tbody').find_all('tr')

    for row in rows:
        # log.debug(row.prettify())
        try:
            season_id = make_season_int(row.find('th', {'data-stat': 'season'}).get_text())
            season_dict = {k: get_data_from_table_cell(row, k)
                           for k in BBREF_COACH_SEASON_DATA_FIELDS}
        except AttributeError as e:
            # An attribute indicates a season in which the coach was an assistant,
            # So while there is a table row present, there are not stats for that season
            continue
        season_dict['season_id'] = season_id
        season_dict['coach'] = coach
        coach_season = CoachSeason(**season_dict)
        coach_seasons.append(coach_season)
    return coach_seasons



