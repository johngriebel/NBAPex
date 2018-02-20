import logging
import json
from datetime import date
from channels import Group
from channels.auth import channel_session_user, channel_session_user_from_http
from nba_stats.models import Player
from nba_fantasy.models import FantasyTeam, FantasyTeamRosterEntry

log = logging.getLogger('stats')


@channel_session_user_from_http
def ws_add(message):
    # TODO: Should really figure out keyword args but this works for now.
    path_parts = message.content['path'].split("/")
    user_id = path_parts[-2]
    league_id = path_parts[-1]
    team = FantasyTeam.objects.get(owner__id=user_id,
                                   league__id=league_id)
    league = team.league
    Group("draft-%s" % league.id).add(message.reply_channel)
    message.reply_channel.send({'accept': True})


# Connected to websocket.receive
@channel_session_user
def ws_message(message):
    data = json.loads(message['text'])
    log.debug(("Data: ", data))
    team = FantasyTeam.objects.get(id=data['team_id'])
    league = team.league
    player = Player.objects.get(id=data['player_id'])
    today = date.today()
    existing_rec = FantasyTeamRosterEntry.objects.get(league=league,
                                                      player=player,
                                                      end_date=None,
                                                      acquired_via="UO")
    existing_rec.end_date = today
    existing_rec.save()
    new_rec = FantasyTeamRosterEntry(league=league,
                                     team=team,
                                     player=player,
                                     acquisition_date=today,
                                     end_date=None,
                                     acquired_via="DR")
    new_rec.save()
    row_to_remove_id = str(player.id) + "_player_row"
    Group("draft-%s" % league.id).send({
        "text": json.dumps({'drafted': True,
                            'selected': row_to_remove_id}),
    })


# Connected to websocket.disconnect
@channel_session_user
def ws_disconnect(message):
    # team = FantasyTeam.objects.get(owner=message.user)
    # league = team.league
    Group("draft-%s" % "41").discard(message.reply_channel)