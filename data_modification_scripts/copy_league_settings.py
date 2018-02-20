import django
import logging
import argparse
django.setup()
from django.core.exceptions import ObjectDoesNotExist
from nba_fantasy.models import FantasyLeague
log = logging.getLogger('fantasy')

parser = argparse.ArgumentParser(description="Copy values on league settings objects to the "
                                             "league they reference so we can delete the "
                                             "unnecessary models.")
parser.add_argument('-p', '--pretend', action='store_const', const=True, default=False,
                    dest='pretend', help="Pass this flag if you want to do a dry run. ")
args = parser.parse_args()
pretend = args.pretend

leagues = FantasyLeague.objects.all()
ignore_vars = ["_league_cache", "league_id", "_state", "id"]

for league in leagues:
    msg = "Working on {lg}".format(lg=league)
    print(msg)
    log.debug(msg)
    try:
        copy_objects = [league.transactionsettings, league.schedulesettings, league.draftsettings,
                        league.scoringsettings, league.rostersettings]
    except ObjectDoesNotExist as e:
        print("{lg} does not have the settings you're looking for. Moving on!")
        continue

    for obj in copy_objects:
        msg = "Copying vars for {x}".format(x=obj.__class__.__name__)
        print(msg)
        log.debug(msg)
        for fld in vars(obj):
            if fld not in ignore_vars:
                val = getattr(obj, fld)
                if not pretend:
                    setattr(league, fld, val)
                    obj.delete()
                else:
                    print("Would be setting {fld} to {val} "
                          "and deleting {cls} w/ id {id}".format(fld=fld,
                                                                 val=val,
                                                                 cls=obj.__class__.__name__,
                                                                 id=obj.id))
    league.save()
