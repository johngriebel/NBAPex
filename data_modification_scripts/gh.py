# QUICK test file. DO NOT COMMIT
import logging
import django
django.setup()
from datetime import date
from nba_stats.models import *
from nba_stats.web_handlers.game_handler import (GameHandler, GameSummaryHandler, BoxScoreHandler,
                                                 PlayByPlayHandler)
log = logging.getLogger('stats')
try:
    gameday = date(year=2017, month=2, day=8)
    gh = GameHandler()
    games = gh.create_games(scoreboard_date=gameday)
    Game.objects.bulk_create(games)

    for game in games:
        gsh = GameSummaryHandler(game=game)
        gsh.fetch_raw_data()
        ostats = gsh.other_stats()
        osxrefs = gsh.official_xrefs()
        ginfo = gsh.game_info()
        lscores = gsh.line_scores()

        GameOtherStats.objects.bulk_create(ostats)
        GameOfficialXref.objects.bulk_create(osxrefs)
        LineScore.objects.bulk_create(lscores)

        box_handler = BoxScoreHandler(game=game)
        box_handler.fetch_raw_data()
        trad = box_handler.boxscore("Traditional")
        adv = box_handler.boxscore("Advanced")
        misc = box_handler.boxscore("Misc")
        scoring = box_handler.boxscore("Scoring")
        # Usage, Tracking, FourFactors, Hustle
        usg = box_handler.boxscore("Usage")
        track = box_handler.boxscore("Tracking")
        four = box_handler.boxscore("FourFactors")
        hustle = box_handler.boxscore("Hustle")

        PlayerTraditionalBoxScore.objects.bulk_create(trad['players'])
        TeamTraditionalBoxScore.objects.bulk_create(trad['teams'])

        PlayerHustleStatsBoxScore.objects.bulk_create(hustle['players'])
        TeamHustleStatsBoxScore.objects.bulk_create(hustle['teams'])

        pbph = PlayByPlayHandler(game=game)
        pbph.fetch_raw_data()
        pbp_events = pbph.play_by_play()
        PlayByPlayEvent.objects.bulk_create(pbp_events)

except Exception as e:
    log.exception(e)
    raise e