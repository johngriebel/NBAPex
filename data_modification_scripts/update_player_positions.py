import django
django.setup()
import logging
from nba_stats.models import Player
from nba_stats.utils import get_beautiful_soup as getbs
from nba_stats.constants import BBREF_BASE_URL

log = logging.getLogger('stats')
block_char = chr(9642)
positions_map = {'point guard': '1',
                 'shooting guard': '2',
                 'small forward': '3',
                 'power forward': '4',
                 'center': '5',
                 'forward': '3,4'}


def find_position_tag(tag):
    return "Position:" in tag.text
try:
    bad_count = 0
    active_players = Player.objects.filter(to_year=2016,
                                           numbered_positions__isnull=True).exclude(bbref_id_str="")
    log.debug(("num players", active_players.count()))
    for player in active_players:
        log.debug(("working on ", player.display_first_last))
        suffix = "players/{l}/{idstr}.html".format(l=player.bbref_id_str[0],
                                                   idstr=player.bbref_id_str)
        full_url = BBREF_BASE_URL + suffix
        soup = getbs(full_url)
        info = soup.find(attrs={'id': 'info'})
        subpanel = info.find(attrs={'itemtype': "http://schema.org/Person"})
        pos_pgraph = subpanel.find_all(find_position_tag)
        if not len(pos_pgraph):
            log.debug(("Couldn't find the position paragraph for ", player.display_first_last))
            bad_count += 1
            continue
        pos_pgraph = pos_pgraph[0]
        cleaned = pos_pgraph.text.replace("\n", "").replace(block_char, "").strip().split(":")
        position_str = cleaned[cleaned.index("Position") + 1].replace("Shoots", "").strip()
        all_positions = [p.lower().strip() for p in position_str.split("and")]
        numerical_position_str = ""
        log.debug(("all positions", all_positions))
        for pos in all_positions:
            log.debug(("current pos", pos))
            numerical_position_str += positions_map[pos] + ","

        log.debug(("Numbered positions for ", player.display_first_last, numerical_position_str))
        player.numbered_positions = numerical_position_str
        player.save()

    log.debug(("Bad count", bad_count))
except Exception as e:
    log.exception(e)
    raise e

