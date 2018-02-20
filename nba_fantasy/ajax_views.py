import logging
import json
from django.http import JsonResponse
from nba_stats.utils import convert_datetime_string_to_date_instance
from nba_fantasy.models import FantasyLineupEntry
log = logging.getLogger('fantasy')


def ajax_update_fantasy_lineup(request):
    user_id = request.session.get('user_id')
    first_player = json.loads(request.POST.get('firstPlayer'))
    second_player = json.loads(request.POST.get('secondPlayer'))
    date_str = request.POST.get('date')
    lup_date = convert_datetime_string_to_date_instance(date_str)
    log.debug(("user_id", user_id,
               "first", first_player,
               "second", second_player,
               "date_str", date_str))

    if int(first_player['playerId']) != 0:
        first_player_lup_entry = FantasyLineupEntry.objects.get(team__owner__id=user_id,
                                                                player_id=first_player['playerId'],
                                                                lineup_date=lup_date)
        first_player_lup_entry.position = second_player['playerPosition']
        first_player_lup_entry.save()

    if int(second_player['playerId']) != 0:
        second_player_lup_entry = FantasyLineupEntry.objects.get(team__owner__id=user_id,
                                                                 player_id=second_player['playerId'],
                                                                 lineup_date=lup_date)
        second_player_lup_entry.position = first_player['playerPosition']
        second_player_lup_entry.save()

    data = {'success': True}
    return JsonResponse(data)
