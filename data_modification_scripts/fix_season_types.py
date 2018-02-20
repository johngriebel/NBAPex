import django
django.setup()
import logging
from django.apps import apps
from nba_stats.models import PlayerSeason
log = logging.getLogger("stats")


player_seasons = PlayerSeason.objects.all().order_by("id")
tot = player_seasons.count()
cur = 1

for season in player_seasons:
    pct_done = str(100 * (cur / tot))[:4]
    if "career" in season.season_type.lower():
        season.career_flag = True
    else:
        # It should already be False, but just in case
        season.career_flag = False
    season.mod_user = __file__
    new_season_type = season.season_type.replace("Career", "").replace("Totals", "").lstrip("Season")
    season.season_type = new_season_type
    season.save()
    cur += 1

stats_models = apps.get_app_config("nba_stats").get_models()
for model in stats_models:
    if hasattr(model, "season_type") and model != PlayerSeason:
        log.info(f"Working on {model}")
        objects = model.objects.all()
        tot = objects.count()
        log.info(f"{tot} objects to update.")
        for obj in objects:
            new_season_type = obj.season_type.replace(" ", "")
            obj.season_type = new_season_type
            obj.mod_user = __file__
            obj.save()
