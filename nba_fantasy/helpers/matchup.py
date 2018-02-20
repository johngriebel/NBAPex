import logging
import simplejson
from collections import defaultdict
from nba_stats.models import Player
from nba_fantasy.models import FantasyLineupEntry
from nba_fantasy.utils import convert_field_to_literal, sort_fields

log = logging.getLogger('fantasy')


class MatchupContext:
    def __init__(self, matchup, team, scoring_json):
        self.matchup = matchup
        self.team = team
        self.scoring_json = scoring_json
        self.field_literals = []
        self.sorted_fields = []
        self.rows = []

    def populate_field_literals(self):
        self.field_literals.append("Player")
        self.sorted_fields.append("player")
        fields = self.scoring_json['total'].keys()
        self.sorted_fields = sort_fields(fields)
        self.field_literals += [convert_field_to_literal(key) for key in self.sorted_fields]

    def populate_rows(self):
        for plr_score in self.scoring_json:
            row = []
            if plr_score != "total":
                player = Player.objects.get(id=plr_score)
                row.append(player)
                for field in self.sorted_fields:
                    row.append(self.scoring_json[plr_score][field])
                self.rows.append(row)
        total_row = ['Totals']
        for field in self.sorted_fields:
            total_row.append(self.scoring_json['total'][field])
        self.rows.append(total_row)


def _get_box_score_model_name(table):
    cls_name = "Player"
    stubs = table.split("_")
    for stub in stubs:
        cls_name += (stub[0].upper() + stub[1:])
        if stub == "hustle":
            cls_name += "Stats"

    cls_name += "BoxScore"
    return cls_name


class MatchupRow:
    def __init__(self, player_name, score_fields):
        self.player_name = player_name
        self.score_fields = score_fields


class TeamMatchupEntries:
    def __init__(self, matchup, team):
        log.debug("Creating a matchup entries obj")
        self.matchup = matchup
        self.team = team
        self.lup_entries = FantasyLineupEntry.objects.filter(team=self.team,
                                                             lineup_date__gte=self.matchup.begin_date,
                                                             lineup_date__lte=self.matchup.end_date)
        self.matchup_rows = []

    def create_rows(self):
        # Would be nice to have a group by
        my_players = self.lup_entries.values_list('player', flat=True).distinct('player')
        final_totals = defaultdict(float)
        for player_id in my_players:
            player_entries = self.lup_entries.filter(player__id=player_id)
            row_totals = defaultdict(float)
            player_name = ""
            for entry in player_entries:
                player_name = entry.player.display_first_last
                score = simplejson.loads(entry.score)
                for key in score:
                    if key == 'total':
                        row_totals[key] += score[key]
                        final_totals[key] += score[key]
                    else:
                        row_totals[key] += score[key][0]
                        final_totals[key] += score[key][0]
            new_row = MatchupRow(player_name=player_name,
                                 score_fields=row_totals)
            self.matchup_rows.append(new_row)
        team_total_row = MatchupRow(player_name="Team Totals",
                                    score_fields=final_totals)
        self.matchup_rows.append(team_total_row)

        return self.matchup_rows

