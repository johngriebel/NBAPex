import argparse
import django
import pandas as pd
django.setup()
from nba_py.team import TeamList
from nba_py.player import PlayerList
from nba_py.league import TeamStats
from nba_stats.models import *
from nba_stats.email_handler import EmailHandler
from nba_stats.helpers.player import create_update_all_seasons_for_player
from nba_stats.helpers.split import create_update_all_splits_for_entity
from nba_stats.helpers.team import (get_currently_active_teams,
                                    create_update_team_seasons)
from nba_stats.web_handlers.league_handler import (LeagueStatsHandler, LeaguePlayerTrackingHandler,
                                                   LineupHandler, GameLogHandler)
from nba_stats.web_handlers.player_handler import (PlayerTransactionHandler,
                                                   PlayerShotChartHandler,
                                                   PlayerHandler)
from nba_stats.web_handlers.team_handler import OnOffHandler, TeamHandler
from nba_stats.web_handlers.game_handler import (GameHandler, GameSummaryHandler,
                                                 BoxScoreHandler, PlayByPlayHandler)
from nba_stats.utils import *
from nba_stats.constants import *
__author__ = 'John Griebel'
log = logging.getLogger('stats')


parser = argparse.ArgumentParser(description="Data management for NBAPex. This is the script you'll"
                                             "want to run for any data creation or updating. In "
                                             "the future, deletion may be integrated here as well.")

parser.add_argument('command', choices=['teams', 'players', 'individuals', 'player_traditional',
                                        'team_seasons', 'shotcharts', 'coaches',
                                        'update_player_stats', 'update_team_stats',
                                        'update_leaguewide_stats', 'update_all'])
parser.add_argument('-begin-date', dest='begin_date',
                    help="Date should be entered in this format: YYYY-MM-DD.")
parser.add_argument('-end-date', dest='end_date',
                    help="Date should be entered in this format: YYYY-MM-DD.")
parser.add_argument('-year', dest="year",
                    help="Enter a year homie.")
parser.add_argument("-season_type", dest="season_type", default=REGULAR_SEASON)


args = parser.parse_args()
command = args.command
begin_date = None
end_date = None
kwargs = {}

if command == 'games':
    if args.begin_date is None or args.end_date is None:
        parser.error("The 'begin-date' and 'end-date' arguments are required when using the "
                     "'games' command.")
    else:
        begin_date_str = args.begin_date
        end_date_str = args.end_date
        begin_date_parts = [int(x) for x in begin_date_str.split("-")]
        end_date_parts = [int(x) for x in end_date_str.split("-")]
        begin_date = pd.datetime(year=begin_date_parts[0], month=begin_date_parts[1],
                                 day=begin_date_parts[2])
        end_date = pd.datetime(year=end_date_parts[0], month=end_date_parts[1],
                               day=end_date_parts[2])
        kwargs = {'begin_date': begin_date, 'end_date': end_date}
elif "update" in command:
    if args.year is None:
        parser.error("If you're trying to update, you need to enter a year!")
    else:
        kwargs['year'] = int(args.year)
        kwargs['season_type'] = args.season_type


def convert_season_type(season_type):
    if season_type == "Regular+Season":
        return "regular"
    else:
        return "post"


def seed_teams():
    log.debug("Seeding teams...")
    team_list = TeamList()
    tids = team_list.info()['TEAM_ID']
    count = 1
    tot = len(tids)
    teams = []
    for team_id in tids:
        log.debug("Working on team {c}/{t}".format(c=count,
                                                   t=tot))
        try:
            th = TeamHandler(team_id=team_id)
            team = th.team()
        except IndexError:
            log.debug(("Couldn't find info for team with id ", team_id))
            log.debug("Creating a dummy record")
            team = Team(team_id=team_id, city="Foo", name="Bar")
        teams.append(team)
        count += 1
    Team.objects.bulk_create(teams)
    log.debug("Finished seeding teams.")


def seed_players():
    log.debug("Seeding players...")
    player_list = PlayerList(only_current=0)
    cur = 1
    total = len(player_list.info())
    players_to_create = []
    all_pids = player_list.info()['PERSON_ID']
    for player_id in all_pids:
        player_handler = PlayerHandler(player=int(player_id))
        player_handler.fetch_raw_data()
        player_instance = player_handler.create_update_player()
        players_to_create.append(player_instance)
        log.debug(str(cur) + "/" + str(total) + " = " + str((cur/total) * 100) + "% done with players.")
        cur += 1
    Player.objects.bulk_create(players_to_create)
    log.debug("Finished seeding players.")


def seed_coaches():
    url = BBREF_BASE_URL + BBREF_NBA_COACH_LIST
    soup = get_beautiful_soup(url)
    table = soup.find("table", {'id': "coaches"})
    tbody = table.find('tbody')
    rows = tbody.find_all('tr')
    coach_seasons_to_create = []
    for row in rows:
        coach_data = extract_coach_data_from_bbref(row)
        if coach_data is None:
            continue
        log.debug(coach_data)
        coach_url = (BBREF_BASE_URL + BBREF_COACH_URL).format(coachid=coach_data['coach_id'])
        log.debug("Coach URL: " + coach_url)
        coach_soup = get_beautiful_soup(coach_url)
        info = coach_soup.find('div', {'id': 'info'})
        coach_data['birthdate'] = None

        relevant_info = info.find_all('p')[1]
        bdate = relevant_info.find('span', {'id': 'necro-birth'})
        if bdate:
            bd_parts = bdate.get('data-birth').split('-')
            coach_data['birthdate'] = date(year=int(bd_parts[0]),
                                           month=int(bd_parts[1]),
                                           day=int(bd_parts[2]))
        coach = Coach(**coach_data)
        coach.display_first_last = coach.first_name + " " + coach.last_name
        coach.save()

        stats_table = coach_soup.find('table', {'id': "coach-stats"})
        coach_seasons_to_create += extract_coach_stats_from_bbref(coach, stats_table)

    CoachSeason.objects.bulk_create(coach_seasons_to_create)


def seed_player_career_stats():
    log.debug("Seeding Player Career Stats.")
    players = Player.objects.filter(id__gt=1814).order_by('id')
    plr_count = players.count()
    cur = 0
    seasons_to_create = []
    for player in players:
        log.debug("Begin creating seasons for " + player.display_first_last)
        seasons_to_create += create_update_all_seasons_for_player(player)
        cur += 1
        # Still haven't gotten the last 5 players in the DB for whatever reason
        if cur % 20 == 0:
            # PlayerTraditionalSeason.objects.bulk_create(seasons_to_create)
            pct = (cur / plr_count) * 100
            pct_done = str(pct)[:4]
            log.debug("Completed {c}/{t} players. {p}% done.".format(c=cur, t=plr_count,
                                                                     p=pct_done))
            seasons_to_create = []


def seed_team_splits():
    log.debug("Seeding Team Splits")
    tids = TeamHistory.objects.filter(active_thru__gte=1996).values_list('team_id',
                                                                         flat=True).distinct()
    completed_teams = TeamShootingSplit.objects.values_list('team_id', flat=True).distinct('team_id')
    abbrevs = ["TOT", "EST", "WST"]
    teams = Team.objects.filter(id__in=tids).exclude(abbreviation__in=
                                                     abbrevs).exclude(id__in=
                                                                      completed_teams).order_by('id')
    team_count = teams.count()
    cur = 0

    for team in teams:
        log.debug("Begin creating splits for {c} {n}".format(c=team.city, n=team.name))
        team_splits = create_update_all_splits_for_entity(team)
        cur += 1
        log.debug("Beginning bulk create calls")
        for key in team_splits:
            splits = team_splits[key]
            if len(splits):
                cls = splits[0].__class__
                cls.objects.bulk_create(splits)

        pct = (cur / team_count) * 100
        pct_done = str(pct)[:4]
        log.debug("Completed {c}/{t} teams. {p}% done.".format(c=cur, t=team_count,
                                                               p=pct_done))


def update_player_stats(season, season_type=REGULAR_SEASON):
    log.debug("Updating player statistics for " + str(season))
    player_list = PlayerList()
    # Only gets active players
    person_ids = player_list.info()['PERSON_ID']
    cur = 1
    tot = len(person_ids)
    completed_pids = []
    try:
        for pid in person_ids:
            if pid in completed_pids:
                continue
            log.debug(("Working on player #", cur, "/", tot, ". ",
                       str(100 * (cur/tot))[:4], "% done."))
            player_handler = PlayerHandler(int(pid))
            player_handler.fetch_raw_data()
            player_handler.create_update_player()

            player = player_handler.player_instance

            log.debug(("Begin updating transactions for ", player.display_first_last))
            ptrans_handler = PlayerTransactionHandler(player)
            ptrans_handler.fetch_raw_data()
            ptrans_handler.transactions()

            completed_pids.append(pid)
            cur += 1

        lsh = LeagueStatsHandler()
        tracking_handler = LeaguePlayerTrackingHandler()

        for per_mode in [TOTALS, PER_POSSESSION, PER_PLAY]:
            for group_set in GROUP_SETS:
                for group_value in SET_TO_VALUES_MAP[group_set]:
                    log.debug((group_set, group_value))
                    if group_set.lower() == "month" and int(group_value) > 10:
                        log.debug("Month greater than 10, skipping.")
                    if group_value == "CUR_SEASON":
                        group_value = make_season_str(determine_season_for_date(date.today()))
                    for measure_type in MEASURE_TYPES:
                        if measure_type in ["Four Factors", "Opponent", "Defense"]:
                            continue
                        lsh.fetch_raw_data(measure_type=measure_type,
                                           per_mode=per_mode,
                                           group_set=group_set,
                                           group_value=group_value,
                                           season=season,
                                           season_type=season_type)
                        splits = lsh.splits()
                        log.debug("Just created or updated {x} splits".format(x=len(splits)))
                    if per_mode == TOTALS:
                        for pt_measure_type in PT_MEASURE_TYPES:
                            tracking_handler.fetch_raw_data(pt_measure_type=pt_measure_type,
                                                            per_mode=per_mode,
                                                            group_set=group_set,
                                                            group_value=group_value,
                                                            season=season,
                                                            season_type=season_type)
                            tracks = tracking_handler.tracking()
                            log.debug("Just created or updated {x} "
                                      "tracking records.".format(x=len(tracks)))

    except Exception as e:
        log.debug(("COMPLETED PIDS", completed_pids))
        log.exception(e)
        raise e
    return completed_pids


def update_team_stats(season=None, year=None, season_type=REGULAR_SEASON):
    if year is not None:
        season = LeagueSeason.objects.get(year=year)
    log.debug(("Updating team stats for ", season))
    lsh = LeagueStatsHandler()
    for per_mode in [TOTALS, PER_POSSESSION, PER_PLAY]:
        for group_set in GROUP_SETS:
            for group_value in SET_TO_VALUES_MAP[group_set]:
                log.debug((group_set, group_value))
                for measure_type in MEASURE_TYPES:
                    if measure_type == USAGE:
                        continue
                    lsh.fetch_raw_data(player_or_team=TeamStats,
                                       measure_type=measure_type,
                                       per_mode=per_mode,
                                       group_set=group_set,
                                       group_value=group_value,
                                       season=season,
                                       season_type=season_type)
                    splits = lsh.splits()
                    log.debug("Just created or updated {x} team splits".format(x=len(splits)))

    teams = get_currently_active_teams()
    cur = 1
    for team in teams:
        log.debug(("Working on ", team))
        log.debug((cur, "/", 30, " = ", str(100 * (cur/30))[:4], "% done."))
        create_update_team_seasons(team, season)

        on_off_handler = OnOffHandler(team)
        for mtype in MEASURE_TYPES:
            if mtype in [USAGE, DEFENSE]:
                continue
            for pmode in [TOTALS, PER_POSSESSION, PER_PLAY]:
                if mtype == SCORING:
                    continue
                on_off_handler.fetch_raw_data(measure_type=mtype,
                                              season=season,
                                              season_type=season_type,
                                              per_mode=pmode)
                on_off_handler.all()
        log.debug(("Done updating", team))
        cur += 1


def update_leaguewide_stats(season=None, year=None, season_type=REGULAR_SEASON):
    if year is not None:
        season = LeagueSeason.objects.get(year=year)
    log.debug(("Updating league wide stats for ", season))
    lineup_handler = LineupHandler()
    for mt in MEASURE_TYPES:
        if mt in [USAGE, DEFENSE]:
            continue
        for per_mode in [TOTALS, PER_POSSESSION, PER_PLAY]:
            for quant in range(2, 6):
                lineup_handler.fetch_raw_data(measure_type=mt,
                                              per_mode=per_mode,
                                              group_quantity=quant,
                                              season=season,
                                              season_type=season_type)
                lineup_handler.lineups()

    log.debug("Finished updating lineups")

    most_recent_game = Game.objects.filter(season=season).order_by('-game_date_est',
                                                                   '-game_sequence').first()
    if most_recent_game is None:
        start_date = season.regular_season_start_date
    else:
        start_date = most_recent_game.game_date_est + timedelta(days=1)

    end_date = season.playoffs_end_date or date.today()

    log.debug(("Game range to update: ", start_date, " - ", end_date))
    games = None
    for dt in pd.date_range(start=start_date, end=end_date):
        log.debug(("Beginning updates for games on ", dt))
        game_handler = GameHandler()
        games = game_handler.create_games(dt.date(), season)
        Game.objects.bulk_create(games)

        ostats = []
        oxs = []
        lscores = []

        btypes = ['Traditional', 'Advanced', 'Misc', 'Scoring',
                  'Usage', 'Tracking', 'Four Factors', 'Hustle']
        bscore_dict = {}
        for k in btypes:
            bscore_dict[k] = {'players': [], 'teams': []}

        pbp_events = []

        for game in games:
            summary_handler = GameSummaryHandler(game)
            summary_handler.fetch_raw_data()

            sup_game_info = summary_handler.game_info()
            for fld in sup_game_info:
                if fld == "game_time":
                    # The NBA is utterly moronic, so we have to do this to handle the case
                    # Where they sent us a timestamp such as 1:60; i.e. 1 hour 60 minutes.
                    hours, minutes = [int(p) for p in sup_game_info[fld].split(":")]
                    duration = timedelta(hours=hours, minutes=minutes)
                    setattr(game, fld, duration)
                    continue
                setattr(game, fld, sup_game_info[fld])
            game.save()

            ostats += summary_handler.other_stats()
            oxs += summary_handler.official_xrefs()
            lscores += summary_handler.line_scores()

            box_handler = BoxScoreHandler(game)
            box_handler.fetch_raw_data()
            for btype in btypes:
                boxes = box_handler.boxscore(btype)
                bscore_dict[btype]['players'] += boxes['players']
                bscore_dict[btype]['teams'] += boxes['teams']

            pbp_handler = PlayByPlayHandler(game)
            pbp_handler.fetch_raw_data()

            pbp_events += pbp_handler.play_by_play()

        GameOtherStats.objects.bulk_create(ostats)
        GameOfficialXref.objects.bulk_create(oxs)
        LineScore.objects.bulk_create(lscores)

        for btype in btypes:
            player_boxes = bscore_dict[btype]['players']
            team_boxes = bscore_dict[btype]['teams']

            if player_boxes:
                player_boxes[0].__class__.objects.bulk_create(player_boxes)
            if team_boxes:
                team_boxes[0].__class__.objects.bulk_create(team_boxes)

        PlayByPlayEvent.objects.bulk_create(pbp_events)
        log.debug(("Finished updates for all games on ", dt))

    if games is not None:
        game_log_handler = GameLogHandler()
        game_log_handler.fetch_raw_data(season=season,
                                        season_type=season_type)
        game_ids = games.values_list('game_id', flat=True)
        game_logs = game_log_handler.game_logs(game_ids=game_ids)
        PlayerGameLog.objects.bulk_create(game_logs)
    return games


def create_shotchart_details(season, players, game_ids=None):
    sc_handler = PlayerShotChartHandler()

    for player in players:
        log.debug(("Begin updating shot charts for ", player.display_first_last))

        sc_handler.fetch_raw_data(player=player,
                                  season=season)

        scdtls = sc_handler.shotcharts(game_ids=game_ids)
        log.debug(("Num shot chart details", len(scdtls)))

        log.debug(("Just created scdtls for ",
                   player.display_first_last))


def update_all(year, season_type=REGULAR_SEASON):
    log.debug("Updating all statistical data")
    season = LeagueSeason.objects.get(year=year)

    player_id_list = update_player_stats(season, season_type)
    players = Player.objects.filter(id__in=player_id_list)
    games = update_leaguewide_stats(season, season_type)
    game_ids = games.values_list('game_id', flat=True).distinct('game_id')
    update_team_stats(season)

    create_shotchart_details(season, players, game_ids)

    log.debug("Completed updating all statistical data")


def error_func():
    raise NotImplementedError("The doofus that wrote this program needs to implement"
                              " whatever it is you are trying to do.")

func_dict = {'teams': seed_teams,
             'players': seed_players,
             'coaches': seed_coaches,
             'player_traditional': seed_player_career_stats,
             'shotcharts': create_shotchart_details,
             'update_player_stats': update_player_stats,
             'update_team_stats': update_team_stats,
             'update_leaguewide_stats': update_leaguewide_stats,
             'update_all': update_all}

action_func = func_dict.get(command, error_func)

try:
    action_func(**kwargs)
except Exception as e:
    message = "Exception during execution of " + action_func.__name__ + ": " + str(e)
    log.exception(message)
    emailer = EmailHandler()
    subject = "Exception During NBAPex Update Process"
    logfile_name = log.handlers[0].baseFilename
    emailer.send_email(message=message,
                       subject=subject,
                       attachment_path=logfile_name)
    raise e
