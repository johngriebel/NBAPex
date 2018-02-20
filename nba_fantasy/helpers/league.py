import logging
from datetime import timedelta, date
from random import randint, sample
from nba_fantasy.models import (FantasyTeam, FantasyMatchup)
from nba_fantasy.constants import (ROTISSERIE, HEAD_TO_HEAD, SNAKE, SALARY_CAP)

log = logging.getLogger('fantasy')


def _get_nonequal_ints(low, high):
    x = randint(low, high)
    y = randint(low, high)
    while x == y:
        y = randint(low, high)

    return (x, y)


# For now assuming an even number of teams & H2H schedule.
def create_schedule(league):
    schedule_settings = ScheduleSettings.objects.get(league=league)
    teams = list(FantasyTeam.objects.filter(league=league))
    end_week = schedule_settings.start_week + (schedule_settings.reg_season_matchups *
                                               schedule_settings.weeks_per_matchup)
    for week in range(schedule_settings.start_week, end_week, schedule_settings.weeks_per_matchup):
        start_date = league.season_start_date + timedelta(weeks=week)
        end_date = start_date + timedelta(weeks=schedule_settings.weeks_per_matchup)
        # This doesn't really seem to give that random of results
        home_teams = set(sample(teams, len(teams) // 2))
        away_teams = set(teams) - home_teams
        for home_tm in home_teams:
            away_tm = away_teams.pop()

            matchup = FantasyMatchup(league=league,
                                     home_team=home_tm,
                                     away_team=away_tm,
                                     begin_date=start_date,
                                     end_date=end_date,
                                     week_num=week)
            matchup.save()


def validate_transaction_settings(data):
    success = True
    message = ""
    if data.get('use_waivers_flag'):
        if data.get('waiver_period') == 0:
            success = False
            message = "If you are using waivers, the waiver period must be set to at least one day."
    else:
        if data.get('waiver_period') != 0:
            success = False
            message = "If you are not using waivers, the waiver period must be set to zero days."
    if data.get('season_acquisition_limit'):
        if data.get('trade_limit', 0) > data.get('season_acquisition_limit'):
            success = False
            message = ("The trade limit must be less than or equal to the "
                       "total season acquisition limit.")

    if data.get('keepers_flag') and data.get('max_keepers') == 0:
        success = False
        message = "If you're using keepers, you must allow at least one player to be kept."
    if data.get('max_keepers') > 0 and not data.get('keepers_flag'):
        success = False
        message = ("If your league doesn't use keepers, "
                   "you can't set a max number of keeper players!")

    return success, message


def validate_schedule_settings(data):
    success = True,
    message = ""

    if data.get('schedule_type') == ROTISSERIE:
        if (data.get('weeks_per_matchup') or data.get('reg_season_matchups') or
                data.get('num_playoff_teams')):
            success = False
            message = ("Weeks Per Matchup, Num. Regular season matchups, and number of playoff "
                       "team should not be set for rotisserie schedules.")
    elif data.get('schedule_type') == HEAD_TO_HEAD:
        # TODO
        pass
    else:
        success = False
        message = "Invalid schedule type"

    return success, message


def validate_draft_settings(data):
    success = True
    message = ""

    if data.get('draft_date') < date.today():
        success = False
        message = "You can't create or edit a draft set in the past."

    elif data.get('draft_type') == SNAKE:
        if data.get('salary_cap') != 0:
            success = False
            message = "Snake draft leagues don't have a salary cap."
        elif data.get('seconds_per_pick') == 0:
            success = False
            message = "You must set a valid pick time for a snake draft."

    elif data.get('draft_type') == SALARY_CAP:
        if data.get('salary_cap') == 0:
            success = False
            message = "You must set a non-zero salary cap."
        elif data.get('seconds_per_pick') != 0:
            success = False
            message = "Salary Cap leagues can't have seconds per pick set."
    else:
        success = False
        message = "Invalid draft type selection."

    return success, message
