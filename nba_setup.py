import django
django.setup()
from nba_stats.models import *
from nba_stats.utils import *
from nba_stats.web_handlers.base_handler import *
from nba_stats.web_handlers.game_handler import *
from nba_stats.web_handlers.league_handler import *
from nba_stats.web_handlers.misc_handler import *
from nba_stats.web_handlers.player_handler import *
from nba_stats.web_handlers.team_handler import *
from nba_stats.helpers.coach import *
from nba_stats.helpers.game import *
from nba_stats.helpers.player import *
from nba_stats.helpers.roster import *
from nba_stats.helpers.split import *
from nba_stats.helpers.team import *
from nba_stats.helpers.tracking import *
from nba_stats.helpers.transaction import *
from nba_stats.constants import *
from nba_fantasy.models import *

# DB dump command pg_dump -d nbapex --username postgres -p 6432 -f NBAPexDump.sql