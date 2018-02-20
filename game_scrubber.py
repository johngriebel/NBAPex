__author__ = 'jgriebel'
import argparse
import django
import pandas as pd
django.setup()
from nba_stats.models import *

parser = argparse.ArgumentParser(description="Delete games and all relevant information from the "
                                             "database because something went wrong during data"
                                             "creation.")
parser.add_argument('-p', '--pretend', action='store_const', const=True, default=False,
                    dest='pretend', help="Pass this flag if you want to do a dry run. ")
parser.add_argument('mode', choices=['before', 'on', 'after', 'all'],
                    help="Options for mode are: 'before', 'on', 'after', and 'all'.")
parser.add_argument('date', help="Date should be entered in this format: YYYY-MM-DD.")

args = parser.parse_args()

pretend = args.pretend
mode = args.mode
date_str = args.date
date_parts = date_str.split("-")
date = pd.datetime(year=int(date_parts[0]), month=int(date_parts[1]), day=int(date_parts[2]))
print("Date: %s" % date)

games = None

if mode == 'on':
    games = Game.objects.filter(game_date_est=date)
elif mode == 'before':
    games = Game.objects.filter(game_date_est__lt=date)
elif mode == 'after':
    games = Game.objects.filter(game_date_est__gt=date)
elif mode == 'all':
    games = Game.objects.all()

if games:
    print("Number of Games to be deleted: {num_games}".format(num_games=games.count()))
    # There's probably a cleverer way to do this, but being explicit is fine.
    qs_to_delete = [LineScore.objects.filter(game__in=games),
                    PlayerTraditionalBoxScore.objects.filter(game__in=games),
                    PlayerAdvancedBoxScore.objects.filter(game__in=games),
                    PlayerMiscBoxScore.objects.filter(game__in=games),
                    PlayerScoringBoxScore.objects.filter(game__in=games),
                    PlayerUsageBoxScore.objects.filter(game__in=games),
                    PlayerTrackingBoxScore.objects.filter(game__in=games),
                    PlayerFourFactorsBoxScore.objects.filter(game__in=games),
                    PlayerHustleStatsBoxScore.objects.filter(game__in=games),
                    TeamTraditionalBoxScore.objects.filter(game__in=games),
                    TeamAdvancedBoxScore.objects.filter(game__in=games),
                    TeamMiscBoxScore.objects.filter(game__in=games),
                    TeamScoringBoxScore.objects.filter(game__in=games),
                    TeamUsageBoxScore.objects.filter(game__in=games),
                    TeamTrackingBoxScore.objects.filter(game__in=games),
                    TeamFourFactorsBoxScore.objects.filter(game__in=games),
                    TeamHustleStatsBoxScore.objects.filter(game__in=games),
                    PlayByPlayEvent.objects.filter(game__in=games),
                    GameOfficialXref.objects.filter(game__in=games),
                    # Need to guarantee that games will be deleted last
                    games]

    for qs in qs_to_delete:
        if qs:
            print("About to delete {n} {model}".format(n=qs.count(),
                                                       model=qs.first().__class__.__name__))
            if pretend:
                print("Pretend mode is on. Skipping actual deletion")
            else:
                qs.delete()

else:
    print("No games were found for the date range chosen!")
